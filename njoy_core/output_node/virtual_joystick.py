import threading
import zmq

from njoy_core.core.model import VirtualControlEvent
from njoy_core.core.model import HatState
from njoy_core.output_node import vjoy_device


class Feeder(threading.Thread):
    def __init__(self, virtual_joystick, control):
        super().__init__()

        self._ctx = virtual_joystick.ctx
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.set(zmq.IDENTITY, VirtualControlEvent.mk_identity(control))
        self._socket.connect(virtual_joystick.events_endpoint)

        self._output_device = virtual_joystick.output_device
        self._control = control

    def _handle_event(self, event):
        raise NotImplementedError

    def loop(self, socket):
        VirtualControlEvent().send(socket)
        event = VirtualControlEvent.recv(socket)
        self._handle_event(event)

    def run(self):
        while True:
            self.loop(self._socket)


class AxisFeeder(Feeder):
    def _handle_event(self, event):
        self._output_device.set_axis(axis_id=self._control.id,
                                     axis_value=event.value)


class ButtonFeeder(Feeder):
    def _handle_event(self, event):
        self._output_device.set_button(button_id=self._control.id,
                                       state=event.value)


class HatFeeder(Feeder):
    # -1 for none (not pressed), or in range [0 .. 35900] (tenth of degrees)
    __to_continuous_pov = {HatState.HAT_UP: 0,
                           HatState.HAT_UP_RIGHT: 4500,
                           HatState.HAT_RIGHT: 9000,
                           HatState.HAT_DOWN_RIGHT: 13500,
                           HatState.HAT_DOWN: 18000,
                           HatState.HAT_DOWN_LEFT: 22500,
                           HatState.HAT_LEFT: 27000,
                           HatState.HAT_UP_LEFT: 31500,
                           HatState.HAT_CENTER: -1}

    def _handle_event(self, event):
        self._output_device.set_cont_pov(pov_id=self._control.id,
                                         pov_value=self.__to_continuous_pov[event.value])


class VirtualJoystick(threading.Thread):
    # TODO: find a way to get the current vjoy configuration for that device
    __MAX_NB_AXES__ = 8
    __MAX_NB_BUTTONS__ = 128
    __MAX_NB_HATS__ = 4

    @classmethod
    def device_capabilities(cls, device_id=None):
        if device_id is None:
            return [cls.device_capabilities(i) for i in range(vjoy_device.VJoyDevice.nb_devices())]

        return {'device_id': device_id,
                'max_nb_axes': cls.__MAX_NB_AXES__,
                'max_nb_buttons': cls.__MAX_NB_BUTTONS__,
                'max_nb_hats': cls.__MAX_NB_HATS__}

    def __init__(self, device, context, events_endpoint):
        super().__init__(name="/virtual_joysticks/{}".format(device.id))
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._device = device
        self._output_device = vjoy_device.VJoyDevice(device_id=device.id)
        self._feeders = self._make_feeders()

    @property
    def ctx(self):
        return self._ctx

    @property
    def events_endpoint(self):
        return self._events_endpoint

    @property
    def output_device(self):
        return self._output_device

    def _make_feeders(self):
        feeders = [AxisFeeder(virtual_joystick=self, control=axis) for axis in self._device.axes.values()]
        feeders += [ButtonFeeder(virtual_joystick=self, control=button) for button in self._device.buttons.values()]
        feeders += [HatFeeder(virtual_joystick=self, control=hat) for hat in self._device.hats.values()]
        return feeders

    def run(self):
        for feeder in self._feeders:
            feeder.start()
        for feeder in self._feeders:
            feeder.join()
