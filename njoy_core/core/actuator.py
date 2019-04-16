import threading
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
        self._input_buffer = InputBuffer(context=context,
                                         input_endpoint=input_endpoint,
                                         physical_controls=virtual_control.input_controls)

    def loop(self):
        VirtualControlEvent(value=self._virtual_control.processor(self._input_buffer.state)).send(self._socket)
        VirtualControlEvent.recv(self._socket)

    def run(self):
        self._input_buffer.start()
        while True:
            self.loop()
