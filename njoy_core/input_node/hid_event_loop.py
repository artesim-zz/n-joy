import sdl2
import sdl2.ext
import time
import zmq

from .sdl_joystick import SDLJoystick
from njoy_core.common.messages import InputNodeRegisterRequest, InputNodeRegisterReply, ControlEvent


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


__LOOP_SLEEP_TIME__ = 0.0001  # 100 µs


class HidEventLoop:
    def __init__(self, context, events_endpoint, requests_endpoint):
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
        InputNodeRegisterRequest(devices=SDLJoystick.device_names()).send(socket)

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(socket)

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
        return devices

    def run(self):
        def _axis(value):
            # Convert from [-32768 .. 32768] to [-1.0 .. 1.0]
            return 2 * ((value + 0x8000) / 0xFFFF) - 1

        def _button(value):
            return value != 0

        SDLJoystick.sdl_init()
        devices = self._register_devices(self._ctx, self._requests_endpoint)

        print("HidEventLoop: started")
        try:
            while True:
                for event in sdl2.ext.get_events():
                    if event.type == sdl2.SDL_QUIT:
                        raise HidEventLoopQuit()

                    elif event.type == sdl2.SDL_JOYAXISMOTION:
                        device = devices[event.jaxis.which]
                        ControlEvent(node=device['node_id'],
                                     device=device['device_id'],
                                     control=event.jaxis.axis,
                                     value=_axis(event.jaxis.value)).send(self._events_socket)

                    elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                        device = devices[event.jbutton.which]
                        ControlEvent(node=device['node_id'],
                                     device=device['device_id'],
                                     control=event.jbutton.button,
                                     value=_button(event.jbutton.state)).send(self._events_socket)

                    elif event.type == sdl2.SDL_JOYHATMOTION:
                        device = devices[event.jhat.which]
                        ControlEvent(node=device['node_id'],
                                     device=device['device_id'],
                                     control=event.jhat.hat,
                                     value=event.jhat.value).send(self._events_socket)
                time.sleep(__LOOP_SLEEP_TIME__)

        except HidEventLoopQuit:
            pass  # normal exit

        finally:
            for device in devices.values():
                device['device'].close()

            SDLJoystick.sdl_quit()
