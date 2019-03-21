import gevent
from zmq import green as zmq

from njoy_core.common.messages import TypedMessage


class Control(gevent.Greenlet):
    def __init__(self, ctrl_id, runner, *input_controls):
        super().__init__()
        self._ctx = runner.ctx
        self._input_controls = input_controls
        self._endpoint = 'inproc://design-runner/controls/{}'.format(ctrl_id)
        self._ctrl_id = ctrl_id

    @property
    def endpoint(self):
        return self._endpoint

    def _process(self, input_message):
        raise NotImplementedError

    def _run(self):
        socket_in = self._ctx.socket(zmq.SUB)
        for ctrl in self._input_controls:
            socket_in.connect(ctrl.endpoint)
        socket_in.setsockopt(zmq.SUBSCRIBE, b'')

        socket_out = self._ctx.socket(zmq.PUB)
        socket_out.bind(self._endpoint)

        while True:
            msg = TypedMessage.recv(socket_in)
            self._process(msg).send(socket_out)


class Axis(Control):
    def _process(self, input_message):
        raise NotImplementedError
