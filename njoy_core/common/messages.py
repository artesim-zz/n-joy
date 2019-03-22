import collections
import enum
import pickle
import struct


class MessageException(Exception):
    pass


@enum.unique
class HatValue(enum.IntFlag):
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


@enum.unique
class CtrlKind(enum.IntFlag):
    AXIS = enum.auto()
    BUTTON = enum.auto()
    HAT = enum.auto()

    def short_str(self):
        return {CtrlKind.AXIS: 'axis',
                CtrlKind.BUTTON: 'button',
                CtrlKind.HAT: 'hat'}[self.value]

    @staticmethod
    def from_value(value):
        if isinstance(value, float):
            return CtrlKind.AXIS
        elif isinstance(value, bool):
            return CtrlKind.BUTTON
        elif isinstance(value, int) and value in HatValue.set():
            return CtrlKind.HAT
        else:
            return None


class CtrlIdentity(collections.namedtuple('CtrlIdentity',
                                          ['node', 'device', 'kind', 'control'],
                                          defaults=[None, None, None, None])):
    __IDENTITY_PACKER = struct.Struct('>H')
    __TO_KIND__ = {0x0080: CtrlKind.AXIS,
                   0x0000: CtrlKind.BUTTON,
                   0x00C0: CtrlKind.HAT}
    __CTRL_MASK__ = {0x0080: 0x0007,
                     0x0000: 0x007F,
                     0x00C0: 0x0003}

    @property
    def is_anonymous(self):
        return all([f is None for f in self])

    @property
    def is_partial(self):
        return any([f is None for f in self])

    def packed(self):
        if self.is_partial:
            return None

        elif self.kind is CtrlKind.AXIS:
            return self.__IDENTITY_PACKER.pack((self.node & 0xF) << 12 |
                                               (self.device & 0xF) << 8 |
                                               0x80 |
                                               (self.control & 0x07))
        elif self.kind is CtrlKind.BUTTON:
            return self.__IDENTITY_PACKER.pack((self.node & 0xF) << 12 |
                                               (self.device & 0xF) << 8 |
                                               (self.control & 0x7F))
        elif self.kind is CtrlKind.HAT:
            return self.__IDENTITY_PACKER.pack((self.node & 0xF) << 12 |
                                               (self.device & 0xF) << 8 |
                                               0xC0 |
                                               (self.control & 0x03))
        else:
            return None

    @classmethod
    def unpacked(cls, frame):
        unpacked = cls.__IDENTITY_PACKER.unpack(frame)
        return cls((unpacked[0] & 0xF000) >> 12,                           # node
                   (unpacked[0] & 0x0F00) >> 8,                            # device
                   cls.__TO_KIND__[unpacked[0] & 0x00C0],                  # kind
                   unpacked[0] & cls.__CTRL_MASK__[unpacked[0] & 0x00C0])  # control


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
    => We can have at most one node per device, so the max number of nodes is equal to the max number of devices

    Max number of devices : 16 => [0x0 .. 0xF]
    => We're bound by the max number of virtual output devices (vjoy API)

    Max number of axes per device    :   8 => [0x0  ..  0x7] => MSB kind = 10, control_id on 3 LSB bits
    Max number of buttons per device : 128 => [0x00 .. 0x7F] => MSB kind = 0,  control_id on 7 remaining LSB bits
    Max number of hats per device    :   4 => [0x0  ..  0x3] => MSB kind = 11, control_id on 2 LSB bits
    => We're bound by the max number of virtual output devices (vjoy API)

    Summing up :
    => The identity can be coded on 2 bytes
    """

    __BUTTON_VALUE_PACKER__ = struct.Struct('>?')
    __HAT_VALUE_PACKER__ = struct.Struct('>B')
    __AXIS_VALUE_PACKER__ = struct.Struct('>d')

    # node, device, ctrl and value are keyword-only arguments (after the *)
    def __init__(self, *, node=None, device=None, kind=None, control=None, identity=None, value=None):
        if identity is None:
            if kind is not None:
                k = kind
            elif node is None and device is None and control is None:
                k = kind
            else:
                k = CtrlKind.from_value(value)
            self.identity = CtrlIdentity(node, device, k, control)
        else:
            self.identity = identity

        self.value = value

    def _serialize_identity(self):
        if self.identity.is_anonymous:
            return []
        else:
            # Adding an empty frame for compatibility with the REQ sockets, when used with a ROUTER socket
            return [self.identity.packed(), b'']

    def _serialize_value(self):
        if self.value is None:
            return [b'']

        if isinstance(self.value, float):
            return [self.__AXIS_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.value, bool):
            return [self.__BUTTON_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.value, int) and (0x00 <= self.value <= 0x0F):
            return [self.__HAT_VALUE_PACKER__.pack(self.value | 0x80)]

        else:
            raise MessageException("Cannot serialize value : {}".format(self.value))

    def send(self, socket):
        socket.send_multipart(self._serialize_identity() + self._serialize_value())

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
            raise MessageException("Cannot deserialize value frames : {}".format(value_frames))

    @classmethod
    def _deserialize(cls, frames):
        if len(frames[0]) == 2 and frames[1] == b'':
            return {'identity': CtrlIdentity.unpacked(frames[0]),
                    'value': cls._deserialize_value(frames[2:])}
        else:
            return {'value': cls._deserialize_value(frames)}

    @classmethod
    def recv(cls, socket):
        return cls(**cls._deserialize(socket.recv_multipart()))


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
                raise MessageException("Invalid command : {}".format(_p))

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
