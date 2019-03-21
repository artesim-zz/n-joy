import collections
import gevent
import zmq.green as zmq

from njoy_core.common.messages import ControlEvent


class Actuator(gevent.Greenlet):
    def __init__(self, context, output_endpoint, identity):
        super().__init__()
        self._ctx, self._socket = self._zmq_setup(context, output_endpoint, identity)
        self._value = None
        self._output_queue = collections.deque(maxlen=1)

    @staticmethod
    def _zmq_setup(context, output_endpoint, identity):
        socket = context.socket(zmq.REQ)
        socket.set(zmq.IDENTITY, identity)
        socket.connect(output_endpoint)
        return context, socket

    @property
    def identity(self):
        return self._socket.get(zmq.IDENTITY)

    @property
    def value(self):
        while self._value is None:
            # Wait a millisecond between each read attempt, to give a chance for other greenlets to run
            gevent.sleep(0.001)
        return self._value

    @value.setter
    def value(self, val):
        if val != self._value:
            self._value = val
            self._output_queue.appendleft(val)

    def _run(self):
        while True:
            while len(self._output_queue) == 0:
                gevent.sleep(0.001)
            ControlEvent(value=self._output_queue.pop()).send(self._socket)
            ControlEvent.recv(self._socket)


class AxisActuator(Actuator):
    pass


class ButtonActuator(Actuator):
    pass


class HatActuator(Actuator):
    pass

# EOF
