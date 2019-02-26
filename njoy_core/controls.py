import gevent
import zmq.green as zmq

from njoy_core.messages import Message, MessageType, HidAxisEvent, HidButtonEvent, HidHatEvent


class Control(gevent.Greenlet):
    """High level abstraction of an individual control (button, hat, axis, etc.) of an input device."""

    def __init__(self, virtual_joystick, virtual_ctrl_id, ctrl, hid_event_loop):
        super(Control, self).__init__()
        self._hid_event_loop = hid_event_loop
        self._virtual_joystick = virtual_joystick
        self._virtual_ctrl_id = virtual_ctrl_id
        self._ctx = hid_event_loop.ctx
        self._subscribe_filter = ctrl.msg_header
        self._value = None

    def _run(self):
        socket_in = self._ctx.socket(zmq.SUB)
        socket_in.connect(self._hid_event_loop.events_endpoint)
        socket_in.setsockopt(zmq.SUBSCRIBE, self._subscribe_filter)

        socket_out = self._ctx.socket(zmq.PUSH)
        socket_out.connect(self._virtual_joystick.events_endpoint)

        while True:
            msg = Message.recv(socket_in)

            if msg.msg_type == MessageType.HID_AXIS_EVENT:
                HidAxisEvent(self._virtual_joystick.device_id, self._virtual_ctrl_id, msg.value).send(socket_out)

            elif msg.msg_type == MessageType.HID_BUTTON_EVENT:
                HidButtonEvent(self._virtual_joystick.device_id, self._virtual_ctrl_id, msg.state).send(socket_out)

            elif msg.msg_type == MessageType.HID_HAT_EVENT:
                HidHatEvent(self._virtual_joystick.device_id, self._virtual_ctrl_id, msg.value).send(socket_out)
