import collections
import threading
import zmq

from njoy_core.core.messages import PhysicalControlEvent


class InputBuffer(threading.Thread):
    def __init__(self, *, context, input_endpoint, physical_controls):
        super().__init__()

        self._ctx = context
        self._socket = context.socket(zmq.SUB)
        self._socket.connect(input_endpoint)
        for control in physical_controls:
            self._socket.subscribe(PhysicalControlEvent.mk_identity(control))

        self._state = {c: None for c in physical_controls}
        self._output_queue = collections.deque(maxlen=2)

    def _publish_state(self):
        self._output_queue.appendleft({c: s for (c, s) in self._state.items()})

    def initial_loop(self, socket):
        while any([value is None for value in self._state.values()]):
            event = PhysicalControlEvent.recv(socket)
            self._state[event.control] = event.value

        # Put that first full set in the output queue
        self._publish_state()

    def loop(self, socket):
        # Consume the input events as fast as we can, collecting the states in a dict.
        # Older unprocessed states are discarded.
        event = PhysicalControlEvent.recv(socket)

        if self._state[event.control] != event.value:
            self._state[event.control] = event.value
            self._publish_state()

    def run(self):
        # First loop : receive inputs until we get a first full set
        self.initial_loop(self._socket)

        # Then start the actual event loop : now we only test for changes
        while True:
            self.loop(self._socket)

    @property
    def state(self):
        if len(self._output_queue) > 0:
            return self._output_queue.pop()
        else:
            return None
