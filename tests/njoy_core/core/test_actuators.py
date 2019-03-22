import random
import threading
import time
import zmq

from njoy_core.core.actuators import Actuator
from njoy_core.common.messages import HatValue, ControlEvent, CtrlKind, control_identity


class MockControl(threading.Thread):
    __KIND__ = NotImplemented

    def __init__(self, context, output, identity):
        super().__init__()
        self._actuator = Actuator(context=context,
                                  outputs=output,
                                  identity=identity)
        self._identity = identity

    def _set_random_value(self):
        raise NotImplementedError

    def run(self):
        print("{} {} : starting actuator".format(self.__KIND__, self._identity))
        self._actuator.start()

        print("{} {} : starting loop".format(self.__KIND__, self._identity))
        i = 0
        while True:
            self._set_random_value()
            i += 1
            if i % 1000 == 0:
                print("{} {} : set {} values".format(self.__KIND__, self._identity, i))

            if random.randrange(10000) == 42:
                print("{} {} : Pausing 5s...".format(self.__KIND__, self._identity))
                time.sleep(5)
            else:
                time.sleep(0.001)


class MockButton(MockControl):
    __KIND__ = 'Button'

    def _set_random_value(self):
        self._actuator.value = (random.randrange(2) == 0)


class MockHat(MockControl):
    __KIND__ = 'Hat'

    def _set_random_value(self):
        self._actuator.value = random.choice(HatValue.list())


class MockAxis(MockControl):
    __KIND__ = 'Axis'

    def _set_random_value(self):
        self._actuator.value = random.uniform(-1.0, 1.0)


class MockOutputMultiplexer(threading.Thread):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.REP)
        self._socket.bind(endpoint)

    def run(self):
        received = 0
        print("Mux Out: Starting loop")
        while True:
            ControlEvent.recv(self._socket)
            received += 1
            if received % 100 == 0:
                print("Mux Out: received {} messages".format(received))
            ControlEvent().send(self._socket)


def main():
    context = zmq.Context()

    random.seed()

    axis = MockAxis(context=context,
                    output='inproc://output',
                    identity=control_identity(node=2, device=2, kind=CtrlKind.AXIS, control=2))

    button = MockButton(context=context,
                        output='inproc://output',
                        identity=control_identity(node=0, device=0, kind=CtrlKind.BUTTON, control=0))

    hat = MockHat(context=context,
                  output='inproc://output',
                  identity=control_identity(node=1, device=1, kind=CtrlKind.HAT, control=1))

    output_multiplexer = MockOutputMultiplexer(context=context,
                                               endpoint='inproc://output')

    axis.start()
    button.start()
    hat.start()
    output_multiplexer.start()
    for t in [axis, button, hat, output_multiplexer]:
        t.join()


if __name__ == '__main__':
    main()
