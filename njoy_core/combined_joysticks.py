import gevent.pool
import threading
import zmq.green as zmq

from njoy_core import controls
from njoy_core.io import virtual_output
from njoy_core.messages import Message, MessageType, HidRequest, HidDeviceFullStateReply


class ControlPoolException(Exception):
    pass


class VirtualJoystick(threading.Thread):
    __MAX_NB_AXES__ = 8
    __MAX_NB_BALLS__ = 0
    __MAX_NB_BUTTONS__ = 128
    __MAX_NB_HATS__ = 4

    @classmethod
    def dispatch_controls(cls, control_events):
        AXIS = MessageType.HID_AXIS_EVENT
        BALL = MessageType.HID_BALL_EVENT
        BUTTON = MessageType.HID_BUTTON_EVENT
        HAT = MessageType.HID_HAT_EVENT

        ctrl_grps = {
            AXIS: {'max': cls.__MAX_NB_AXES__, 'groups': list()},
            BALL: {'max': cls.__MAX_NB_BALLS__, 'groups': list()},
            BUTTON: {'max': cls.__MAX_NB_BUTTONS__, 'groups': list()},
            HAT: {'max': cls.__MAX_NB_HATS__, 'groups': list()}
        }

        for ctrl_evt in control_events:
            if not ctrl_grps[ctrl_evt.msg_type]['groups']:
                ctrl_grps[ctrl_evt.msg_type]['groups'].append(list())

            if len(ctrl_grps[ctrl_evt.msg_type]['groups'][-1]) == ctrl_grps[ctrl_evt.msg_type]['max']:
                ctrl_grps[ctrl_evt.msg_type]['groups'].append(list())

            ctrl_grps[ctrl_evt.msg_type]['groups'][-1].append(ctrl_evt)

        return [{
            'axes': enumerate(ctrl_grps[AXIS]['groups'][i] if i < len(ctrl_grps[AXIS]['groups']) else list()),
            'balls': enumerate(ctrl_grps[BALL]['groups'][i] if i < len(ctrl_grps[BALL]['groups']) else list()),
            'buttons': enumerate(ctrl_grps[BUTTON]['groups'][i] if i < len(ctrl_grps[BUTTON]['groups']) else list()),
            'hats': enumerate(ctrl_grps[HAT]['groups'][i] if i < len(ctrl_grps[HAT]['groups']) else list())
        } for i in range(max([len(g['groups']) for g in ctrl_grps.values()]))]

    def __init__(self, device_id, context, events_endpoint):
        super(VirtualJoystick, self).__init__(name="/virtual_joysticks/{}".format(device_id))
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._device_id = device_id
        self._output_device = virtual_output.OutputDevice(device_id=device_id)

    @property
    def events_endpoint(self):
        return self._events_endpoint

    @property
    def device_id(self):
        return self._device_id

    def run(self):
        def _to_float_axis(_axis_value):
            return _axis_value / 32768 if _axis_value < 0 else _axis_value / 32767

        socket = self._ctx.socket(zmq.PULL)
        socket.bind(self._events_endpoint)

        while True:
            msg = Message.recv(socket)

            if msg.msg_type == MessageType.HID_AXIS_EVENT:
                self._output_device.set_axis(axis_id=msg.ctrl_id, axis_value=_to_float_axis(msg.value))

            elif msg.msg_type == MessageType.HID_BUTTON_EVENT:
                self._output_device.set_button(button_id=msg.ctrl_id, state=msg.state)

            elif msg.msg_type == MessageType.HID_HAT_EVENT:
                pass  # self._output_device.set_disc_pov(PovID=msg.ctrl_id, PovValue=msg.value)


class CombinedJoystick(threading.Thread):
    def __init__(self, hid_event_loop):
        super(CombinedJoystick, self).__init__()
        self._hid_event_loop = hid_event_loop
        self._ctx = hid_event_loop.ctx

    @property
    def ctx(self):
        return self._ctx

    @staticmethod
    def _hid_full_state(socket):
        ctrls = set()

        for joystick in ["Joystick - HOTAS Warthog",
                         "Throttle - HOTAS Warthog",
                         "MFG Crosswind V2",
                         "Saitek Pro Flight Throttle Quadrant"]:

            HidRequest('open', joystick).send(socket)
            full_state_msg = Message.recv(socket)

            if isinstance(full_state_msg, HidDeviceFullStateReply):
                for ctrl in full_state_msg.control_events:
                    if ctrl in ctrls:
                        print("Skipping duplicate control : {}".format(ctrl))
                    else:
                        ctrls.add(ctrl)

        return sorted(ctrls)

    def run(self):
        socket = self._ctx.socket(zmq.REQ)
        socket.connect(self._hid_event_loop.requests_endpoint)

        group = gevent.pool.Group()
        for virtual_joystick, ctrl_grp in [(VirtualJoystick(device_id=i,
                                                            context=self._ctx,
                                                            events_endpoint="inproc://virtual_joysticks/{}".format(i)),
                                            ctrl_grp)
                                           for (i, ctrl_grp) in
                                           enumerate(VirtualJoystick.dispatch_controls(self._hid_full_state(socket)))]:

            for ctrl in [controls.Control(virtual_joystick, ctrl_id, ctrl, self._hid_event_loop)
                         for ctrl_id, ctrl in ctrl_grp['axes']]:
                group.start(ctrl)

            for ctrl in [controls.Control(virtual_joystick, ctrl_id, ctrl, self._hid_event_loop)
                         for ctrl_id, ctrl in ctrl_grp['balls']]:
                group.start(ctrl)

            for ctrl in [controls.Control(virtual_joystick, ctrl_id, ctrl, self._hid_event_loop)
                         for ctrl_id, ctrl in ctrl_grp['buttons']]:
                group.start(ctrl)

            for ctrl in [controls.Control(virtual_joystick, ctrl_id, ctrl, self._hid_event_loop)
                         for ctrl_id, ctrl in ctrl_grp['hats']]:
                group.start(ctrl)

            virtual_joystick.start()

        gevent.sleep(0)
        HidRequest('start_event_loop').send(socket)
        Message.recv(socket)

        group.join()

# eof
