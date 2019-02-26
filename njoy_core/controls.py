import gevent
import zmq.green as zmq

from njoy_core.messages import Message


class Control(gevent.Greenlet):
    """High level abstraction of an individual control (button, hat, axis, etc.) of an input device."""

    def __init__(self, virtual_joystick, ctrl, hid_event_loop):
        super(Control, self).__init__()
        self._hid_event_loop = hid_event_loop
        self._virtual_joystick = virtual_joystick
        self._ctx = hid_event_loop.ctx
        self._subscribe_filter = ctrl.msg_header
        self._device_id, self._ctrl_type, self._ctrl_id = ctrl.as_key
        self._value = None

    def __repr__(self):
        return '<Control /{}/{}/{}>'.format(self._device_id, self._ctrl_type, self._ctrl_id)

    def _run(self):
        socket_in = self._ctx.socket(zmq.SUB)
        socket_in.connect(self._hid_event_loop.events_endpoint)
        socket_in.setsockopt(zmq.SUBSCRIBE, self._subscribe_filter)

        socket_out = self._ctx.socket(zmq.PUSH)
        socket_out.connect(self._virtual_joystick.events_endpoint)

        while True:
            msg = Message.recv(socket_in)
            msg.send(socket_out)
            gevent.sleep(0)
