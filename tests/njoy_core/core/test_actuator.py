import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.actuator import Actuator
from njoy_core.common.messages import ControlEvent

ZMQ_CONTEXT = zmq.Context()


class MockControl(gevent.Greenlet):
    def __init__(self, context, output_endpoint, identity):
        super().__init__()
        self._actuator = Actuator(context=context,
                                  output_endpoint=output_endpoint,
                                  identity=identity)

    def _run(self):
        grp = gevent.pool.Group()
        grp.start(self._actuator)

        i = 0
        while True:
            self._actuator.value = (random.randrange(2) == 0)
            i += 1
            if i % 1000 == 0:
                print("Control: set {} values".format(i))
            gevent.sleep(0.001)

            if random.randrange(10000) == 42:
                print("Router: Pausing 5s...")
                gevent.sleep(5)


class MockRouter(gevent.Greenlet):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.REP)
        self._socket.bind(endpoint)

    def _run(self):
        received = 0
        while True:
            ControlEvent.recv(self._socket)
            received += 1
            if received % 100 == 0:
                print("Router: received {} messages".format(received))
            ControlEvent().send(self._socket)


if __name__ == '__main__':
    random.seed()

    control = MockControl(context=ZMQ_CONTEXT,
                          output_endpoint='inproc://output',
                          identity='control')

    router = MockRouter(context=ZMQ_CONTEXT,
                        endpoint='inproc://output')

    grp = gevent.pool.Group()
    grp.start(control)
    grp.start(router)
    grp.join()

# EOF
