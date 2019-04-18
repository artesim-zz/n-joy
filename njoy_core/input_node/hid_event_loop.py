import time

import sdl2
import sdl2.ext

from njoy_core.core.model import InputNodeRegisterRequest, InputNodeRegisterReply, PhysicalControlEvent

from .sdl_joystick import SDLJoystick


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""


class HidEventLoopQuit(HidEventLoopException):
    pass


class HidEventLoop:
    __LOOP_SLEEP_TIME__ = 0.0001  # 100 µs

    def __init__(self):
        self._devices = None

    def handshake(self, socket):
        SDLJoystick.sdl_init()

        # First send our list of joysticks to njoy_core, excluding vJoy devices (those are our output devices)
        InputNodeRegisterRequest(available_devices=SDLJoystick.device_list(exclude_list=['vJoy Device'])).send(socket)
        print("Input Node: sent request")

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(socket)
        print("Input Node: received reply")

        # ... so open those
        devices = dict()
        for njoy_device in reply.node:
            sdl_device = SDLJoystick.open(njoy_device.guid)
            devices[sdl_device.instance_id] = {'njoy_device': njoy_device,
                                               'sdl_device': sdl_device}
        self._devices = devices

    @staticmethod
    def _axis_value(value):
        # Convert from [-32768 .. 32768] to [-1.0 .. 1.0]
        return 2 * ((value + 0x8000) / 0xFFFF) - 1

    @staticmethod
    def _button_value(value):
        return value != 0

    def emit_full_state(self, socket):
        for device in self._devices.values():
            sdl_device = device['sdl_device']
            for axis in device['njoy_device'].axes.values():
                PhysicalControlEvent(control=axis,
                                     value=sdl_device.get_axis(axis.id)).send(socket)
            for button in device['njoy_device'].buttons.values():
                PhysicalControlEvent(control=button,
                                     value=sdl_device.get_button(button.id)).send(socket)
            for hat in device['njoy_device'].hats.values():
                PhysicalControlEvent(control=hat,
                                     value=sdl_device.get_hat(hat.id)).send(socket)

    def loop(self, socket):
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                raise HidEventLoopQuit()

            if event.type == sdl2.SDL_JOYAXISMOTION:
                device = self._devices[event.jaxis.which]['njoy_device']
                if event.jaxis.axis in device.axes:
                    PhysicalControlEvent(control=device.axes[event.jaxis.axis],
                                         value=self._axis_value(event.jaxis.value)).send(socket)

            elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                device = self._devices[event.jbutton.which]['njoy_device']
                if event.jbutton.button in device.buttons:
                    PhysicalControlEvent(control=device.buttons[event.jbutton.button],
                                         value=self._button_value(event.jbutton.state)).send(socket)

            elif event.type == sdl2.SDL_JOYHATMOTION:
                device = self._devices[event.jhat.which]['njoy_device']
                if event.jhat.hat in device.hats:
                    PhysicalControlEvent(control=device.hats[event.jhat.hat],
                                         value=event.jhat.value).send(socket)

        time.sleep(self.__LOOP_SLEEP_TIME__)
