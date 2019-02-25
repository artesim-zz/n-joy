import enum
import struct


class MessageException(Exception):
    pass


@enum.unique
class MessageType(enum.IntEnum):
    HID_FULL_STATE = 0
    HID_AXIS_EVENT = 1
    HID_BALL_EVENT = 2
    HID_BUTTON_EVENT = 3
    HID_HAT_EVENT = 4


class Message:
    __HEADER_PACKER__ = struct.Struct('>B')

    @property
    def msg_parts(self):
        raise NotImplementedError

    @classmethod
    def from_msg_parts(cls, msg_parts):
        msg_type, = cls.__HEADER_PACKER__.unpack(msg_parts[0][0:cls.__HEADER_PACKER__.size])

        if msg_type == MessageType.HID_FULL_STATE:
            return HidDeviceFullStateMsg.from_msg_parts(msg_parts)

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


class HidDeviceFullStateMsg(Message):
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
        msg_parts = [self.__HEADER_PACKER__.pack(MessageType.HID_FULL_STATE, self._device_id)]
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
        self._device_id = device_id
        self._ctrl_id = ctrl_id

    @property
    def as_key(self):
        return NotImplemented

    def __hash__(self):
        return hash(self.as_key)

    def __lt__(self, other):
        return self.as_key < other.as_key

    @property
    def device_id(self):
        return self._device_id

    @property
    def ctrl_id(self):
        return self._ctrl_id

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
                               value=HidHatEvent.from_value_parts(*msg_parts[1:]))

        else:
            raise MessageException("Invalid Message Type")


class HidAxisEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>h')

    def __init__(self, device_id, ctrl_id, value):
        super(HidAxisEvent, self).__init__(device_id, ctrl_id)
        self._value = value

    def __repr__(self):
        return '<HidAxisEvent: /{}/axis/{} = {}>'.format(self._device_id, self._ctrl_id, self._value)

    @property
    def as_key(self):
        return self._device_id, 'axis', self._ctrl_id

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        return [self.__HEADER_PACKER__.pack(MessageType.HID_AXIS_EVENT, self._device_id, self._ctrl_id),
                self.__VALUE_PACKER__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_PACKER__.unpack(value_part)
        return value


class HidBallEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>hh')

    def __init__(self, device_id, ctrl_id, dx, dy):
        super(HidBallEvent, self).__init__(device_id, ctrl_id)
        self._dx = dx
        self._dy = dy

    def __repr__(self):
        return '<HidBallEvent: /{}/ball/{} = ({}, {})>'.format(self._device_id,
                                                               self._ctrl_id, self._dx, self._dy)

    @property
    def as_key(self):
        return self._device_id, 'ball', self._ctrl_id

    @property
    def dx(self):
        return self._dx

    @property
    def dy(self):
        return self._dy

    @property
    def msg_parts(self):
        return [self.__HEADER_PACKER__.pack(MessageType.HID_BALL_EVENT, self._device_id, self._ctrl_id),
                self.__VALUE_PACKER__.pack(self._dx, self._dy)]

    @classmethod
    def from_value_parts(cls, value_part):
        dx, dy, = cls.__VALUE_PACKER__.unpack(value_part)
        return dx, dy


class HidButtonEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>?')

    def __init__(self, device_id, ctrl_id, state):
        super(HidButtonEvent, self).__init__(device_id, ctrl_id)
        self._state = state

    def __repr__(self):
        return '<HidButtonEvent: /{}/button/{} = {}>'.format(self._device_id, self._ctrl_id, self._state)

    @property
    def as_key(self):
        return self._device_id, 'button', self._ctrl_id

    @property
    def state(self):
        return self._state

    @property
    def msg_parts(self):
        return [self.__HEADER_PACKER__.pack(MessageType.HID_BUTTON_EVENT, self._device_id, self._ctrl_id),
                self.__VALUE_PACKER__.pack(self._state)]

    @classmethod
    def from_value_parts(cls, value_part):
        state, = cls.__VALUE_PACKER__.unpack(value_part)
        return state


class HidHatEvent(HidEvent):
    __VALUE_PACKER__ = struct.Struct('>B')

    def __init__(self, device_id, ctrl_id, value):
        super(HidHatEvent, self).__init__(device_id, ctrl_id)
        self._value = value

    def __repr__(self):
        return '<HidHatEvent: /{}/hat/{} = {}>'.format(self._device_id, self._ctrl_id, self._value)

    @property
    def as_key(self):
        return self._device_id, 'hat', self._ctrl_id

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        return [self.__HEADER_PACKER__.pack(MessageType.HID_HAT_EVENT, self._device_id, self._ctrl_id),
                self.__VALUE_PACKER__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_PACKER__.unpack(value_part)
        return value

# EOF
