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


@enum.unique
class ControlEventKind(enum.IntFlag):
    BUTTON = 1
    HAT = 2
    AXIS = 4

    def short_str(self):
        if self == 1:
            return 'button'
        elif self == 2:
            return 'hat'
        elif self == 4:
            return 'axis'

    @classmethod
    def from_value(cls, value):
        if isinstance(value, bool):
            return cls.BUTTON
        elif isinstance(value, int):
            return cls.HAT
        elif isinstance(value, float):
            return cls.AXIS


class ControlEvent:
    """
    Anonymous ControlEvent frames:
            | Evt Kind | Evt Val      |
    Ready:  |     -    |                A single empty frame (used as a 'ready' signal)
    Button: | 00000001 | 0000000.     | bool
    Hat:    | 00000010 | 0000....     | HatValue enum
    Axis:   | 00000100 | ........ * 8 | float (double)

    ControlEvent frames:
            |     Identity      |
            | Node/Dev Control  | Empty | Evt Kind | Evt Val      |
    Ready:  | ........ ........ |   -   |     -    |                Id + 2 empty frames (used as a 'ready' signal)
    Button: | ........ ........ |   -   | 00000001 | 0000000.     | bool
    Hat:    | ........ ........ |   -   | 00000010 | 0000....     | HatValue enum
    Axis:   | ........ ........ |   -   | 00000100 | ........ * 8 | float (double)

    Reasoning for the format of the identity frame :

    Max number of nodes : 16 => [0x0 .. 0xF]
    => We can have at most one node per device, so the max number of nodes is equal to the max number of devices

    Max number of devices : 16 => [0x0 .. 0xF]
    => We're bound by the max number of virtual output devices (vjoy API)

    Max number of controls per device : 128 buttons + 8 axis + 4 hats => [0x00 .. 0x8B]
    => We're bound by the max number of virtual output devices (vjoy API)

    Summing up :
    => The identity can be coded on 16 bits : [0x0000 .. 0xFF8B]
    """

    __IDENTITY_PACKER = struct.Struct('>H')

    __EVENT_KIND_PACKER__ = struct.Struct('>B')

    __BUTTON_VALUE_PACKER__ = struct.Struct('>?')
    __HAT_VALUE_PACKER__ = struct.Struct('>B')
    __AXIS_VALUE_PACKER__ = struct.Struct('>d')

    # node, device, ctrl and value are keyword-only arguments (after the *)
    def __init__(self, *, node=None, device=None, control=None, value=None):
        self.node = node
        self.device = device
        self.control = control
        self.control_kind = ControlEventKind.from_value(value)
        self.value = value

    @property
    def identity(self):
        if self.is_event:
            return self.__IDENTITY_PACKER.pack((self.node & 0xF) << 12 |
                                               (self.device & 0xF) << 8 |
                                               (self.control & 0xFF))
        else:
            return None

    @property
    def is_event(self):
        return not self.is_ready_signal

    @property
    def is_ready_signal(self):
        return any([self.node is None,
                    self.device is None,
                    self.control is None])

    @classmethod
    def _unpacked_identity(cls, identity):
        unpacked = cls.__IDENTITY_PACKER.unpack(identity)
        return ((unpacked[0] & 0xF000) >> 12,
                (unpacked[0] & 0x0F00) >> 8,
                (unpacked[0] & 0x00FF))

    def _serialize_identity(self):
        identity = self.identity

        if identity is None:
            return []
        else:
            # Adding an empty frame for compatibility with the REQ sockets, when used with a ROUTER socket
            return [identity, b'']

    def _serialize_value(self):
        if self.value is None:
            return [b'']

        elif isinstance(self.value, bool):
            return [self.__EVENT_KIND_PACKER__.pack(ControlEventKind.BUTTON),
                    self.__BUTTON_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.value, int) and (0x00 <= self.value <= 0x0F):
            return [self.__EVENT_KIND_PACKER__.pack(ControlEventKind.HAT),
                    self.__HAT_VALUE_PACKER__.pack(self.value)]

        elif isinstance(self.value, float):
            return [self.__EVENT_KIND_PACKER__.pack(ControlEventKind.AXIS),
                    self.__AXIS_VALUE_PACKER__.pack(self.value)]

        else:
            raise MessageException("Cannot serialize value : {}".format(self.value))

    def send(self, socket):
        frames = self._serialize_identity() + self._serialize_value()
        socket.send_multipart(frames)

    @classmethod
    def _deserialize_value(cls, value_frames):
        if len(value_frames) == 1 and value_frames[0] == b'':
            return None  # Single-Frame 'Ready' signal

        elif len(value_frames) == 2:
            event_kind = cls.__EVENT_KIND_PACKER__.unpack(value_frames[0])
            event_kind = ControlEventKind(event_kind[0])

            if event_kind == ControlEventKind.BUTTON:
                unpacked = cls.__BUTTON_VALUE_PACKER__.unpack(value_frames[1])
                return unpacked[0]

            elif event_kind == ControlEventKind.HAT:
                unpacked = cls.__HAT_VALUE_PACKER__.unpack(value_frames[1])
                return unpacked[0]

            elif event_kind == ControlEventKind.AXIS:
                unpacked = cls.__AXIS_VALUE_PACKER__.unpack(value_frames[1])
                return unpacked[0]

            else:
                raise MessageException("Cannot deserialize value frames : {}".format(value_frames))
        else:
            raise MessageException("Cannot deserialize value frames : {}".format(value_frames))

    @classmethod
    def _deserialize(cls, frames):
        if len(frames[0]) == 2 and frames[1] == b'':
            node, device, control = cls._unpacked_identity(frames[0])
            return {'node': node,
                    'device': device,
                    'control': control,
                    'value': cls._deserialize_value(frames[2:])}
        else:
            return {'node': None,
                    'device': None,
                    'control': None,
                    'value': cls._deserialize_value(frames)}

    @classmethod
    def recv(cls, socket):
        return cls(**cls._deserialize(socket.recv_multipart()))


class RequestReply:
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
        return cls(command=frames[0].decode('utf-8'),
                   payload=[pickle.loads(frame) for frame in frames[1:]])


class InputNodeRegisterRequest(RequestReply):
    def __init__(self, *, devices):
        super().__init__(command='register',
                         payload=devices)
        self.devices = devices

    @classmethod
    def recv(cls, socket):
        request = RequestReply.recv(socket)
        if request.command == 'register':
            return cls(devices=request.payload)
        else:
            raise MessageException("Unexpected answer : {}".format(request))


class InputNodeRegisterReply(RequestReply):
    def __init__(self, *, node_id, device_ids_map):
        super().__init__(command='registered',
                         payload=[node_id, device_ids_map])
        self.node_id = node_id
        self.device_ids_map = device_ids_map

    @classmethod
    def recv(cls, socket):
        reply = RequestReply.recv(socket)
        if reply.command == 'registered':
            return cls(node_id=reply.payload[0],
                       device_ids_map=reply.payload[1])
        else:
            raise MessageException("Unexpected answer : {}".format(reply))

# EOF
