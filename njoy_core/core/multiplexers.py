import threading
import zmq

from njoy_core.core.messages import VirtualControlEvent


class OutputMultiplexerError(Exception):
    pass


class InputMultiplexer(threading.Thread):
    def __init__(self, *, context, frontend, backend):
        super().__init__()
        self._ctx = context
        self._frontend = self._ctx.socket(zmq.PULL)
        self._frontend.bind(frontend)
        self._backend = self._ctx.socket(zmq.PUB)
        self._backend.bind(backend)

    def run(self):
        zmq.proxy(self._frontend, self._backend)


class OutputMultiplexer(threading.Thread):
    def __init__(self, *, context, frontend, backend):
        super().__init__()
        self._ctx = context
        self._frontend = self._ctx.socket(zmq.ROUTER)
        self._frontend.bind(frontend)
        self._backend = self._ctx.socket(zmq.ROUTER)
        self._backend.bind(backend)
        self._poller = zmq.Poller()
        self._poller.register(self._backend)
        self._poller.register(self._frontend)
        self._queue = dict()

    def loop(self):
        events = dict(self._poller.poll())

        if self._backend in events:
            event = VirtualControlEvent.recv(self._backend)
            if event.control in self._queue:
                # The node is already waiting for this control event, forward it immediately
                event.send(self._frontend)
                # And also signal the backend that we treated this event
                self._queue[event.control].send(self._backend)
                del self._queue[event.control]
            else:
                # The node is not ready for this event yet, queue it
                self._queue[event.control] = event

        if self._frontend in events:
            event = VirtualControlEvent.recv(self._frontend)
            if event.control in self._queue:
                # The backend has already put an event for this control, forward it immediately
                self._queue[event.control].send(self._frontend)
                del self._queue[event.control]
                # And also signal the backend that we treated this event
                event.send(self._backend)
            else:
                # The backend hasn't sent us any event for this control yet, queue the request
                self._queue[event.control] = event

    def run(self):
        while True:
            self.loop()
