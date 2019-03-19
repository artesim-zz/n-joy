import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.control import TmpOneToOneControl
from njoy_core.common.messages import ControlEvent

ZMQ_CONTEXT = zmq.Context()


class MockInputRouter(gevent.Greenlet):
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
            if identity['control'] == 7:
                value = random.uniform(-1, 1)
            else:
                value = 1 == random.randint(0, 1)

            ControlEvent(**identity, value=value).send(self._socket)
            sent += 1
            if sent % 1000 == 0:
                print("Router: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Router: Pausing 10s...")
                gevent.sleep(10)
            else:
                gevent.sleep(0.001)


class MockOutputRouter(gevent.Greenlet):
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

    router_in = MockInputRouter(context=ZMQ_CONTEXT,
                                endpoint='inproc://input')

    router_out = MockOutputRouter(context=ZMQ_CONTEXT,
                                  endpoint='inproc://output')

    controls = [TmpOneToOneControl(context=ZMQ_CONTEXT,
                                   input_endpoint='inproc://input',
                                   input_identities=[ControlEvent(node=0, device=0, control=1).identity],
                                   output_endpoint='inproc://output',
                                   identity=ControlEvent(node=0, device=0, control=0).identity),
                TmpOneToOneControl(context=ZMQ_CONTEXT,
                                   input_endpoint='inproc://input',
                                   input_identities=[ControlEvent(node=0, device=0, control=1).identity,
                                                     ControlEvent(node=0, device=0, control=2).identity,
                                                     ControlEvent(node=0, device=0, control=3).identity],
                                   output_endpoint='inproc://output',
                                   identity=ControlEvent(node=0, device=0, control=1).identity),
                TmpOneToOneControl(context=ZMQ_CONTEXT,
                                   input_endpoint='inproc://input',
                                   input_identities=[ControlEvent(node=0, device=0, control=3).identity],
                                   output_endpoint='inproc://output',
                                   identity=ControlEvent(node=0, device=0, control=2).identity),
                TmpOneToOneControl(context=ZMQ_CONTEXT,
                                   input_endpoint='inproc://input',
                                   input_identities=[ControlEvent(node=0, device=0, control=7).identity],
                                   output_endpoint='inproc://output',
                                   identity=ControlEvent(node=0, device=0, control=3).identity)]

    grp = gevent.pool.Group()
    grp.start(router_in)
    for control in controls:
        grp.start(control)
    grp.start(router_out)
    grp.join()


if __name__ == '__main__':
    main()

# EOF
