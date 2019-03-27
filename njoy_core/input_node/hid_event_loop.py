import sdl2
import sdl2.ext
import time

from .sdl_joystick import SDLJoystick
from njoy_core.core.model.device import PhysicalDevice
from njoy_core.core.model.control import Axis, Button, Hat
from njoy_core.core.messages import InputNodeRegisterRequest, InputNodeRegisterReply, PhysicalControlEvent


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

        # First send our list of joysticks to njoy_core, excluding vJoy devices (those are our output devices)
        InputNodeRegisterRequest(devices=SDLJoystick.device_list(exclude_list=['vJoy Device'])).send(socket)
        print("Input Node: sent request")

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(socket)
        print("Input Node: received reply")

        # ... so open those
        if not reply.device_ids_map:
            raise HidEventLoopException("The nJoy core isn't interested in any of our devices, exiting.")

        devices = dict()
        for (sdl_device_guid, njoy_device_id) in reply.device_ids_map.items():
            device = SDLJoystick.open(sdl_device_guid)
            devices[device.instance_id] = {'njoy_device': PhysicalDevice(node=reply.node_id, dev=njoy_device_id),
                                           'sdl_device': device}
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
                PhysicalControlEvent(control=Axis(dev=self._devices[event.jaxis.which]['njoy_device'],
                                                  ctrl=event.jaxis.axis),
                                     value=self._axis(event.jaxis.value)).send(socket)

            elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                PhysicalControlEvent(control=Button(dev=self._devices[event.jbutton.which]['njoy_device'],
                                                    ctrl=event.jbutton.button),
                                     value=self._button(event.jbutton.state)).send(socket)

            elif event.type == sdl2.SDL_JOYHATMOTION:
                PhysicalControlEvent(control=Hat(dev=self._devices[event.jhat.which]['njoy_device'],
                                                 ctrl=event.jhat.hat),
                                     value=event.jhat.value).send(socket)

        time.sleep(self.__LOOP_SLEEP_TIME__)
