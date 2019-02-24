import threading
import sdl2
import sdl2.ext
import zmq


class HidInputDeviceException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidInputDeviceQuit(HidInputDeviceException):
    pass


class Joystick:
    """OOP-ified wrapper around the SDL2 library"""

    @staticmethod
    def get_event_state():
        return Joystick.set_event_state(sdl2.SDL_QUERY)

    @staticmethod
    def set_event_state(state):
        event_state = sdl2.SDL_JoystickEventState(state)
        if event_state < 0:
            raise HidInputDeviceException(sdl2.SDL_GetError())
        return event_state

    @staticmethod
    def nb_joysticks():
        nb_joysticks = sdl2.SDL_NumJoysticks()
        if nb_joysticks < 0:
            raise HidInputDeviceException(sdl2.SDL_GetError())
        return nb_joysticks

    @staticmethod
    def update():
        sdl2.SDL_JoystickUpdate()

    @staticmethod
    def device_guid(device_index):
        guid = sdl2.SDL_JoystickGetDeviceGUID(device_index)
        if guid == 0:
            raise HidInputDeviceException(sdl2.SDL_GetError())
        return guid

    @staticmethod
    def device_name(device_index):
        name = sdl2.SDL_JoystickNameForIndex(device_index)
        if not name:
            raise HidInputDeviceException(sdl2.SDL_GetError())
        return name.decode('utf-8')

    @staticmethod
    def to_guid_str(guid):
        return ['{:02x}'.format(guid.data[i]) for i in range(guid.data)]

    @classmethod
    def open(cls, device_index, zmq_context, zmq_end_point):
        sdl_joystick = sdl2.SDL_JoystickOpen(device_index)
        if not sdl_joystick:
            raise HidInputDeviceException(sdl2.SDL_GetError())
        return cls(sdl_joystick, device_index, zmq_context, zmq_end_point)

    def close(self):
        sdl2.SDL_JoystickClose(self._sdl_joystick)
        self._sdl_joystick = None

    def is_attached(self):
        return sdl2.SDL_JoystickGetAttached(self._sdl_joystick) if self._sdl_joystick else False

    def __init__(self, sdl_joystick, device_index, zmq_context, zmq_end_point):
        self._zmq_context = zmq_context
        self._zmq_end_point = zmq_end_point

        self._device_index = device_index
        self._sdl_joystick = sdl_joystick

        self._current_power_level = None
        self._guid = None
        self._instance_id = None
        self._name = None

        self._nb_axes = None
        self._nb_balls = None
        self._nb_buttons = None
        self._nb_hats = None

        self._axes = self._compute_axes()
        self._balls = self._compute_balls()
        self._buttons = self._compute_buttons()
        self._hats = self._compute_hats()

    def __repr__(self):
        return "<InputDevice #{} {}>".format(self.instance_id, self.name)

    def _compute_axes(self):
        axes = dict()
        for i in range(self.nb_axes):
            axes[i] = sdl2.SDL_JoystickGetAxis(self._sdl_joystick, i)  # -32768 to 32767
        return axes

    def _compute_balls(self):
        balls = dict()
        for i in range(self.nb_balls):
            dx = dy = 0
            code = sdl2.SDL_JoystickGetBall(self._sdl_joystick, i, dx, dy)
            if code < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
            balls[i] = (dx, dy)
        return balls

    def _compute_buttons(self):
        buttons = dict()
        for i in range(self.nb_buttons):
            buttons[i] = (sdl2.SDL_JoystickGetButton(self._sdl_joystick, i) == sdl2.SDL_PRESSED)
        return buttons

    def _compute_hats(self):
        hats = dict()
        for i in range(self.nb_hats):
            hats[i] = sdl2.SDL_JoystickGetHat(self._sdl_joystick, i)
        return hats

    @property
    def current_power_level(self):
        if self._current_power_level is None:
            self._current_power_level = sdl2.SDL_JoystickCurrentPowerLevel(self._sdl_joystick)
            if self._current_power_level == sdl2.SDL_JOYSTICK_POWER_UNKNOWN:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._current_power_level

    @property
    def guid(self):
        if self._guid is None:
            self._guid = sdl2.SDL_JoystickGetGUID()
            if self._guid == 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._guid

    @property
    def guid_str(self):
        return self.to_guid_str(self.guid)

    @property
    def instance_id(self):
        if self._instance_id is None:
            self._instance_id = sdl2.SDL_JoystickInstanceID(self._sdl_joystick)
            if self._instance_id < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._instance_id

    @property
    def device_index(self):
        return self._device_index

    @property
    def name(self):
        if self._name is None:
            name = sdl2.SDL_JoystickName(self._sdl_joystick)
            if not name:
                raise HidInputDeviceException(sdl2.SDL_GetError())
            self._name = name.decode('utf-8')
        return self._name

    @property
    def nb_axes(self):
        if self._nb_axes is None:
            self._nb_axes = sdl2.SDL_JoystickNumAxes(self._sdl_joystick)
            if self._nb_axes < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._nb_axes

    @property
    def nb_balls(self):
        if self._nb_balls is None:
            self._nb_balls = sdl2.SDL_JoystickNumBalls(self._sdl_joystick)
            if self._nb_balls < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._nb_balls

    @property
    def nb_buttons(self):
        if self._nb_buttons is None:
            self._nb_buttons = sdl2.SDL_JoystickNumButtons(self._sdl_joystick)
            if self._nb_buttons < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._nb_buttons

    @property
    def nb_hats(self):
        if self._nb_hats is None:
            self._nb_hats = sdl2.SDL_JoystickNumHats(self._sdl_joystick)
            if self._nb_hats < 0:
                raise HidInputDeviceException(sdl2.SDL_GetError())
        return self._nb_hats


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

        device_index_of = {Joystick.device_name(device_index): device_index
                           for device_index in range(Joystick.nb_joysticks())}

        self._joysticks = {joystick.instance_id: joystick
                           for joystick in [Joystick.open(device_index_of[device_name], self._ctx, self._out_end_point)
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
