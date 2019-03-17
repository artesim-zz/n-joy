import sdl2
import sdl2.ext
import zmq

from .sdl_joystick import SDLJoystick
from njoy_core.common.messages import *


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


class HidEventLoop:
    def __init__(self, context, events_endpoint, requests_endpoint):
        self._devices = dict()
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._requests_endpoint = requests_endpoint

    def _register_devices(self):
        socket = self._ctx.socket(zmq.REQ)
        socket.connect(self._requests_endpoint)

        # First send our list of joysticks to njoy_core
        Request('register', *SDLJoystick.device_names()).send(socket)

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = Message.recv(socket)

        # ... so open those
        if reply.command != 'registered':
            raise HidEventLoopException("Unexpected reply from nJoy core : {}".format(reply))

        if not reply.args:
            raise HidEventLoopException("The nJoy core isn't interested in any of our devices, exiting.")

        for device_name in reply.args:
            device_index = SDLJoystick.find_device_index(device_name)
            if device_index is None:
                raise HidEventLoopException("Unknown device : {}".format(device_name))

            device = SDLJoystick.open(device_index)
            self._devices[device.instance_id] = device

    def run(self):
        socket = self._ctx.socket(zmq.PUSH)
        socket.connect(self._events_endpoint)

        SDLJoystick.sdl_init()

        self._register_devices()

        print("HidEventLoop: started")
        try:
            while True:
                for event in sdl2.ext.get_events():
                    if event.type == sdl2.SDL_QUIT:
                        raise HidEventLoopQuit()

                    elif event.type == sdl2.SDL_JOYAXISMOTION:
                        AxisEvent(device_name=self._devices[event.jaxis.which].name,
                                  ctrl_id=event.jaxis.axis,
                                  value=event.jaxis.value).send(socket)

                    elif event.type == sdl2.SDL_JOYBALLMOTION:
                        BallEvent(device_name=self._devices[event.jball.which].name,
                                  ctrl_id=event.jball.ball,
                                  dx=event.jball.xrel,
                                  dy=event.jball.yrel).send(socket)

                    elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                        ButtonEvent(device_name=self._devices[event.jbutton.which].name,
                                    ctrl_id=event.jbutton.button,
                                    state=event.jbutton.state).send(socket)

                    elif event.type == sdl2.SDL_JOYHATMOTION:
                        HatEvent(device_name=self._devices[event.jhat.which].name,
                                 ctrl_id=event.jhat.hat,
                                 value=event.jhat.value).send(socket)

        except HidEventLoopQuit:
            pass  # normal exit

        finally:
            for device in self._devices.values():
                device.close()

            SDLJoystick.sdl_quit()
