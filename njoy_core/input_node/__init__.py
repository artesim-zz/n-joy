import threading
import zmq

import njoy_core.input_node.hid_event_loop


class EmbeddedInputNode(threading.Thread):
    def __init__(self, *, context, events_endpoint, requests_endpoint):
        super().__init__()

        self._ctx = context

        self._events_socket = self._ctx.socket(zmq.PUSH)
        self._events_socket.connect(events_endpoint)

        self._requests_socket = self._ctx.socket(zmq.REQ)
        self._requests_socket.connect(requests_endpoint)

        self._hid_event_loop = njoy_core.input_node.hid_event_loop.HidEventLoop()

    def handshake(self):
        self._hid_event_loop.handshake(self._requests_socket)

    def run(self):
        self.handshake()
        print("Input Node: emitting all initial events")
        self._hid_event_loop.emit_full_state(self._events_socket)
        print("Input Node: starting event loop")
        while True:
            self._hid_event_loop.loop(self._events_socket)
