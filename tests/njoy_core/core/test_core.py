import random
import zmq.green as zmq
import gevent.pool

from njoy_core.common.messages import HatValue, ControlEvent
from njoy_core.common.messages import InputNodeRegisterRequest, InputNodeRegisterReply
from njoy_core.core import Core

ZMQ_CONTEXT = zmq.Context()


class MockInputNode(gevent.Greenlet):
    def __init__(self, context, requests_endpoint, events_endpoint):
        super().__init__()
        self._ctx = context
        self._requests_socket = context.socket(zmq.REQ)
        self._requests_socket.connect(requests_endpoint)
        self._events_socket = context.socket(zmq.PUSH)
        self._events_socket.connect(events_endpoint)

    def _register(self):
        # First send our list of joysticks to njoy_core
        InputNodeRegisterRequest(devices=['Joystick - HOTAS Warthog',
                                          'Throttle - HOTAS Warthog']).send(self._requests_socket)
        print("Input Node: sent request")

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(self._requests_socket)
        print("Input Node: Received answer")
        return reply

    def _events_loop(self):
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

            ControlEvent(**identity, value=value).send(self._events_socket)
            sent += 1
            if sent % 1000 == 0:
                print("Mux In: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Mux In: Pausing 10s...")
                gevent.sleep(10)
            else:
                gevent.sleep(0.001)

    def _run(self):
        self._register()
        self._events_loop()


def main():
    random.seed()

    input_node = MockInputNode(context=ZMQ_CONTEXT,
                               requests_endpoint='inproc://requests',
                               events_endpoint='inproc://input')

    core = Core(context=ZMQ_CONTEXT,
                input_events_endpoint='inproc://input',
                output_events_endpoint='inproc://output',
                requests_endpoint='inproc://requests')

    grp = gevent.pool.Group()
    grp.start(input_node)
    grp.start(core)
    grp.join()


if __name__ == '__main__':
    main()

# EOF
