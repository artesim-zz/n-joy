import threading
import zmq

from njoy_core.core.messages import ControlEvent


class InputMultiplexer(threading.Thread):
    def __init__(self, *, context, frontend, backend):
        super().__init__()
        self._ctx = context
        self._frontend = self._ctx.socket(zmq.PULL)
        self._frontend.bind(frontend)
        self._backend = self._ctx.socket(zmq.PUB)
        self._backend.bind(backend)

    def run(self):
        zmq.proxy(self._frontend, self._backend)


class OutputMultiplexer(threading.Thread):
    def __init__(self, *, context, frontend, backend):
        super().__init__()
        self._ctx = context
        self._frontend = self._ctx.socket(zmq.ROUTER)
        self._frontend.bind(frontend)
        self._backend = self._ctx.socket(zmq.ROUTER)
        self._backend.bind(backend)
        self._received = 0

    def loop(self, frontend, backend):
        ControlEvent.recv(backend)
        self._received += 1
        if self._received % 100 == 0:
            print("Output MUX: received {} messages".format(self._received))
        ControlEvent().send(backend)

    def run(self):
        while True:
            self.loop(self._frontend, self._backend)
