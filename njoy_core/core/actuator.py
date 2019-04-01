import threading
import time
import zmq

from njoy_core.core.model import VirtualControlEvent
from .input_buffer import InputBuffer


class Actuator(threading.Thread):
    def __init__(self, *, context, input_endpoint, output_endpoint, virtual_control):
        super().__init__()
        self._ctx = context
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.set(zmq.IDENTITY, VirtualControlEvent.mk_identity(virtual_control))
        self._socket.connect(output_endpoint)

        self._virtual_control = virtual_control
        self._input_states = self._init_input_states(virtual_control)
        self._input_buffer = InputBuffer(context=context,
                                         input_endpoint=input_endpoint,
                                         physical_controls=list(self._input_states.keys()))

    def _init_input_states(self, virtual_control):
        physical_controls = virtual_control.physical_inputs
        for physical_control in physical_controls:
            physical_control.processor = lambda _: self._input_states[physical_control]
        return {c: None for c in physical_controls}

    def _update_inputs(self):
        input_states = None
        while input_states is None:
            input_states = self._input_buffer.state
            time.sleep(0.0001)  # Wait 100 µs between each read attempt, to give a chance for other threads to run

        for (c, s) in input_states.items():
            self._input_states[c] = s

    def loop(self, socket):
        self._update_inputs()
        VirtualControlEvent(value=self._virtual_control.state).send(socket)
        VirtualControlEvent.recv(socket)

    def run(self):
        self._input_buffer.start()
        while True:
            self.loop(self._socket)
