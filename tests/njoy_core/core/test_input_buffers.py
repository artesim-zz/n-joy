import random
import threading
import time
import zmq

from njoy_core.core.input_buffers import InputBuffer
from njoy_core.common.messages import ControlEvent, ControlEventKind, control_identity


class MockInputMultiplexer(threading.Thread):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.PUB)
        self._socket.bind(endpoint)

    def run(self):
        identities = [{'node': 0, 'device': 0, 'control': i} for i in range(6)]
        sent = 0
        while True:
            ControlEvent(**random.choice(identities),
                         value=random.randrange(2) == 1).send(self._socket)
            sent += 1
            if sent % 1000 == 0:
                print("Input Mux: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Input Mux: Pausing 5s...")
                time.sleep(5)
            else:
                time.sleep(0.001)


class MockControl(threading.Thread):
    def __init__(self, context, input_endpoint, input_identities):
        super().__init__()
        self._buffer = InputBuffer(context=context,
                                   inputs=input_endpoint,
                                   input_identities=input_identities)
        self._value = None

    def run(self):
        self._buffer.start()

        received = 0
        while True:
            states = self._buffer.inputs
            if states is not None:
                received += 1
                if received % 100 == 0:
                    print("Control: received {} messages".format(received))

            # Simulate random processing time
            time.sleep(0.001 * random.randint(1, 200))


def main():
    context = zmq.Context()

    random.seed()

    multiplexer = MockInputMultiplexer(context=context,
                                       endpoint='inproc://input')

    control = MockControl(context=context,
                          input_endpoint='inproc://input',
                          input_identities=[control_identity(node=0,
                                                             device=0,
                                                             kind=ControlEventKind.BUTTON,
                                                             control=i)
                                            for i in range(3)])
    multiplexer.start()
    control.start()

    multiplexer.join()
    control.join()


if __name__ == '__main__':
    main()
