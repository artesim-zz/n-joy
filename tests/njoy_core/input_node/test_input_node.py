#
# WARNING:
# Need to set PYSDL2_DLL_PATH=../../../lib64/sdl2 for this test
#

import zmq.green as zmq
import gevent.pool

from njoy_core.common.messages import InputNodeRegisterRequest, InputNodeRegisterReply, ControlEvent
from njoy_core.input_node import EmbeddedInputNode

ZMQ_CONTEXT = zmq.Context()


class MockInputMultiplexer(gevent.Greenlet):
    def __init__(self, context, events_endpoint, requests_endpoint):
        super().__init__()
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._requests_endpoint = requests_endpoint
        self._registered_devices = dict()

    def _handle_input_events(self):
        socket = self._ctx.socket(zmq.PULL)
        socket.bind(self._events_endpoint)

        while True:
            msg = ControlEvent.recv(socket)
            print("InputRouter: /Node{}/{}/{}/{} = {}".format(msg.node,
                                                              self._registered_devices[msg.node][msg.device],
                                                              msg.kind.short_str(),
                                                              msg.control,
                                                              msg.value))

    def _handle_requests(self):
        socket = self._ctx.socket(zmq.REP)
        socket.bind(self._requests_endpoint)
        while True:
            request = InputNodeRegisterRequest.recv(socket)
            node_id = len(self._registered_devices)
            accepted_devices = enumerate(filter(lambda d: d != 'vJoy Device', request.devices))
            self._registered_devices[node_id] = {i: name for (i, name) in accepted_devices}
            InputNodeRegisterReply(node_id=node_id,
                                   device_ids_map=self._registered_devices[node_id]).send(socket)

    def _run(self):
        grp = gevent.pool.Group()
        grp.spawn(self._handle_input_events)
        grp.spawn(self._handle_requests)
        grp.join()


def main():
    mux_in = MockInputMultiplexer(context=ZMQ_CONTEXT,
                                  events_endpoint='inproc://router_events',
                                  requests_endpoint='inproc://router_requests')

    input_node = EmbeddedInputNode(context=ZMQ_CONTEXT,
                                   events_endpoint='inproc://router_events',
                                   requests_endpoint='inproc://router_requests')

    mux_in.start()
    input_node.start()
    mux_in.join()
    input_node.join()


if __name__ == '__main__':
    main()
