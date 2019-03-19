import collections
import gevent
import zmq.green as zmq

from njoy_core.common.messages import ControlEvent


class FilteringBuffer(gevent.Greenlet):
    def __init__(self, context, input_endpoint, input_identities):
        super().__init__()
        self._ctx, self._socket = self._zmq_setup(context, input_endpoint, input_identities)
        self._nb_inputs = len(input_identities)
        self._output_queue = collections.deque(maxlen=2)

    @staticmethod
    def _zmq_setup(context, input_endpoint, input_identities):
        socket = context.socket(zmq.SUB)
        socket.connect(input_endpoint)
        for identity in input_identities:
            socket.subscribe(identity)
        return context, socket

    def _run(self):
        input_values = dict()

        # First loop : receive inputs until we get a first full set
        while len(input_values) != self._nb_inputs:
            event = ControlEvent.recv(self._socket)
            input_values[event.identity] = event.value

        # Put that first full set in the output queue
        self._output_queue.appendleft(input_values)

        # Start the actual event loop : now we only test for changes
        while True:
            # Consume the input events as fast as we can, collecting the states in a dict.
            # Older unprocessed states are discarded.
            event = ControlEvent.recv(self._socket)

            if input_values[event.identity] != event.value:
                input_values[event.identity] = event.value
                self._output_queue.appendleft(input_values)

    @property
    def input_values(self):
        if len(self._output_queue) > 0:
            return self._output_queue.pop()
        else:
            return None
