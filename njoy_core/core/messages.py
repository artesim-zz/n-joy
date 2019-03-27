import pickle
import struct

from .model.device import PhysicalDevice, VirtualDevice
from .model.control import HatState, Axis, Button, Hat


class MessageError(Exception):
    pass


class ControlEvent:
    """
    Anonymous ControlEvent frames:
            | Evt Val      |
    Ready:  |     -        | A single empty frame (used as a 'ready' signal)
    Axis:   | vvvvvvvv * 8 | float (double)
    Button: | 0000000v     | bool          (MSB = 0)
    Hat:    | 1000vvvv     | HatValue enum (MSB = 1)

    ControlEvent frames:
            |     Identity      |
            | Node+Dev Kind+Ctrl| Empty | Evt Val      |
    Ready:  | nnnndddd ........ |   -   |     -        | Id + 2 empty frames (used as a 'ready' signal)
    Axis:   | nnnndddd 10000ccc |   -   | vvvvvvvv * 8 | float (double)
    Button: | nnnndddd 0ccccccc |   -   | 0000000v     | bool          (MSB = 0)
    Hat:    | nnnndddd 110000cc |   -   | 1000vvvv     | HatValue enum (MSB = 1)

    Reasoning for the format of the identity frame :

    Max number of nodes : 16 => [0x0 .. 0xF]
    => Arbitrary limit, using what's left of the first byte when the device id has been coded (see below)
    => Plus, 16 nodes still seems a reasonable limit for now (16x16=256 devices, that's a lot)

    Max number of devices per node : 16 => [0x0 .. 0xF]
    => We're bound by the max number of virtual output devices (vjoy API)

    Max number of axes per device    :   8 => [0x0  ..  0x7] => MSB kind = 10, control_id on 3 LSB bits
    Max number of buttons per device : 128 => [0x00 .. 0x7F] => MSB kind = 0,  control_id on 7 remaining LSB bits
    Max number of hats per device    :   4 => [0x0  ..  0x3] => MSB kind = 11, control_id on 2 LSB bits
    => We're bound by the max number of virtual output devices (vjoy API)

    Summing up :
    => The identity can be coded on 2 bytes
    """
    __IDENTITY_PACKER = struct.Struct('>H')

    __BUTTON_VALUE_PACKER__ = struct.Struct('>?')
    __HAT_VALUE_PACKER__ = struct.Struct('>B')
    __AXIS_VALUE_PACKER__ = struct.Struct('>d')

    __CTRL_CLS__ = {0x0080: Axis,
                    0x0000: Button,
                    0x0040: Button,
                    0x00C0: Hat}
    __CTRL_ID_MASK__ = {0x0080: 0x0007,
                        0x0000: 0x007F,
                        0x00C0: 0x0003}
    __DEV_CLASS__ = NotImplemented

    def __init__(self, *, control=None, value=None):
        self.control = control
        self.value = value

    def _serialize_control(self):
        if self.control is None:
            return []
        else:
            if not self.control.is_assigned:
                raise MessageError("Cannot serialize an unassigned control.")

            elif isinstance(self.control, Axis):
                packed_control = self.__IDENTITY_PACKER.pack((self.control.dev.node.id & 0xF) << 12 |
                                                             (self.control.dev.id & 0xF) << 8 |
                                                             0x80 |
                                                             (self.control.id & 0x07))
            elif isinstance(self.control, Button):
                packed_control = self.__IDENTITY_PACKER.pack((self.control.dev.node.id & 0xF) << 12 |
                                                             (self.control.dev.id & 0xF) << 8 |
                                                             (self.control.id & 0x7F))
            elif isinstance(self.control, Hat):
                packed_control = self.__IDENTITY_PACKER.pack((self.control.dev.node.id & 0xF) << 12 |
                                                             (self.control.dev.id & 0xF) << 8 |
                                                             0xC0 |
                                                             (self.control.id & 0x03))
            else:
                raise MessageError("Cannot serialize: invalid control.")

            # Adding an empty frame for compatibility with the REQ sockets, when used with a ROUTER socket
            return [packed_control, b'']

    def _serialize_value(self):
        if self.value is None:
            return [b'']

        if isinstance(self.control, Axis) or isinstance(self.value, float):
            return [self.__AXIS_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.control, Button) or isinstance(self.value, bool):
            return [self.__BUTTON_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.control, Hat) or (isinstance(self.value, int) and (0x00 <= self.value <= 0x0F)):
            return [self.__HAT_VALUE_PACKER__.pack(self.value | 0x80)]

        else:
            raise MessageError("Cannot serialize value : {}".format(self.value))

    def send(self, socket):
        socket.send_multipart(self._serialize_control() + self._serialize_value())

    @classmethod
    def _control_class_from_value(cls, value):
        if isinstance(value, float):
            return Axis
        elif isinstance(value, bool):
            return Button
        elif isinstance(value, int) and value in HatState.set():
            return Hat
        else:
            return None

    @classmethod
    def _deserialize_control(cls, control_frame):
        unpacked = cls.__IDENTITY_PACKER.unpack(control_frame)
        dev = cls.__DEV_CLASS__(node=(unpacked[0] & 0xF000) >> 12,
                                dev=(unpacked[0] & 0x0F00) >> 8)
        ctrl_class = cls.__CTRL_CLS__[unpacked[0] & 0x00C0]
        ctrl_id = unpacked[0] & cls.__CTRL_ID_MASK__[unpacked[0] & 0x00C0]
        return ctrl_class(dev=dev, ctrl=ctrl_id)

    @classmethod
    def _deserialize_value(cls, value_frames):
        if value_frames[0] == b'':
            return None  # Single-Frame 'Ready' signal

        elif len(value_frames[0]) == 8:
            unpacked = cls.__AXIS_VALUE_PACKER__.unpack(value_frames[0])
            return unpacked[0]

        elif len(value_frames[0]) == 1 and value_frames[0][0] & 0x80 == 0x00:
            unpacked = cls.__BUTTON_VALUE_PACKER__.unpack(value_frames[0])
            return unpacked[0]

        elif len(value_frames[0]) == 1 and value_frames[0][0] & 0x80 == 0x80:
            unpacked = cls.__HAT_VALUE_PACKER__.unpack(value_frames[0])
            return unpacked[0] & 0x0F

        else:
            raise MessageError("Cannot deserialize value frames : {}".format(value_frames))

    @classmethod
    def _deserialize(cls, frames):
        if len(frames[0]) == 2 and frames[1] == b'':
            return {'control': cls._deserialize_control(frames[0]),
                    'value': cls._deserialize_value(frames[2:])}
        else:
            return {'value': cls._deserialize_value(frames)}

    @classmethod
    def recv(cls, socket):
        return cls(**cls._deserialize(socket.recv_multipart()))


class PhysicalControlEvent(ControlEvent):
    __DEV_CLASS__ = PhysicalDevice


class VirtualControlEvent(ControlEvent):
    __DEV_CLASS__ = VirtualDevice


class CoreRequest:
    def __init__(self, *, command, payload):
        self.command = command
        self.payload = payload

    def send(self, socket):
        def _encoded_command(_p):
            if isinstance(_p, str):
                return _p.encode('utf-8')
            elif isinstance(_p, bytes):
                return _p
            else:
                raise MessageError("Invalid command : {}".format(_p))

        socket.send_multipart([_encoded_command(self.command)] +
                              [pickle.dumps(frame) for frame in self.payload])

    @classmethod
    def recv(cls, socket):
        frames = socket.recv_multipart()
        command = frames[0].decode('utf-8')
        payload = [pickle.loads(frame) for frame in frames[1:]]
        if command == 'register':
            return InputNodeRegisterRequest(devices=payload)
        elif command == 'registered':
            return InputNodeRegisterReply(node_id=payload[0],
                                          device_ids_map=payload[1])
        elif command == 'capabilities':
            return OutputNodeCapabilities(capabilities=payload)
        elif command == 'assignments':
            return OutputNodeAssignments(node_id=payload[0],
                                         assignments=payload[1])
        else:
            return cls(command=command, payload=payload)


class InputNodeRegisterRequest(CoreRequest):
    def __init__(self, *, devices):
        super().__init__(command='register',
                         payload=devices)

    @property
    def devices(self):
        return self.payload


class InputNodeRegisterReply(CoreRequest):
    def __init__(self, *, node_id, device_ids_map):
        super().__init__(command='registered',
                         payload=[node_id, device_ids_map])

    @property
    def node_id(self):
        return self.payload[0]

    @property
    def device_ids_map(self):
        return self.payload[1]


class OutputNodeCapabilities(CoreRequest):
    def __init__(self, *, capabilities):
        super().__init__(command='capabilities',
                         payload=capabilities)

    @property
    def capabilities(self):
        return self.payload


class OutputNodeAssignments(CoreRequest):
    def __init__(self, *, node_id, assignments):
        super().__init__(command='assignments',
                         payload=[node_id, assignments])

    @property
    def node_id(self):
        return self.payload[0]

    @property
    def assignments(self):
        return self.payload[1]
