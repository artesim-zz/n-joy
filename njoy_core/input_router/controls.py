import gevent
from zmq import green as zmq

from njoy_core.common.messages import TypedMessage, AxisOldEvent, ButtonOldEvent, HatValue, HatOldEvent


class Control(gevent.Greenlet):
    def __init__(self, router, device_name, ctrl_id, aliases):
        super().__init__()
        self._ctx = router.ctx
        self._input_endpoint = router.input_nodes_internal_endpoint
        self._output_endpoint = router.output_nodes_internal_endpoint
        self._device_name = device_name
        self._ctrl_id = ctrl_id
        self._aliases = aliases

    def _subscribe(self, socket):
        raise NotImplementedError

    def _process(self, input_messages):
        raise NotImplementedError

    def _run(self):
        socket_in = self._ctx.socket(zmq.SUB)
        socket_in.connect(self._input_endpoint)
        self._subscribe(socket_in)

        socket_out = self._ctx.socket(zmq.PUSH)
        socket_out.connect(self._output_endpoint)

        while True:
            msg = TypedMessage.recv(socket_in)
            for msg_out in self._process(msg):
                msg_out.send(socket_out)


class Axis(Control):
    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, AxisOldEvent(self._device_name, self._ctrl_id).header_parts)

    def _process(self, input_message):
        return [AxisOldEvent(self._device_name, alias, input_message.value)
                for alias in self._aliases]


class Button(Control):
    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, ButtonOldEvent(self._device_name, self._ctrl_id).header_parts)

    def _process(self, input_message):
        return [ButtonOldEvent(self._device_name, alias, input_message.value)
                for alias in self._aliases]


class Hat(Control):
    __TO_HAT_VALUE__ = {
        'up': HatValue.HAT_UP,
        'up-right': HatValue.HAT_UP_RIGHT,
        'right': HatValue.HAT_RIGHT,
        'down-right': HatValue.HAT_DOWN_RIGHT,
        'down': HatValue.HAT_DOWN,
        'down-left': HatValue.HAT_DOWN_LEFT,
        'left': HatValue.HAT_LEFT,
        'up-left': HatValue.HAT_UP_LEFT
    }

    def __init__(self, router, device_name, ctrl_id, direction, aliases):
        super().__init__(router, device_name, ctrl_id, aliases)
        self._direction = self.__TO_HAT_VALUE__[direction]

    def _subscribe(self, socket):
        socket.setsockopt(zmq.SUBSCRIBE, HatOldEvent(self._device_name, self._ctrl_id).header_parts)

    def _process(self, input_message):
        return [ButtonOldEvent(self._device_name, alias, input_message.value == self._direction)
                for alias in self._aliases]


class PseudoButton(Control):
    def __init__(self, router, device_name, neither_ids, aliases):
        super().__init__(router, device_name, None, aliases)
        self._neither_ids = neither_ids
        self._input_states = {ctrl_id: False for ctrl_id in neither_ids}

    def _subscribe(self, socket):
        for i in self._neither_ids:
            socket.setsockopt(zmq.SUBSCRIBE, ButtonOldEvent(self._device_name, i).header_parts)

    def _process(self, input_message):
        self._input_states[input_message.ctrl_id] = input_message.value
        output_state = not any(list(self._input_states.values()))
        return [ButtonOldEvent(self._device_name, alias, output_state)
                for alias in self._aliases]

# EOF
