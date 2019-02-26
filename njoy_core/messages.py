import enum
import struct


class MessageException(Exception):
    pass


@enum.unique
class MessageType(enum.IntEnum):
    HID_REQUEST = enum.auto()
    HID_REPLY = enum.auto()
    HID_FULL_STATE_REPLY = enum.auto()
    HID_AXIS_EVENT = enum.auto()
    HID_BALL_EVENT = enum.auto()
    HID_BUTTON_EVENT = enum.auto()
    HID_HAT_EVENT = enum.auto()


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


class Message:
    __HEADER_PACKER__ = struct.Struct('>B')

    @property
    def msg_parts(self):
        raise NotImplementedError

    @classmethod
    def from_msg_parts(cls, msg_parts):
        msg_type, = cls.__HEADER_PACKER__.unpack(msg_parts[0][0:cls.__HEADER_PACKER__.size])

        if msg_type == MessageType.HID_REQUEST:
            return HidRequest.from_msg_parts(msg_parts)

        elif msg_type == MessageType.HID_REPLY:
            return HidReply.from_msg_parts(msg_parts)

        elif msg_type == MessageType.HID_FULL_STATE_REPLY:
            return HidDeviceFullStateReply.from_msg_parts(msg_parts)

        elif msg_type in {MessageType.HID_AXIS_EVENT,
                          MessageType.HID_BALL_EVENT,
                          MessageType.HID_BUTTON_EVENT,
                          MessageType.HID_HAT_EVENT}:
            return HidEvent.from_msg_parts(msg_parts)

    def send(self, socket):
        socket.send_multipart(self.msg_parts)

    @classmethod
    def recv(cls, socket):
        return cls.from_msg_parts(socket.recv_multipart())


class HidRequest(Message):
    def __init__(self, command, *args):
        self._command = command
        self._args = args

    @property
    def command(self):
        return self._command

    @property
    def args(self):
        return self._args

    @property
    def msg_header(self):
        return self.__HEADER_PACKER__.pack(MessageType.HID_REQUEST)

    @property
    def msg_parts(self):
        def _encoded_part(_p):
            if isinstance(_p, str):
                return _p.encode('utf-8')
            elif isinstance(_p, bytes):
                return _p
            else:
                raise MessageException("Invalid message_part type : {}".format(type(_p)))

        return [self.msg_header, _encoded_part(self._command)] + [_encoded_part(p) for p in self._args]

    @classmethod
    def from_msg_parts(cls, msg_parts):
        decoded_args = [arg.decode('utf-8') for arg in msg_parts[2:]]
        return cls(msg_parts[1].decode('utf-8'), *decoded_args)


class HidReply(HidRequest):
    @property
    def msg_header(self):
        return self.__HEADER_PACKER__.pack(MessageType.HID_REPLY)


class HidDeviceFullStateReply(Message):
    __HEADER_PACKER__ = struct.Struct('>BI')

    def __init__(self, device_id, device_full_state=None, decoded_control_events=None):
        self._device_id = device_id

        if device_full_state is not None:
            self._control_events = list()
            for ctrl_type, ctrl_id, value in device_full_state:
                if ctrl_type == 'axis':
                    self._control_events.append(HidAxisEvent(device_id=device_id,
                                                             ctrl_id=ctrl_id,
                                                             value=value))
                elif ctrl_type == 'ball':
                    self._control_events.append(HidBallEvent(device_id=device_id,
                                                             ctrl_id=ctrl_id,
                                                             dx=value[0],
                                                             dy=value[1]))
                elif ctrl_type == 'button':
                    self._control_events.append(HidButtonEvent(device_id=device_id,
                                                               ctrl_id=ctrl_id,
                                                               state=value))
                elif ctrl_type == 'hat':
                    self._control_events.append(HidHatEvent(device_id=device_id,
                                                            ctrl_id=ctrl_id,
                                                            value=value))
                else:
                    raise MessageException("Unknown control type : {}".format(ctrl_type))

        else:
            self._control_events = decoded_control_events

    def __repr__(self):
        return '<HidDeviceFullState: {} ({} controls)>'.format(self._device_id, len(self._control_events))

    @property
    def device_id(self):
        return self._device_id

    @property
    def control_events(self):
        return self._control_events

    @property
    def msg_parts(self):
        msg_parts = [self.__HEADER_PACKER__.pack(MessageType.HID_FULL_STATE_REPLY, self._device_id)]
        for control_event in self._control_events:
            msg_parts.extend(control_event.msg_parts)
        return msg_parts

    @classmethod
    def from_msg_parts(cls, msg_parts):
        _, device_id = cls.__HEADER_PACKER__.unpack(msg_parts[0])
        return cls(device_id=device_id,
                   decoded_control_events=[Message.from_msg_parts(msg_parts[i:i+2])
                                           for i in range(1, len(msg_parts) - 1, 2)])


class HidEvent(Message):
    __HEADER_PACKER__ = struct.Struct('>BII')

    def __init__(self, device_id, ctrl_id):
        self._msg_type = NotImplemented
        self._device_id = device_id
        self._ctrl_id = ctrl_id

    def __hash__(self):
        return hash(self.as_key)

    def __lt__(self, other):
        return self.as_key < other.as_key

    @property
    def as_key(self):
        return self._device_id, self._msg_type, self._ctrl_id

    @property
    def msg_type(self):
        return self._msg_type

    @property
    def device_id(self):
        return self._device_id

    @property
    def ctrl_id(self):
        return self._ctrl_id

    @property
    def msg_header(self):
        return self.__HEADER_PACKER__.pack(self._msg_type, self._device_id, self._ctrl_id)

    @property
    def msg_parts(self):
        raise NotImplementedError

    @classmethod
    def from_msg_parts(cls, msg_parts):
        msg_type, device_id, ctrl_id = cls.__HEADER_PACKER__.unpack(msg_parts[0])

        if msg_type == MessageType.HID_AXIS_EVENT:
            return HidAxisEvent(device_id=device_id,
                                ctrl_id=ctrl_id,
                                value=HidAxisEvent.from_value_parts(*msg_parts[1:]))

        elif msg_type == MessageType.HID_BALL_EVENT:
            dx, dy = HidBallEvent.from_value_parts(*msg_parts[1:])
            return HidBallEvent(device_id=device_id,
                                ctrl_id=ctrl_id,
                                dx=dx,
                                dy=dy)

        elif msg_type == MessageType.HID_BUTTON_EVENT:
            return HidButtonEvent(device_id=device_id,
                                  ctrl_id=ctrl_id,
                                  state=HidButtonEvent.from_value_parts(*msg_parts[1:]))

        elif msg_type == MessageType.HID_HAT_EVENT:
            return HidHatEvent(device_id=device_id,
                               ctrl_id=ctrl_id,
                               value=HatValue(HidHatEvent.from_value_parts(*msg_parts[1:])))

        else:
            raise MessageException("Invalid Message Type")


class HidAxisEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>h')

    def __init__(self, device_id, ctrl_id, value):
        super(HidAxisEvent, self).__init__(device_id, ctrl_id)
        self._msg_type = MessageType.HID_AXIS_EVENT
        self._value = value

    def __repr__(self):
        return '<HidAxisEvent: /{}/axis/{} = {}>'.format(self._device_id, self._ctrl_id, self._value)

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        return [self.msg_header, self.__VALUE_PACKER__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_PACKER__.unpack(value_part)
        return value


class HidBallEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>hh')

    def __init__(self, device_id, ctrl_id, dx, dy):
        super(HidBallEvent, self).__init__(device_id, ctrl_id)
        self._msg_type = MessageType.HID_BALL_EVENT
        self._dx = dx
        self._dy = dy

    def __repr__(self):
        return '<HidBallEvent: /{}/ball/{} = ({}, {})>'.format(self._device_id,
                                                               self._ctrl_id, self._dx, self._dy)

    @property
    def dx(self):
        return self._dx

    @property
    def dy(self):
        return self._dy

    @property
    def msg_parts(self):
        return [self.msg_header, self.__VALUE_PACKER__.pack(self._dx, self._dy)]

    @classmethod
    def from_value_parts(cls, value_part):
        dx, dy, = cls.__VALUE_PACKER__.unpack(value_part)
        return dx, dy


class HidButtonEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>?')

    def __init__(self, device_id, ctrl_id, state):
        super(HidButtonEvent, self).__init__(device_id, ctrl_id)
        self._msg_type = MessageType.HID_BUTTON_EVENT
        self._state = state

    def __repr__(self):
        return '<HidButtonEvent: /{}/button/{} = {}>'.format(self._device_id, self._ctrl_id, self._state)

    @property
    def state(self):
        return self._state

    @property
    def msg_parts(self):
        return [self.msg_header, self.__VALUE_PACKER__.pack(self._state)]

    @classmethod
    def from_value_parts(cls, value_part):
        state, = cls.__VALUE_PACKER__.unpack(value_part)
        return state


class HidHatEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>B')

    def __init__(self, device_id, ctrl_id, value):
        super(HidHatEvent, self).__init__(device_id, ctrl_id)
        self._msg_type = MessageType.HID_HAT_EVENT
        self._value = value

    def __repr__(self):
        return '<HidHatEvent: /{}/hat/{} = {}>'.format(self._device_id, self._ctrl_id, self._value)

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        return [self.msg_header, self.__VALUE_PACKER__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_PACKER__.unpack(value_part)
        return value

# EOF
