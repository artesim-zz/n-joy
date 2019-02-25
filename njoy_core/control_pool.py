import gevent.pool
import threading
import zmq.green as zmq

from njoy_core import controls
from njoy_core.messages import Message, HidDeviceFullStateMsg


class ControlPoolException(Exception):
    pass


class ControlPool(threading.Thread):
    def __init__(self, hid_event_loop, events_endpoint):
        super(ControlPool, self).__init__()
        self._hid_event_loop = hid_event_loop
        self._ctx = hid_event_loop.ctx
        self._events_endpoint = events_endpoint
        self._group = gevent.pool.Group()

    @property
    def ctx(self):
        return self._ctx

    @property
    def events_endpoint(self):
        return self._events_endpoint

    def _setup_controls(self):
        socket = self._ctx.socket(zmq.REQ)
        socket.connect(self._hid_event_loop.requests_endpoint)

        ctrls = set()
        for joystick in ["Joystick - HOTAS Warthog",
                         "Throttle - HOTAS Warthog",
                         "MFG Crosswind V2",
                         "Saitek Pro Flight Throttle Quadrant"]:
            socket.send_multipart([b'open', joystick.encode('utf-8')])
            full_state_msg = Message.recv(socket)
            if isinstance(full_state_msg, HidDeviceFullStateMsg):
                for ctrl in full_state_msg.control_events:
                    if ctrl in ctrls:
                        print("Skipping duplicate control : {}".format(ctrl))
                    else:
                        ctrls.add(ctrl)

        for ctrl in ctrls:
            self._group.start(controls.Control(self._ctx, self._hid_event_loop.events_endpoint, ctrl))

    def run(self):
        self._setup_controls()
        self._group.join()

# eof