import collections
import threading
import zmq

from njoy_core.core.messages import ControlEvent


class InputBuffer(threading.Thread):
    def __init__(self, *, context, inputs, input_identities):
        super().__init__()

        self._ctx = context
        self._socket = context.socket(zmq.SUB)
        self._socket.connect(inputs)
        for identity in input_identities:
            self._socket.subscribe(identity.packed())

        self._inputs = dict()
        self._nb_expected_inputs = len(input_identities)
        self._output_queue = collections.deque(maxlen=2)

    def initial_loop(self, socket):
        while len(self._inputs) < self._nb_expected_inputs:
            event = ControlEvent.recv(socket)
            self._inputs[event.identity] = event.value

        # Put that first full set in the output queue
        self._output_queue.appendleft(self._inputs)

    def loop(self, socket):
        # Consume the input events as fast as we can, collecting the states in a dict.
        # Older unprocessed states are discarded.
        event = ControlEvent.recv(socket)

        if self._inputs[event.identity] != event.value:
            self._inputs[event.identity] = event.value
            self._output_queue.appendleft(self._inputs)

    def run(self):
        # First loop : receive inputs until we get a first full set
        self.initial_loop(self._socket)

        # Then start the actual event loop : now we only test for changes
        while True:
            self.loop(self._socket)

    @property
    def inputs(self):
        if len(self._output_queue) > 0:
            return self._output_queue.pop()
        else:
            return None
