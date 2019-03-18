#
# WARNING:
# Need to set PYSDL2_DLL_PATH=../../../lib64/sdl2 for this test
#

import zmq.green as zmq
import gevent.pool

from njoy_core.common.messages import HidRequest, HidReply, NamedControlEvent
from njoy_core.input_node import EmbeddedInputNode

ZMQ_CONTEXT = zmq.Context()


class MockInputRouter(gevent.Greenlet):
    def __init__(self, context, events_endpoint, requests_endpoint):
        super().__init__()
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._requests_endpoint = requests_endpoint

    def _handle_input_events(self):
        socket = self._ctx.socket(zmq.PULL)
        socket.bind(self._events_endpoint)

        while True:
            msg = NamedControlEvent.recv(socket)
            print("InputRouter: {} = {}".format(msg.identity, msg.value))

    def _handle_requests(self):
        socket = self._ctx.socket(zmq.REP)
        socket.bind(self._requests_endpoint)
        while True:
            msg = HidRequest.recv(socket)
            HidReply('registered', *msg.args).send(socket)

    def _run(self):
        grp = gevent.pool.Group()
        grp.spawn(self._handle_input_events)
        grp.spawn(self._handle_requests)
        grp.join()


if __name__ == '__main__':
    router = MockInputRouter(context=ZMQ_CONTEXT,
                             events_endpoint='inproc://router_events',
                             requests_endpoint='inproc://router_requests')

    input_node = EmbeddedInputNode(context=ZMQ_CONTEXT,
                                   events_endpoint='inproc://router_events',
                                   requests_endpoint='inproc://router_requests')

    router.start()
    input_node.start()
    router.join()
    input_node.join()

# EOF
