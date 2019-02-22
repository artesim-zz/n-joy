import enum
import math
import pyvjoy


class OutputDevice(pyvjoy.VJoyDevice):
    """Wrapper class around pyvjoy.VJoyDevice.
    It serves three purposes :
    - fixing some quirks of the pyvjoy interface I don't like, such 1-based indexes.
    - augment the pyvjoy interface with some useful utility functions.
    - most importantly, provide a layer of abstraction, should I want to switch to something else later."""
    class Axis(enum.Enum):
        X = 0
        Y = 1
        Z = 2
        RX = 3
        RY = 4
        RZ = 5
        SL0 = 6
        SL1 = 7
        WHEEL = 8
        POV = 9

    def __init__(self, device_id):
        """device_id is 0-based, internally converted to vjoy 1-based index."""
        super(OutputDevice, self).__init__(1 + device_id)
        self.reset()

    @staticmethod
    def _to_vjoy_cont_pov(value):
        mapping = {(0, 0): -1,
                   (0, 1): 0,
                   (1, 1): 4500,
                   (1, 0): 9000,
                   (1, -1): 13500,
                   (0, -1): 18000,
                   (-1, -1): 22500,
                   (-1, 0): 27000,
                   (-1, 1): 31500}
        return mapping[value]

    @staticmethod
    def _to_vjoy_axis_id(value):
        mapping = [pyvjoy.HID_USAGE_X, pyvjoy.HID_USAGE_Y, pyvjoy.HID_USAGE_Z,
                   pyvjoy.HID_USAGE_RX, pyvjoy.HID_USAGE_RY, pyvjoy.HID_USAGE_RZ,
                   pyvjoy.HID_USAGE_SL0, pyvjoy.HID_USAGE_SL1,
                   pyvjoy.HID_USAGE_WHL,
                   pyvjoy.HID_USAGE_POV]
        return mapping[value]

    def set_button(self, button_id, state, delay=None):
        """Set a given button to On (1 or True) or Off (0 or False)
        button_id is 0-based, internally converted to vjoy 1-based button ID"""
        def _set_button():
            super(OutputDevice, self).set_button(1 + button_id, state)

        if delay is None:
            _set_button()

    def pulse_button(self, button_id, state, duration=20, delay=None):
        """Set a given button to 'state', but only for 'duration' milliseconds, and with optional delay
        button_id is 0-based, internally converted to vjoy 1-based button ID"""
        def _start_pulse():
            def _release():
                self.set_button(button_id, not state)
            self.set_button(button_id, state)

        if delay is None:
            _start_pulse()

    def set_axis(self, axis_id, axis_value):
        """Set a given axis to the given value.
        axis_id is 0-based [0..9], internally converted to vjoy axis ID
        axis_value is a float in range [-1.0 .. 1.0], internally converted to vjoy int range [0X0001..0x8000]"""
        return super(OutputDevice, self).set_axis(self._to_vjoy_axis_id(axis_id),
                                                  math.floor(1 + (0x7FFF * (1 + axis_value)) / 2))

    def set_cont_pov(self, pov_id, pov_value):
        """Set a given POV (numbered from 0) to a continuous direction :
        pov_id is 0-based, internally converted to vjoy 1-based pov ID
        pov_value is :an int in range [0 .. 35900] (tenth of degrees) or -1 for none (not pressed)"""
        return super(OutputDevice, self).set_cont_pov(1 + pov_id, self._to_vjoy_cont_pov(pov_value))
