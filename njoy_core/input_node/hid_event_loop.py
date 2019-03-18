import sdl2
import sdl2.ext
import time
import zmq

from .sdl_joystick import SDLJoystick
from njoy_core.common.messages import HidRequest, HidReply, NamedControlEvent


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


__LOOP_SLEEP_TIME__ = 0.0001  # 100 µs


class HidEventLoop:
    def __init__(self, context, events_endpoint, requests_endpoint):
        self._devices = dict()
        self._ctx, self._events_socket = self._zmq_setup(context, events_endpoint)
        self._requests_endpoint = requests_endpoint

    @staticmethod
    def _zmq_setup(context, events_endpoint):
        socket = context.socket(zmq.PUSH)
        socket.connect(events_endpoint)
        return context, socket

    @staticmethod
    def _register_devices(context, requests_endpoint):
        socket = context.socket(zmq.REQ)
        socket.connect(requests_endpoint)

        # First send our list of joysticks to njoy_core
        HidRequest('register', *SDLJoystick.device_names()).send(socket)

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = HidReply.recv(socket)

        # ... so open those
        # TODO: registered should send a device_id for each registered device, so we can use that in the events
        if reply.command != 'registered':
            raise HidEventLoopException("Unexpected reply from nJoy core : {}".format(reply))

        if not reply.args:
            raise HidEventLoopException("The nJoy core isn't interested in any of our devices, exiting.")

        devices = dict()
        for device_name in reply.args:
            device_index = SDLJoystick.find_device_index(device_name)
            if device_index is None:
                raise HidEventLoopException("Unknown device : {}".format(device_name))

            device = SDLJoystick.open(device_index)
            devices[device.instance_id] = device
        return devices

    def run(self):
        def _identity(device_name, ctrl_type, ctrl_id):
            return '/{}/{}/{}'.format(device_name, ctrl_type, ctrl_id)

        def _axis(value):
            # Convert from [-32768 .. 32768] to [-1.0 .. 1.0]
            return 2 * ((value + 0x8000) / 0xFFFF) - 1

        def _button(value):
            return value != 0

        SDLJoystick.sdl_init()
        self._devices = self._register_devices(self._ctx, self._requests_endpoint)

        print("HidEventLoop: started")
        try:
            while True:
                for event in sdl2.ext.get_events():
                    if event.type == sdl2.SDL_QUIT:
                        raise HidEventLoopQuit()

                    elif event.type == sdl2.SDL_JOYAXISMOTION:
                        NamedControlEvent(identity=_identity(self._devices[event.jaxis.which].name,
                                                             'axis',
                                                             event.jaxis.axis),
                                          value=_axis(event.jaxis.value)).send(self._events_socket)

                    elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                        NamedControlEvent(identity=_identity(self._devices[event.jbutton.which].name,
                                                             'button',
                                                             event.jbutton.button),
                                          value=_button(event.jbutton.state)).send(self._events_socket)

                    elif event.type == sdl2.SDL_JOYHATMOTION:
                        NamedControlEvent(identity=_identity(self._devices[event.jhat.which].name,
                                                             'hat',
                                                             event.jhat.hat),
                                          value=event.jhat.value).send(self._events_socket)
                time.sleep(__LOOP_SLEEP_TIME__)

        except HidEventLoopQuit:
            pass  # normal exit

        finally:
            for device in self._devices.values():
                device.close()

            SDLJoystick.sdl_quit()
