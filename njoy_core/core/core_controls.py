import threading
import time

from .input_buffers import InputBuffer
from .actuators import Actuator


class CoreControl(threading.Thread):
    def __init__(self, *, context, inputs, input_identities, outputs, identity):
        super().__init__()
        self._buffer = InputBuffer(context=context,
                                   inputs=inputs,
                                   input_identities=input_identities)
        self._actuator = Actuator(context=context,
                                  outputs=outputs,
                                  identity=identity)

    @property
    def identity(self):
        return self._actuator.identity

    def _process(self, inputs):
        # XXX: This is where we should inject an algorithm, that somehow comes up from parsing the nJoy Design.
        raise NotImplementedError

    def loop(self):
        inputs = self._buffer.inputs
        if inputs is not None:
            self._actuator.value = self._process(inputs)

    def run(self):
        self._buffer.start()
        self._actuator.start()

        while True:
            self.loop()

            # Wait 100µs between each read attempt, to give a chance for other threads to run
            time.sleep(0.0001)


class Axis(CoreControl):
    def _process(self, inputs):
        return list(inputs.values())[0]


class Button(CoreControl):
    def _process(self, inputs):
        return list(inputs.values())[0]


class Hat(CoreControl):
    def _process(self, inputs):
        return list(inputs.values())[0]


class PseudoButton(CoreControl):
    def _process(self, inputs):
        return not any(inputs.values())
