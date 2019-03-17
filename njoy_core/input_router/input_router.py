import gevent.pool
import threading
import zmq.green as zmq

from njoy_core.common.messages import *
import njoy_core.parsers.device_mapping
from .controls import Axis, Button, Hat, PseudoButton


class InputRouterException(Exception):
    pass


class InputRouter(threading.Thread):
    def __init__(self, context, input_nodes_endpoint, requests_endpoint, output_nodes_endpoint):
        super().__init__()
        self._ctx = context

        self._input_nodes_endpoint = input_nodes_endpoint
        self._input_nodes_internal_endpoint = 'inproc://input_router/internal/input_events'

        self._requests_endpoint = requests_endpoint

        self._output_nodes_internal_endpoint = 'inproc://input_router/internal/output_events'
        self._output_nodes_endpoint = output_nodes_endpoint

        self._device_mappings = njoy_core.parsers.device_mapping.parse_device_mappings()
        self._idx_controls_by_device = dict()

    @property
    def ctx(self):
        return self._ctx

    @property
    def input_nodes_internal_endpoint(self):
        return self._input_nodes_internal_endpoint

    @property
    def output_nodes_internal_endpoint(self):
        return self._output_nodes_internal_endpoint

    def _register_controls(self, device_name):
        if device_name in self._idx_controls_by_device:
            raise InputRouterException("Already registered controls of {}".format(device_name))

        group = gevent.pool.Group()
        for control in self._device_mappings[device_name]['controls']:
            if control['type'] == 'axis':
                group.start(Axis(router=self,
                                 device_name=device_name,
                                 ctrl_id=control['id'],
                                 aliases=control['aliases']))
            elif control['type'] == 'button':
                group.start(Button(router=self,
                                   device_name=device_name,
                                   ctrl_id=control['id'],
                                   aliases=control['aliases']))
            elif control['type'] == 'hat':
                group.start(Hat(router=self,
                                device_name=device_name,
                                ctrl_id=control['id'],
                                direction=control['direction'],
                                aliases=control['aliases']))
            elif control['type'] == 'pseudo_button':
                group.start(PseudoButton(router=self,
                                         device_name=device_name,
                                         neither_ids=control['neither_ids'],
                                         aliases=control['aliases']))

        self._idx_controls_by_device[device_name] = group

    def _input_nodes_handler(self):
        frontend = self._ctx.socket(zmq.PULL)
        frontend.bind(self._input_nodes_endpoint)
        backend = self._ctx.socket(zmq.PUB)
        backend.bind(self._input_nodes_internal_endpoint)
        zmq.proxy(frontend, backend)

    def _requests_handler(self):
        socket = self._ctx.socket(zmq.REP)
        socket.bind(self._requests_endpoint)

        while True:
            request = TypedMessage.recv(socket)
            if request.command == 'register':
                registered = list()
                for device_name in request.args:
                    if device_name not in self._device_mappings:
                        continue
                    self._register_controls(device_name)
                    registered.append(device_name)
                Reply('registered', *registered).send(socket)
            else:
                raise InputRouterException("Unexpected command : {}".format(request.command))

    def _output_nodes_handler(self):
        # TODO: probably not necessary, they can all publish themselves
        frontend = self._ctx.socket(zmq.PULL)
        frontend.bind(self._output_nodes_internal_endpoint)
        backend = self._ctx.socket(zmq.PUB)
        backend.bind(self._output_nodes_endpoint)
        zmq.proxy(frontend, backend)

    def run(self):
        input_nodes_handler = gevent.spawn(self._input_nodes_handler)
        requests_handler = gevent.spawn(self._requests_handler)
        output_nodes_handler = gevent.spawn(self._output_nodes_handler)
        gevent.joinall([input_nodes_handler,
                        requests_handler,
                        output_nodes_handler])
