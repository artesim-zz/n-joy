import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.actuators import Actuator
from njoy_core.common.messages import HatValue, ControlEvent

ZMQ_CONTEXT = zmq.Context()


class MockControl(gevent.Greenlet):
    __KIND__ = NotImplemented

    def __init__(self, context, output_endpoint, identity):
        super().__init__()
        self._actuator = Actuator(context=context,
                                  output_endpoint=output_endpoint,
                                  identity=identity)
        self._identity = identity

    def _set_random_value(self):
        raise NotImplementedError

    def _run(self):
        grp = gevent.pool.Group()
        grp.start(self._actuator)

        i = 0
        while True:
            self._set_random_value()
            i += 1
            if i % 1000 == 0:
                print("{} {} : set {} values".format(self.__KIND__, self._identity, i))
            gevent.sleep(0.001)

            if random.randrange(10000) == 42:
                print("{} {} : Pausing 5s...".format(self.__KIND__, self._identity))
                gevent.sleep(5)


class MockButton(MockControl):
    __KIND__ = 'Button'

    def _set_random_value(self):
        self._actuator.value = (random.randrange(2) == 0)


class MockHat(MockControl):
    __KIND__ = 'Hat'

    def _set_random_value(self):
        self._actuator.value = random.choice(list(HatValue))


class MockAxis(MockControl):
    __KIND__ = 'Axis'

    def _set_random_value(self):
        self._actuator.value = random.uniform(-1.0, 1.0)


class MockOutputMultiplexer(gevent.Greenlet):
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


def main():
    random.seed()

    button = MockButton(context=ZMQ_CONTEXT,
                        output_endpoint='inproc://output',
                        identity=ControlEvent(node=0, device=0, control=0).identity)

    hat = MockHat(context=ZMQ_CONTEXT,
                  output_endpoint='inproc://output',
                  identity=ControlEvent(node=1, device=1, control=1).identity)

    axis = MockAxis(context=ZMQ_CONTEXT,
                    output_endpoint='inproc://output',
                    identity=ControlEvent(node=2, device=2, control=2).identity)

    output_multiplexer = MockOutputMultiplexer(context=ZMQ_CONTEXT,
                                               endpoint='inproc://output')

    grp = gevent.pool.Group()
    grp.start(button)
    grp.start(hat)
    grp.start(axis)
    grp.start(output_multiplexer)
    grp.join()


if __name__ == '__main__':
    main()

# EOF
