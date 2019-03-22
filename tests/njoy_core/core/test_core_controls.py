import random
import threading
import time
import zmq

from njoy_core.core.core_controls import Axis, Button, Hat, PseudoButton
from njoy_core.common.messages import HatValue, ControlEvent, CtrlKind, CtrlIdentity

ZMQ_CONTEXT = zmq.Context()


class MockInputMultiplexer(threading.Thread):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.PUB)
        self._socket.bind(endpoint)

    def run(self):
        identities = [{'node': 0, 'device': 0, 'control': i}
                      for i in range(10)]
        sent = 0
        while True:
            identity = random.choice(identities)
            if identity['control'] in {7, 8}:
                value = random.uniform(-1, 1)
            elif identity['control'] in {9}:
                value = random.choice(HatValue.list())
            else:
                value = random.choice([False, True])

            ControlEvent(**identity, value=value).send(self._socket)
            sent += 1
            if sent % 1000 == 0:
                print("Mux In: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Mux In: Pausing 10s...")
                time.sleep(10)
            else:
                time.sleep(0.001)


class MockOutputMultiplexer(threading.Thread):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.REP)
        self._socket.bind(endpoint)

    def run(self):
        received = 0
        while True:
            ControlEvent.recv(self._socket)
            received += 1
            if received % 100 == 0:
                print("Mux Out: received {} messages".format(received))
            ControlEvent().send(self._socket)


def main():
    random.seed()

    threads = [MockInputMultiplexer(context=ZMQ_CONTEXT,
                                    endpoint='inproc://input'),
               MockOutputMultiplexer(context=ZMQ_CONTEXT,
                                     endpoint='inproc://output'),
               Axis(context=ZMQ_CONTEXT,
                    inputs='inproc://input',
                    input_identities=[CtrlIdentity(node=0, device=0, kind=CtrlKind.AXIS, control=7)],
                    outputs='inproc://output',
                    identity=CtrlIdentity(node=0, device=0, kind=CtrlKind.AXIS, control=0)),
               Button(context=ZMQ_CONTEXT,
                      inputs='inproc://input',
                      input_identities=[CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=0)],
                      outputs='inproc://output',
                      identity=CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=1)),
               Hat(context=ZMQ_CONTEXT,
                   inputs='inproc://input',
                   input_identities=[CtrlIdentity(node=0, device=0, kind=CtrlKind.HAT, control=9)],
                   outputs='inproc://output',
                   identity=CtrlIdentity(node=0, device=0, kind=CtrlKind.HAT, control=2)),
               PseudoButton(context=ZMQ_CONTEXT,
                            inputs='inproc://input',
                            input_identities=[
                                CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=1),
                                CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=2),
                                CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=3)],
                            outputs='inproc://output',
                            identity=CtrlIdentity(node=0, device=0, kind=CtrlKind.BUTTON, control=3))]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()
