import sdl2


class SdlJoystickException(Exception):
    pass


class SDLJoystick:
    """OOP-ified wrapper around the SDL2 joystick interface"""

    @staticmethod
    def sdl_init():
        sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_JOYSTICK)

    @staticmethod
    def sdl_quit():
        sdl2.SDL_Quit()

    @staticmethod
    def get_event_state():
        return SDLJoystick.set_event_state(sdl2.SDL_QUERY)

    @staticmethod
    def set_event_state(state):
        event_state = sdl2.SDL_JoystickEventState(state)
        if event_state < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return event_state

    @staticmethod
    def nb_joysticks():
        nb_joysticks = sdl2.SDL_NumJoysticks()
        if nb_joysticks < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return nb_joysticks

    @staticmethod
    def update():
        sdl2.SDL_JoystickUpdate()

    @staticmethod
    def device_guid(device_index):
        guid = sdl2.SDL_JoystickGetDeviceGUID(device_index)
        if guid == 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return guid

    @staticmethod
    def device_name(device_index):
        name = sdl2.SDL_JoystickNameForIndex(device_index)
        if not name:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return name.decode('utf-8')

    @staticmethod
    def find_device_index(device_name):
        for i in range(SDLJoystick.nb_joysticks()):
            if device_name == SDLJoystick.device_name(i):
                return i

    @staticmethod
    def to_guid_str(guid):
        return ['{:02x}'.format(guid.data[i]) for i in range(guid.data)]

    @classmethod
    def open(cls, device_name_or_index):
        sdl_joystick = sdl2.SDL_JoystickOpen(device_name_or_index
                                             if isinstance(device_name_or_index, int)
                                             else SDLJoystick.find_device_index(device_name_or_index))
        if not sdl_joystick:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return cls(sdl_joystick, device_name_or_index)

    def close(self):
        sdl2.SDL_JoystickClose(self._sdl_joystick)
        self._sdl_joystick = None

    def is_attached(self):
        return sdl2.SDL_JoystickGetAttached(self._sdl_joystick) if self._sdl_joystick else False

    def __init__(self, sdl_joystick, device_index):
        self._device_index = device_index
        self._sdl_joystick = sdl_joystick

    def __repr__(self):
        return "<InputDevice #{} {}>".format(self.instance_id, self.name)

    def get_axis(self, i):
        return sdl2.SDL_JoystickGetAxis(self._sdl_joystick, i)  # -32768 to 32767

    def get_ball(self, i):
        dx = dy = 0
        code = sdl2.SDL_JoystickGetBall(self._sdl_joystick, i, dx, dy)
        if code < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return dx, dy

    def get_button(self, i):
        return sdl2.SDL_JoystickGetButton(self._sdl_joystick, i) == sdl2.SDL_PRESSED

    def get_hat(self, i):
        return sdl2.SDL_JoystickGetHat(self._sdl_joystick, i)

    @property
    def full_state(self):
        self.update()
        return [('axis', i, self.get_axis(i)) for i in range(self.nb_axes)] + \
               [('ball', i, self.get_ball(i)) for i in range(self.nb_balls)] + \
               [('button', i, self.get_button(i)) for i in range(self.nb_buttons)] + \
               [('hat', i, self.get_hat(i)) for i in range(self.nb_hats)]

    @property
    def current_power_level(self):
        current_power_level = sdl2.SDL_JoystickCurrentPowerLevel(self._sdl_joystick)
        if current_power_level == sdl2.SDL_JOYSTICK_POWER_UNKNOWN:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return current_power_level

    @property
    def guid(self):
        guid = sdl2.SDL_JoystickGetGUID(self._sdl_joystick)
        if guid == 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return guid

    @property
    def guid_str(self):
        return self.to_guid_str(self.guid)

    @property
    def instance_id(self):
        instance_id = sdl2.SDL_JoystickInstanceID(self._sdl_joystick)
        if instance_id < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return instance_id

    @property
    def device_index(self):
        return self._device_index

    @property
    def name(self):
        name = sdl2.SDL_JoystickName(self._sdl_joystick)
        if not name:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return name.decode('utf-8')

    @property
    def nb_axes(self):
        nb_axes = sdl2.SDL_JoystickNumAxes(self._sdl_joystick)
        if nb_axes < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return nb_axes

    @property
    def nb_balls(self):
        nb_balls = sdl2.SDL_JoystickNumBalls(self._sdl_joystick)
        if nb_balls < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return nb_balls

    @property
    def nb_buttons(self):
        nb_buttons = sdl2.SDL_JoystickNumButtons(self._sdl_joystick)
        if nb_buttons < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return nb_buttons

    @property
    def nb_hats(self):
        nb_hats = sdl2.SDL_JoystickNumHats(self._sdl_joystick)
        if nb_hats < 0:
            raise SdlJoystickException(sdl2.SDL_GetError())
        return nb_hats
