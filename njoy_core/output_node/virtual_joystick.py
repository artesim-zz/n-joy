import gevent
import gevent.pool
import threading

from zmq import green as zmq

from njoy_core.common.messages import MessageType, HatValue, Message, AxisEvent, ButtonEvent, HatEvent
from njoy_core.output_node import vjoy_device


class Feeder(gevent.greenlet):
    def __init__(self, virtual_joystick, ctrl_id):
        super().__init__()
        self._device_id = virtual_joystick.device_id
        self._ctrl_id = ctrl_id
        self._output_device = virtual_joystick.output_device
        self._ctx = virtual_joystick.ctx
        self._events_endpoint = virtual_joystick.events_endpoint

    def _subscribe(self, socket):
        raise NotImplementedError

    def _handle_event(self, event):
        raise NotImplementedError

    def run(self):
        socket = self._ctx.socket(zmq.SUB)
        socket.connect(self._events_endpoint)
        self._subscribe(socket)

        while True:
            msg = Message.recv(socket)
            self._handle_event(msg)


class AxisFeeder(Feeder):
    @staticmethod
    def _to_float_axis(_axis_value):
        return _axis_value / 32768 if _axis_value < 0 else _axis_value / 32767

    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, AxisEvent(self._device_id, self._ctrl_id).header_parts)

    def _handle_event(self, event):
        self._output_device.set_axis(axis_id=self._ctrl_id,
                                     axis_value=self._to_float_axis(event.value))


class ButtonFeeder(Feeder):
    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, ButtonEvent(self._device_id, self._ctrl_id).header_parts)

    def _handle_event(self, event):
        self._output_device.set_button(button_id=self._ctrl_id,
                                       state=event.state)


class HatFeeder(Feeder):
    # -1 for none (not pressed), or in range [0 .. 35900] (tenth of degrees)
    __to_continuous_pov = {HatValue.HAT_UP: 0,
                           HatValue.HAT_UP_RIGHT: 4500,
                           HatValue.HAT_RIGHT: 9000,
                           HatValue.HAT_DOWN_RIGHT: 13500,
                           HatValue.HAT_DOWN: 18000,
                           HatValue.HAT_DOWN_LEFT: 22500,
                           HatValue.HAT_LEFT: 27000,
                           HatValue.HAT_UP_LEFT: 31500,
                           HatValue.HAT_CENTER: -1}

    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, HatEvent(self._device_id, self._ctrl_id).header_parts)

    def _handle_event(self, event):
        self._output_device.set_axis(pov_id=self._ctrl_id,
                                     pov_value=self.__to_continuous_pov[event.value])


class VirtualJoystick(threading.Thread):
    __MAX_NB_DEVICES__ = 16
    __MAX_NB_AXES__ = 8
    __MAX_NB_BUTTONS__ = 128
    __MAX_NB_HATS__ = 4

    @classmethod
    def max_nb_devices(cls):
        return cls.__MAX_NB_DEVICES__

    @classmethod
    def device_capabilities(cls, device_id=None):
        if device_id is None:
            return [cls.device_capabilities(i) for i in range(cls.max_nb_devices())]
        else:
            return {'device_id': device_id,
                    'max_nb_axes': cls.__MAX_NB_AXES__,
                    'max_nb_buttons': cls.__MAX_NB_BUTTONS__,
                    'max_nb_hats': cls.__MAX_NB_HATS__}

    def __init__(self, device_id, controls, context, events_endpoint):
        super().__init__(name="/virtual_joysticks/{}".format(device_id))
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._device_id = device_id
        self._output_device = vjoy_device.VJoyDevice(device_id=device_id)
        self._controls = [self._make_feeder(c) for c in controls]

    @property
    def ctx(self):
        return self._ctx

    @property
    def events_endpoint(self):
        return self._events_endpoint

    @property
    def device_id(self):
        return self._device_id

    @property
    def output_device(self):
        return self._output_device

    def _make_feeder(self, feeder_def):
        feeder_class = {MessageType.AXIS_EVENT: AxisFeeder,
                        MessageType.BUTTON_EVENT: ButtonFeeder,
                        MessageType.HAT_EVENT: HatFeeder}
        try:
            return feeder_class[feeder_def['ctrl_type']](virtual_joystick=self, ctrl_id=feeder_def['ctrl_id'])
        except KeyError as e:
            raise Exception("Unknown control type : {}".format(e))

    def run(self):
        group = gevent.pool.Group()
        for control in self._controls:
            group.start(control)
        group.join()
