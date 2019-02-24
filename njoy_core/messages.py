import enum
import struct


class MessageException(Exception):
    pass


@enum.unique
class HidControlType(enum.IntEnum):
    AXIS = 0
    BALL = 1
    BUTTON = 2
    HAT = 3


class HidEvent:
    __TOPIC_STRUCT__ = struct.Struct('>IBI')

    def __init__(self, joystick_instance_id, ctrl_type, ctrl_id):
        self._instance_id = joystick_instance_id
        self._type = ctrl_type
        self._id = ctrl_id

    @property
    def instance_id(self):
        return self._instance_id

    @property
    def type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def msg_parts(self):
        return [self.__TOPIC_STRUCT__.pack(self._instance_id, self._type, self._id)]

    @classmethod
    def from_msg_parts(cls, msg_parts):
        instance_id, ctrl_type, ctrl_id = cls.__TOPIC_STRUCT__.unpack(msg_parts[0])

        if ctrl_type == HidControlType.AXIS:
            return HidAxisEvent(joystick_instance_id=instance_id,
                                ctrl_id=ctrl_id,
                                value=HidAxisEvent.from_value_parts(*msg_parts[1:]))

        elif ctrl_type == HidControlType.BALL:
            dx, dy = HidBallEvent.from_value_parts(*msg_parts[1:])
            return HidBallEvent(joystick_instance_id=instance_id,
                                ctrl_id=ctrl_id,
                                dx=dx,
                                dy=dy)

        elif ctrl_type == HidControlType.BUTTON:
            return HidButtonEvent(joystick_instance_id=instance_id,
                                  ctrl_id=ctrl_id,
                                  state=HidButtonEvent.from_value_parts(*msg_parts[1:]))

        elif ctrl_type == HidControlType.HAT:
            return HidHatEvent(joystick_instance_id=instance_id,
                               ctrl_id=ctrl_id,
                               value=HidHatEvent.from_value_parts(*msg_parts[1:]))

        else:
            raise MessageException("Invalid HidControlType")

    def send(self, socket):
        socket.send_multipart(self.msg_parts)

    @classmethod
    def recv(cls, socket):
        return cls.from_msg_parts(socket.recv_multipart())


class HidAxisEvent(HidEvent):
    __VALUE_STRUCT__ = struct.Struct('>i')

    def __init__(self, joystick_instance_id, ctrl_id, value):
        super(HidAxisEvent, self).__init__(joystick_instance_id, HidControlType.AXIS, ctrl_id)
        self._value = value

    def __repr__(self):
        return '<HidAxisEvent: /{}/axis/{} = {}>'.format(self._instance_id, self._id, self._value)

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        topic, = super(HidAxisEvent, self).msg_parts
        return [topic, self.__VALUE_STRUCT__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_STRUCT__.unpack(value_part)
        return value


class HidBallEvent(HidEvent):
    __VALUE_STRUCT__ = struct.Struct('>ii')

    def __init__(self, joystick_instance_id, ctrl_id, dx, dy):
        super(HidBallEvent, self).__init__(joystick_instance_id, HidControlType.BALL, ctrl_id)
        self._dx = dx
        self._dy = dy

    def __repr__(self):
        return '<HidBallEvent: /{}/ball/{} = ({}, {})>'.format(self._instance_id,
                                                               self._id, self._dx, self._dy)

    @property
    def dx(self):
        return self._dx

    @property
    def dy(self):
        return self._dy

    @property
    def msg_parts(self):
        topic, = super(HidBallEvent, self).msg_parts
        return [topic, self.__VALUE_STRUCT__.pack(self._dx, self._dy)]

    @classmethod
    def from_value_parts(cls, value_part):
        dx, dy, = cls.__VALUE_STRUCT__.unpack(value_part)
        return dx, dy


class HidButtonEvent(HidEvent):
    __VALUE_STRUCT__ = struct.Struct('>?')

    def __init__(self, joystick_instance_id, ctrl_id, state):
        super(HidButtonEvent, self).__init__(joystick_instance_id, HidControlType.BUTTON, ctrl_id)
        self._state = state

    def __repr__(self):
        return '<HidButtonEvent: /{}/button/{} = {}>'.format(self._instance_id, self._id, self._state)

    @property
    def state(self):
        return self._state

    @property
    def msg_parts(self):
        topic, = super(HidButtonEvent, self).msg_parts
        return [topic, self.__VALUE_STRUCT__.pack(self._state)]

    @classmethod
    def from_value_parts(cls, value_part):
        state, = cls.__VALUE_STRUCT__.unpack(value_part)
        return state


class HidHatEvent(HidEvent):
    __VALUE_STRUCT__ = struct.Struct('>B')

    def __init__(self, joystick_instance_id, ctrl_id, value):
        super(HidHatEvent, self).__init__(joystick_instance_id, HidControlType.HAT, ctrl_id)
        self._value = value

    def __repr__(self):
        return '<HidHatEvent: /{}/hat/{} = {}>'.format(self._instance_id, self._id, self._value)

    @property
    def value(self):
        return self._value

    @property
    def msg_parts(self):
        topic, = super(HidHatEvent, self).msg_parts
        return [topic, self.__VALUE_STRUCT__.pack(self._value)]

    @classmethod
    def from_value_parts(cls, value_part):
        value, = cls.__VALUE_STRUCT__.unpack(value_part)
        return value

# EOF
