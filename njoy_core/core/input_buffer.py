import collections
import threading
import time
import zmq

from njoy_core.core.model import PhysicalControlEvent


class InputBuffer(threading.Thread):
    """Input Buffer for the Actuators.

    It has two consecutive loops :
    - The initial loop collects events until we have a full set of control values.
      When we do, this full state is put in an internal queue, so it can be consumed
      when reading the state property.
      The internal queue remains empty during this phase.

    - The main loop collects events as fast as it can, but only publishes a new state when something changed.

    The state property is a blocking call, which is waiting for a state to be put in the queue
    It then pops and return it, so each state change is only consumed once."""

    def __init__(self, *, context, input_endpoint, physical_controls):
        super().__init__()

        self._ctx = context
        self._socket = context.socket(zmq.SUB)
        self._socket.connect(input_endpoint)
        for control in physical_controls:
            self._socket.subscribe(PhysicalControlEvent.mk_identity(control))

        self._state = {c: None for c in physical_controls}
        self._state_queue = collections.deque(maxlen=2)

    def _publish_state(self):
        self._state_queue.appendleft({c: s for (c, s) in self._state.items()})

    def initial_loop(self):
        # Consume the first events and collect them
        event = PhysicalControlEvent.recv(self._socket)
        self._state[event.control] = event.value

        # Delay publishing into the output queue until we have a first full set
        if not any([value is None for value in self._state.values()]):
            self._publish_state()

    def loop(self):
        # Consume the input events as fast as we can, collecting the states in a dict.
        # Older unprocessed states are discarded.
        event = PhysicalControlEvent.recv(self._socket)

        if self._state[event.control] != event.value:
            self._state[event.control] = event.value
            self._publish_state()

    def run(self):
        # First loop : receive inputs until we get a first full set
        while not self._state_queue:
            self.initial_loop()

        # Then start the actual event loop : now we only test for changes
        while True:
            self.loop()

    @property
    def state(self):
        # Blocking call : wait 100 µs between each read attempt, to give a chance for other threads to run
        while not self._state_queue:
            time.sleep(0.0001)
        return self._state_queue.pop()
