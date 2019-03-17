import multiprocessing
import pickle
import threading
import zmq

from njoy_core.common.messages import Request, Reply
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

        msg_parts = [pickle.dumps(dc) for dc in VirtualJoystick.device_capabilities()]
        Request('register', *msg_parts).send(socket)

        assignments = Reply.recv(socket)
        if assignments.command == 'not_enough_controls':
            raise OutputNodeException("Not enough controls available on all the Virtual Devices")

        elif assignments.command == 'assignments':
            return [pickle.loads(assignment) for assignment in assignments.args]

        else:
            raise OutputNodeException("Unexpected answer : {}".format(assignments.command))

    def run(self):
        virtual_joysticks = [VirtualJoystick(device_id=assignment['device_id'],
                                             controls=assignment['controls'],
                                             context=self._ctx,
                                             events_endpoint=self._events_endpoint)
                             for assignment in self._request_assignments()]

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

# EOF
