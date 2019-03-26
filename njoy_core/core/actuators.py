import collections
import threading
import time
import zmq

from njoy_core.core.messages import ControlEvent


class Actuator(threading.Thread):
    def __init__(self, *, context, outputs, identity):
        super().__init__()
        self._ctx = context
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.set(zmq.IDENTITY, identity.packed())
        self._socket.connect(outputs)
        self._value = None
        self._output_queue = collections.deque(maxlen=1)

    @property
    def identity(self):
        return self._socket.get(zmq.IDENTITY)

    @property
    def value(self):
        while self._value is None:
            # Wait 100 µs between each read attempt, to give a chance for other threads to run
            time.sleep(0.0001)
        return self._value

    @value.setter
    def value(self, val):
        if val != self._value:
            self._value = val
            self._output_queue.appendleft(val)

    def loop(self, socket):
        while len(self._output_queue) == 0:
            # Wait 100 µs between each read attempt, to give a chance for other threads to run
            time.sleep(0.0001)

        ControlEvent(value=self._output_queue.pop()).send(socket)
        ControlEvent.recv(socket)

    def run(self):
        while True:
            self.loop(self._socket)


class AxisActuator(Actuator):
    pass


class ButtonActuator(Actuator):
    pass


class HatActuator(Actuator):
    pass
