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
        while True:
            # Consume the input events as fast as we can, collecting the states in a dict.
            # Older unprocessed states are discarded.
            event = ControlEvent.recv(self._socket)

            if event.identity not in input_values:
                input_values[event.identity] = event.value
                changed = True
            elif input_values[event.identity] != event.value:
                input_values[event.identity] = event.value
                changed = True
            else:
                changed = False

            # Once we have a full set of input values, put them in the output queue.
            if changed and len(input_values) == self._nb_inputs:
                self._output_queue.appendleft(input_values)

    @property
    def input_values(self):
        if len(self._output_queue) > 0:
            return self._output_queue.pop()
        else:
            return None
