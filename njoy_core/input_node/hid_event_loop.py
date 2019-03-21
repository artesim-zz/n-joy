import sdl2
import sdl2.ext
import time

from .sdl_joystick import SDLJoystick
from njoy_core.common.messages import InputNodeRegisterRequest, InputNodeRegisterReply, ControlEvent


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


class HidEventLoop:
    __LOOP_SLEEP_TIME__ = 0.0001  # 100 µs

    def __init__(self):
        self._devices = None

    def handshake(self, socket):
        SDLJoystick.sdl_init()

        # First send our list of joysticks to njoy_core
        InputNodeRegisterRequest(devices=SDLJoystick.device_names()).send(socket)
        print("Input Node: sent request")

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(socket)
        print("Input Node: received reply")

        # ... so open those
        if not reply.device_ids_map:
            raise HidEventLoopException("The nJoy core isn't interested in any of our devices, exiting.")

        devices = dict()
        for (njoy_device_id, device_name) in reply.device_ids_map.items():
            sdl_device_id = SDLJoystick.find_device_index(device_name)
            if sdl_device_id is None:
                raise HidEventLoopException("Unknown device : {}".format(device_name))

            device = SDLJoystick.open(sdl_device_id)
            devices[device.instance_id] = {'node_id': reply.node_id,
                                           'device_id': njoy_device_id,
                                           'device': device}
        self._devices = devices

    @staticmethod
    def _axis(value):
        # Convert from [-32768 .. 32768] to [-1.0 .. 1.0]
        return 2 * ((value + 0x8000) / 0xFFFF) - 1

    @staticmethod
    def _button(value):
        return value != 0

    def loop(self, socket):
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                raise HidEventLoopQuit()

            elif event.type == sdl2.SDL_JOYAXISMOTION:
                device = self._devices[event.jaxis.which]
                ControlEvent(node=device['node_id'],
                             device=device['device_id'],
                             control=event.jaxis.axis,
                             value=self._axis(event.jaxis.value)).send(socket)

            elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                device = self._devices[event.jbutton.which]
                ControlEvent(node=device['node_id'],
                             device=device['device_id'],
                             control=event.jbutton.button,
                             value=self._button(event.jbutton.state)).send(socket)

            elif event.type == sdl2.SDL_JOYHATMOTION:
                device = self._devices[event.jhat.which]
                ControlEvent(node=device['node_id'],
                             device=device['device_id'],
                             control=event.jhat.hat,
                             value=event.jhat.value).send(socket)

        time.sleep(self.__LOOP_SLEEP_TIME__)
