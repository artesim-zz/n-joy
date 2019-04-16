import multiprocessing
import threading
import zmq

from njoy_core.core.model import OutputNodeCapabilities, OutputNodeAssignments
from .virtual_joystick import VirtualJoystick


class OutputNodeException(Exception):
    pass


class StandaloneOutputNode:
    def __init__(self, context, requests_endpoint, events_endpoint):
        self._ctx = context
        self._requests_endpoint = requests_endpoint
        self._events_endpoint = events_endpoint

    def _request_assignments(self):
        socket = self._ctx.socket(zmq.REQ)
        socket.connect(self._requests_endpoint)
        OutputNodeCapabilities(capabilities=VirtualJoystick.device_capabilities()).send(socket)
        reply = OutputNodeAssignments.recv(socket)
        return reply.node

    def run(self):
        virtual_joysticks = [VirtualJoystick(device=device,
                                             context=self._ctx,
                                             events_endpoint=self._events_endpoint)
                             for device in self._request_assignments()]

        for vj in virtual_joysticks:
            vj.start()

        for vj in virtual_joysticks:
            vj.join()


class EmbeddedOutputNode(threading.Thread):
    def __init__(self, context, requests_endpoint, events_endpoint):
        super().__init__()
        self._ctx = context
        self._node = StandaloneOutputNode(self._ctx, requests_endpoint, events_endpoint)

    def run(self):
        self._node.run()


class ExternalOutputNode(multiprocessing.Process):
    def __init__(self, requests_endpoint, events_endpoint):
        super().__init__()
        self._ctx = zmq.Context()
        self._node = StandaloneOutputNode(self._ctx, requests_endpoint, events_endpoint)

    def run(self):
        self._node.run()


if __name__ == '__main__':
    # TODO: get the nJoy core endpoints from settings and instantiate StandaloneOutputNode with that
    # context = zmq.Context()
    # StandaloneOutputNode(context, requests_endpoint, events_endpoint).run()
    pass
