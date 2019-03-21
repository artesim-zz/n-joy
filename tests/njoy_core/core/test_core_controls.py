import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.core_controls import Axis, Button, Hat, PseudoButton
from njoy_core.common.messages import HatValue, ControlEvent, ControlEventKind, control_identity

ZMQ_CONTEXT = zmq.Context()


class MockInputMultiplexer(gevent.Greenlet):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.PUB)
        self._socket.bind(endpoint)

    def _run(self):
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
                gevent.sleep(10)
            else:
                gevent.sleep(0.001)


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
                print("Mux Out: received {} messages".format(received))
            ControlEvent().send(self._socket)


def main():
    random.seed()

    mux_in = MockInputMultiplexer(context=ZMQ_CONTEXT,
                                  endpoint='inproc://input')

    mux_out = MockOutputMultiplexer(context=ZMQ_CONTEXT,
                                    endpoint='inproc://output')

    controls = [Axis(context=ZMQ_CONTEXT,
                     input_endpoint='inproc://input',
                     input_identities=[control_identity(node=0, device=0, kind=ControlEventKind.AXIS, control=7)],
                     output_endpoint='inproc://output',
                     identity=control_identity(node=0, device=0, kind=ControlEventKind.AXIS, control=0)),
                Button(context=ZMQ_CONTEXT,
                       input_endpoint='inproc://input',
                       input_identities=[control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=0)],
                       output_endpoint='inproc://output',
                       identity=control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=1)),
                Hat(context=ZMQ_CONTEXT,
                    input_endpoint='inproc://input',
                    input_identities=[control_identity(node=0, device=0, kind=ControlEventKind.HAT, control=9)],
                    output_endpoint='inproc://output',
                    identity=control_identity(node=0, device=0, kind=ControlEventKind.HAT, control=2)),
                PseudoButton(context=ZMQ_CONTEXT,
                             input_endpoint='inproc://input',
                             input_identities=[control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=1),
                                               control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=2),
                                               control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=3)],
                             output_endpoint='inproc://output',
                             identity=control_identity(node=0, device=0, kind=ControlEventKind.BUTTON, control=3))]

    grp = gevent.pool.Group()
    grp.start(mux_in)
    for control in controls:
        grp.start(control)
    grp.start(mux_out)
    grp.join()


if __name__ == '__main__':
    main()
