import gevent
import zmq.green as zmq

from njoy_core.messages import Message


class Control(gevent.Greenlet):
    """High level abstraction of an individual control (button, hat, axis, etc.) of an input device."""

    def __init__(self, context, input_endpoint, ctrl):
        super(Control, self).__init__()
        self._ctx = context
        self._input_endpoint = input_endpoint
        self._subscribe_filter = ctrl.msg_header

        self._device_id, self._ctrl_type, self._ctrl_id = ctrl.as_key
        self._value = None

    def __repr__(self):
        return '<Control #{}/{}/{}>'.format(self._device_id, self._ctrl_type, self._ctrl_id)

    def _run(self):
        socket = self._ctx.socket(zmq.SUB)
        socket.connect(self._input_endpoint)
        socket.setsockopt(zmq.SUBSCRIBE, self._subscribe_filter)
        while True:
            msg = Message.recv(socket)
            print('{} received {}'.format(self, msg))
            gevent.sleep(0)
