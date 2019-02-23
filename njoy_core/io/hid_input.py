import threading
import sdl2
import sdl2.ext
import zmq


class InputDeviceException(Exception):
    pass


class InputDevice:
    def __init__(self, sdl_instance, output_device):
        self.sdl_instance = sdl_instance
        self.output_device = output_device
        self.name = sdl2.SDL_JoystickName(sdl_instance)

    def __repr__(self):
        return "<InputDevice {}>".format(self.name)

    def set_button(self, button_id, state):
        self.output_device.set_button(button_id, state)


class InputDevicesMonitor(threading.Thread):
    def __init__(self, zmq_context, device_names, output_devices, *args, **kwargs):
        super(InputDevicesMonitor, self).__init__(*args, **kwargs)
        self.zmq_context = zmq_context
        self.device_names = set(device_names)
        self.output_devices = {k: v for (k, v) in zip(device_names, output_devices)}
        self.devices = dict()

    def _sdl_init(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_JOYSTICK)

        nb_joysticks = sdl2.SDL_NumJoysticks()
        if nb_joysticks < 0:
            raise InputDeviceException(sdl2.SDL_GetError())

        for i in range(nb_joysticks):
            joystick = sdl2.SDL_JoystickOpen(i)
            if not joystick:
                raise InputDeviceException(sdl2.SDL_GetError())

            joystick_name = sdl2.SDL_JoystickName(joystick).decode('utf-8')
            if joystick_name in self.device_names:
                instance_id = sdl2.SDL_JoystickInstanceID(joystick)
                self.devices[instance_id] = InputDevice(joystick, self.output_devices[joystick_name])

    def _sdl_close(self):
        for j in self.devices.values():
            sdl2.SDL_JoystickClose(j)
        sdl2.SDL_Quit()

    def run(self, *args, **kwargs):
        try:
            self._sdl_init()

            sender = self.zmq_context.socket(zmq.PUSH)
            sender.connect("inproc://input_device_monitor")

            running = True
            while running:
                for event in sdl2.ext.get_events():
                    if event.type == sdl2.SDL_QUIT:
                        running = False
                        break
                    elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                        jbutton_event = event.jbutton
                        if jbutton_event.which in self.devices:
                            joystick = self.devices[jbutton_event.which]
                            joystick.set_button(jbutton_event.button, 1)
                            sender.send_string("{}: Joy button {} down".format(joystick, jbutton_event.button))
                    elif event.type == sdl2.SDL_JOYBUTTONUP:
                        jbutton_event = event.jbutton
                        if jbutton_event.which in self.devices:
                            joystick = self.devices[jbutton_event.which]
                            joystick.set_button(jbutton_event.button, 0)
                            sender.send_string("{}: Joy button {} up".format(joystick, jbutton_event.button))
                sdl2.SDL_Delay(1)

        finally:
            self._sdl_close()
