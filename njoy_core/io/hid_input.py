import threading
import sdl2
import sdl2.ext
import zmq

from njoy_core.io.sdl_joystick import SDLJoystick


class HidInputDeviceException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidInputDeviceQuit(HidInputDeviceException):
    pass


class HidEventLoop(threading.Thread):
    def __init__(self, zmq_context, zmq_end_point, monitored_devices):
        super(HidEventLoop, self).__init__()
        self._joysticks = monitored_devices
        self._ctx, self._out_end_point, self._out_socket = self._zmq_init(zmq_context, zmq_end_point)

    @staticmethod
    def _zmq_init(context, end_point):
        socket = context.socket(zmq.PUB)
        socket.bind(end_point)
        return context, end_point, socket

    def _sdl_init(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_JOYSTICK)

        device_index_of = {SDLJoystick.device_name(device_index): device_index
                           for device_index in range(SDLJoystick.nb_joysticks())}

        self._joysticks = {joystick.instance_id: joystick
                           for joystick in [SDLJoystick.open(device_index_of[device_name])
                                            for device_name in self._joysticks
                                            if device_name in device_index_of.keys()]}

    def _sdl_close(self):
        for joystick in self._joysticks.values():
            joystick.close()
        self._joysticks = None
        sdl2.SDL_Quit()

    def run(self, *args, **kwargs):
        try:
            self._sdl_init()

            while True:
                for event in sdl2.ext.get_events():
                    if event.type == sdl2.SDL_QUIT:
                        raise HidInputDeviceQuit()

                    elif event.type == sdl2.SDL_JOYAXISMOTION:
                        if event.jaxis.which in self._joysticks:
                            self._out_socket.send_string("/{}/axes/{} = {}".format(event.jaxis.which,
                                                                                   event.jaxis.axis,
                                                                                   event.jaxis.value))

                    elif event.type == sdl2.SDL_JOYBALLMOTION:
                        if event.jball.which in self._joysticks:
                            self._out_socket.send_string("/{}/balls/{} = ({}, {})".format(event.jball.which,
                                                                                          event.jball.ball,
                                                                                          event.jball.xrel,
                                                                                          event.jball.yrel))

                    elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                        if event.jbutton.which in self._joysticks:
                            self._out_socket.send_string("/{}/buttons/{} = {}".format(event.jbutton.which,
                                                                                      event.jbutton.button,
                                                                                      event.jbutton.state))

                    elif event.type == sdl2.SDL_JOYDEVICEADDED:
                        if event.jdevice.which in self._joysticks:
                            name = self._joysticks[event.jdevice.which].name
                            self._out_socket.send_string("{}: Connected".format(name))

                    elif event.type == sdl2.SDL_JOYDEVICEREMOVED:
                        if event.jdevice.which in self._joysticks:
                            name = self._joysticks[event.jdevice.which].name
                            self._out_socket.send_string("{}: Disconnected".format(name))

                    elif event.type == sdl2.SDL_JOYHATMOTION:
                        if event.jhat.which in self._joysticks:
                            self._out_socket.send_string("/{}/hats/{} = {}".format(event.jhat.which,
                                                                                   event.jhat.hat,
                                                                                   event.jhat.value))

                sdl2.SDL_Delay(1)

        finally:
            self._sdl_close()
