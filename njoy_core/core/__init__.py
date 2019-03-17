import gevent.pool
import pickle
import threading
import zmq.green as zmq

from njoy_core.common.messages import MessageType, Message, HidReply
from .filtering_buffer import FilteringBuffer


class DesignRunnerException(Exception):
    pass


class DesignRunner(threading.Thread):
    def __init__(self, context, input_events_endpoint, output_events_endpoint, requests_endpoint):
        super().__init__()
        self._ctx = context
        self._input_events_endpoint = input_events_endpoint
        self._output_events_endpoint = output_events_endpoint
        self._requests_endpoint = requests_endpoint
        self._controls = self._load_design()

    @property
    def input_events_endpoint(self):
        return self._input_events_endpoint

    @property
    def output_events_endpoint(self):
        return self._output_events_endpoint

    def _load_design(self):
        return {
            'input_controls': list(),
            'design_controls': list(),
            'terminal_controls': list()
        }

    def _assign_terminal_controls(self, device_capabilities):
        def _to_ctrl_assignment(_ctrl):
            event_type = {InputAxis: MessageType.AXIS_EVENT,
                          InputButton: MessageType.BUTTON_EVENT,
                          InputHat: MessageType.HAT_EVENT}
            return {'event_type': event_type[_ctrl], 'ctrl_id': _ctrl.ctrl_id}

        remaining_axes = list(filter(lambda c: isinstance(c, InputAxis),
                                     self._controls['terminal_controls']))
        remaining_buttons = list(filter(lambda c: isinstance(c, InputButton),
                                        self._controls['terminal_controls']))
        remaining_hats = list(filter(lambda c: isinstance(c, InputHat),
                                     self._controls['terminal_controls']))

        # TODO: robustness : check if all the controls were assigned or not
        return [{'device_id': _id,
                 'controls': [_to_ctrl_assignment(c)
                              for c in ([remaining_axes.pop() for _ in range(nb_axes)] +
                                        [remaining_buttons.pop() for _ in range(nb_buttons)] +
                                        [remaining_hats.pop() for _ in range(nb_hats)])]}
                for (_id, nb_axes, nb_buttons, nb_hats) in [(dc['device_id'],
                                                             min(len(remaining_axes), dc['max_nb_axes']),
                                                             min(len(remaining_buttons), dc['max_nb_buttons']),
                                                             min(len(remaining_hats), dc['max_nb_hats']))
                                                            for dc in device_capabilities]]

    def _setup_output_nodes(self):
        socket = self._ctx.socket(zmq.REQ)
        socket.bind(self._requests_endpoint)
        request = Message.recv(socket)
        if request.command == 'register':
            HidReply(command='assignments',
                     *self._assign_terminal_controls([pickle.loads(dc) for dc in request.args]))

        else:
            raise DesignRunnerException("Unexpected request : {}".format(request.command))

    def run(self):
        self._setup_output_nodes()
        for group in self._controls.values():
            group.join()

# EOF
