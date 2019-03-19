import gevent.pool

from .filtering_buffer import FilteringBuffer
from .actuator import Actuator


class Control(gevent.Greenlet):
    def __init__(self, context, input_endpoint, input_identities, output_endpoint, identity):
        super().__init__()
        self._buffer = FilteringBuffer(context=context,
                                       input_endpoint=input_endpoint,
                                       input_identities=input_identities)
        self._actuator = Actuator(context=context,
                                  output_endpoint=output_endpoint,
                                  identity=identity)
        self.identity = identity

    def _process(self, values):
        # XXX: This is where we should inject an algorithm, that somehow comes up from parsing the nJoy Design.
        raise NotImplementedError

    def _run(self):
        grp = gevent.pool.Group()
        grp.start(self._buffer)
        grp.start(self._actuator)

        while True:
            values = self._buffer.input_values
            if values is not None:
                self._actuator.value = self._process(values)

            # Wait a millisecond between each read attempt, to give a chance for other greenlets to run
            gevent.sleep(0.001)


class TmpOneToOneControl(Control):
    def _process(self, values):
        if all([isinstance(v, bool) for v in values.values()]):
            return all(values.values())
        else:
            return list(values.values())[0]

# EOF
