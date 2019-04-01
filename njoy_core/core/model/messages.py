import enum
import pickle
import struct

from .devices import PhysicalDevice, VirtualDevice
from .controls import Axis, Button, Hat


class MessageError(Exception):
    pass


@enum.unique
class HatState(enum.IntFlag):
    HAT_CENTER = 0
    HAT_UP = 1
    HAT_RIGHT = 2
    HAT_DOWN = 4
    HAT_LEFT = 8
    HAT_UP_RIGHT = HAT_UP | HAT_RIGHT
    HAT_UP_LEFT = HAT_UP | HAT_LEFT
    HAT_DOWN_RIGHT = HAT_DOWN | HAT_RIGHT
    HAT_DOWN_LEFT = HAT_DOWN | HAT_LEFT

    @classmethod
    def list(cls):
        return [v for v in cls]

    @classmethod
    def set(cls):
        return {v for v in cls}


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

    @classmethod
    def mk_identity(cls, control):
        if not control.is_assigned:
            raise MessageError("Cannot make a socket identity out of unassigned controls.")

        elif isinstance(control, Axis):
            return cls.__IDENTITY_PACKER.pack((control.dev.node.id & 0xF) << 12 |
                                              (control.dev.id & 0xF) << 8 |
                                              0x80 |
                                              (control.id & 0x07))
        elif isinstance(control, Button):
            return cls.__IDENTITY_PACKER.pack((control.dev.node.id & 0xF) << 12 |
                                              (control.dev.id & 0xF) << 8 |
                                              (control.id & 0x7F))
        elif isinstance(control, Hat):
            return cls.__IDENTITY_PACKER.pack((control.dev.node.id & 0xF) << 12 |
                                              (control.dev.id & 0xF) << 8 |
                                              0xC0 |
                                              (control.id & 0x03))
        else:
            raise MessageError("Invalid control class.")

    def _serialize_control(self):
        if self.control is None:
            return []
        else:
            # Adding an empty frame for compatibility with the REQ sockets, when used with a ROUTER socket
            return [self.mk_identity(self.control), b'']

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

    @staticmethod
    def _encoded_string(string):
        if isinstance(string, str):
            return string.encode('utf-8')
        elif isinstance(string, bytes):
            return string

    @staticmethod
    def _decoded_string(string):
        if isinstance(string, str):
            return string
        elif isinstance(string, bytes):
            return string.decode('utf-8')

    def send(self, socket):
        socket.send_multipart([self._encoded_string(self.command)] +
                              [pickle.dumps(frame) for frame in self.payload])

    @classmethod
    def recv(cls, socket):
        frames = socket.recv_multipart()
        command = cls._decoded_string(frames[0])
        payload = [pickle.loads(frame) for frame in frames[1:]]
        if command == 'register':
            return InputNodeRegisterRequest(available_devices=payload)
        elif command == 'registered':
            return InputNodeRegisterReply(node=payload[0])
        elif command == 'capabilities':
            return OutputNodeCapabilities(capabilities=payload)
        elif command == 'assignments':
            return OutputNodeAssignments(node=payload[0])
        else:
            return cls(command=command, payload=payload)


class InputNodeRegisterRequest(CoreRequest):
    def __init__(self, *, available_devices):
        super().__init__(command='register',
                         payload=available_devices)

    @property
    def available_devices(self):
        return self.payload


class InputNodeRegisterReply(CoreRequest):
    def __init__(self, *, node):
        super().__init__(command='registered',
                         payload=[node])

    @property
    def node(self):
        return self.payload[0]


class OutputNodeCapabilities(CoreRequest):
    def __init__(self, *, capabilities):
        super().__init__(command='capabilities',
                         payload=capabilities)

    @property
    def capabilities(self):
        return self.payload


class OutputNodeAssignments(CoreRequest):
    def __init__(self, *, node):
        super().__init__(command='assignments',
                         payload=[node])

    @property
    def node(self):
        return self.payload[0]
