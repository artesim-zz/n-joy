import gevent
import zmq.green as zmq

from njoy_core.common.messages import ControlEvent


class InputMultiplexer(gevent.Greenlet):
    def __init__(self, context, internal_endpoint, external_endpoint):
        super().__init__()
        self._ctx = context
        self._frontend = context.socket(zmq.PULL)
        self._frontend.bind(external_endpoint)
        self._backend = context.socket(zmq.PUB)
        self._backend.bind(internal_endpoint)

    def _run(self):
        zmq.proxy(self._frontend, self._backend)


class MockOutputMultiplexer(gevent.Greenlet):
    def __init__(self, context, internal_endpoint, external_endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.REP)
        self._socket.bind(internal_endpoint)

    def _run(self):
        received = 0
        while True:
            ControlEvent.recv(self._socket)
            received += 1
            if received % 100 == 0:
                print("Output MUX: received {} messages".format(received))
            ControlEvent().send(self._socket)


# XXX: tmp
OutputMultiplexer = MockOutputMultiplexer


# EOF
