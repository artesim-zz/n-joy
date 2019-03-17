import multiprocessing
import threading
import zmq

from .hid_event_loop import HidEventLoop


class EmbeddedInputNode(threading.Thread):
    def __init__(self, context, events_endpoint, requests_endpoint):
        super().__init__()
        self._hid_event_loop = HidEventLoop(context, events_endpoint, requests_endpoint)

    def run(self):
        self._hid_event_loop.run()


class ExternalInputNode(multiprocessing.Process):
    def __init__(self, events_endpoint, requests_endpoint):
        super().__init__()
        self._ctx = zmq.Context()
        self._hid_event_loop = HidEventLoop(self._ctx, events_endpoint, requests_endpoint)

    def run(self):
        self._hid_event_loop.run()


class StandaloneInputNode:
    def __init__(self):
        pass  # TODO: get the nJoy core endpoints from settings and instantiate the event loop with that
