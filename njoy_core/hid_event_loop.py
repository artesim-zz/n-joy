import gevent
import threading
import sdl2
import sdl2.ext
import zmq.green as zmq

from njoy_core.io.sdl_joystick import SDLJoystick
from njoy_core.messages import HidAxisEvent, HidBallEvent, HidButtonEvent, HidHatEvent


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


class HidEventLoop(threading.Thread):
    def __init__(self, context, events_endpoint, requests_endpoint):
        super(HidEventLoop, self).__init__()
        self._joysticks = dict()
        self._joysticks_by_idx = dict()
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._requests_endpoint = requests_endpoint

    def _requests_handler(self):
        socket = self._ctx.socket(zmq.REP)
        socket.bind(self._requests_endpoint)

        while True:
            request, parameters = socket.recv_multipart()

            if request == b'open':
                device_name = parameters.decode('utf-8')

                device_index = SDLJoystick.find_device_index(device_name)
                if device_index is None:
                    raise HidEventLoopException("Unknown device : {}".format(device_name))

                if device_index in self._joysticks_by_idx:
                    joystick = self._joysticks_by_idx[device_index]
                else:
                    joystick = SDLJoystick.open(device_index)
                    self._joysticks[joystick.instance_id] = joystick
                    self._joysticks_by_idx[device_index] = joystick

                socket.send_pyobj(joystick.full_state)

            else:
                socket.send_pyobj(False)

    def _event_loop(self):
        socket = self._ctx.socket(zmq.PUB)
        socket.bind(self._events_endpoint)

        while gevent.sleep(0) is None:
            events = sdl2.ext.get_events()
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    raise HidEventLoopQuit()

                elif event.type == sdl2.SDL_JOYAXISMOTION:
                    HidAxisEvent(joystick_instance_id=event.jaxis.which,
                                 ctrl_id=event.jaxis.axis,
                                 value=event.jaxis.value).send(socket)

                elif event.type == sdl2.SDL_JOYBALLMOTION:
                    HidBallEvent(joystick_instance_id=event.jball.which,
                                 ctrl_id=event.jball.ball,
                                 dx=event.jball.xrel,
                                 dy=event.jball.yrel).send(socket)

                elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                    HidButtonEvent(joystick_instance_id=event.jbutton.which,
                                   ctrl_id=event.jbutton.button,
                                   state=event.jbutton.state).send(socket)

                elif event.type == sdl2.SDL_JOYHATMOTION:
                    HidHatEvent(joystick_instance_id=event.jhat.which,
                                ctrl_id=event.jhat.hat,
                                value=event.jhat.value).send(socket)

    def run(self, *args, **kwargs):
        SDLJoystick.sdl_init()

        requests_server = gevent.spawn(self._requests_handler)
        event_loop = gevent.spawn(self._event_loop)
        gevent.joinall([requests_server, event_loop])

        for joystick in self._joysticks.values():
            joystick.close()

        SDLJoystick.sdl_quit()
