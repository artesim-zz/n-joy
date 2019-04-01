import threading
import zmq

import njoy_core.core.parsers.design_parser
from .actuators import Actuator
from .model import CoreRequest
from .model import InputNodeRegisterRequest, InputNodeRegisterReply
from .model import OutputNodeCapabilities, OutputNodeAssignments
from .model import InputNode, OutputNode, PhysicalDevice, VirtualDevice, Axis, Button, Hat
from .multiplexers import InputMultiplexer, OutputMultiplexer


class CoreException(Exception):
    pass


class Core(threading.Thread):
    __INTERNAL_MUX_IN__ = 'inproc://core/internal/mux_in'
    __INTERNAL_MUX_OUT__ = 'inproc://core/internal/mux_out'

    def __init__(self, *, context, input_events, output_events, requests):
        super().__init__()

        self._ctx = context

        self._mux_in = InputMultiplexer(context=self._ctx,
                                        frontend=input_events,
                                        backend=self.__INTERNAL_MUX_IN__)

        self._mux_out = OutputMultiplexer(context=self._ctx,
                                          frontend=output_events,
                                          backend=self.__INTERNAL_MUX_OUT__)

        self._requests = self._ctx.socket(zmq.REP)
        self._requests.bind(requests)

    @staticmethod
    def _register_input_node(available_devices):
        node = InputNode()

        for (guid, name) in available_devices:
            device = PhysicalDevice.find(guid=guid, name=name)
            if device:
                node.append(device)

        return node

    @staticmethod
    def _register_output_node(controls, device_capabilities):
        node = OutputNode()

        remaining_axes = [c for c in controls if isinstance(c, Axis) and not c.is_assigned]
        remaining_buttons = [c for c in controls if isinstance(c, Button) and not c.is_assigned]
        remaining_hats = [c for c in controls if isinstance(c, Hat) and not c.is_assigned]

        for dc in device_capabilities:
            device = VirtualDevice(node=node)

            nb_axes = min(len(remaining_axes), dc['max_nb_axes'])
            nb_buttons = min(len(remaining_buttons), dc['max_nb_buttons'])
            nb_hats = min(len(remaining_hats), dc['max_nb_hats'])

            for axis in remaining_axes[0:nb_axes]:
                device.register_axis(axis)

            for button in remaining_buttons[0:nb_buttons]:
                device.register_button(button)

            for hat in remaining_hats[0:nb_hats]:
                device.register_hat(hat)

            remaining_axes = remaining_axes[nb_axes:]
            remaining_buttons = remaining_buttons[nb_buttons:]
            remaining_hats = remaining_hats[nb_hats:]

        return node

    def _handshake(self):
        parsed_design = njoy_core.core.parsers.design_parser.parse_design()
        devices = parsed_design['input_devices']
        controls = parsed_design['controls']

        # Accepts requests until we've registered all the input and output nodes
        while devices or controls:
            request = CoreRequest.recv(self._requests)

            if isinstance(request, InputNodeRegisterRequest):
                reply = InputNodeRegisterReply(node=self._register_input_node(request.available_devices))
                devices = [d for d in devices if not d.is_assigned]

            elif isinstance(request, OutputNodeCapabilities):
                reply = OutputNodeAssignments(node=self._register_output_node(controls, request.capabilities))
                controls = [c for c in controls if not c.is_assigned]

            else:
                raise CoreException("Unexpected request : {}".format(request.command))

            reply.send(self._requests)

        return [Actuator(context=self._ctx,
                         input_endpoint=self.__INTERNAL_MUX_IN__,
                         output_endpoint=self.__INTERNAL_MUX_OUT__,
                         virtual_control=control)
                for control in parsed_design['controls']]

    def run(self):
        threads = [self._mux_in, self._mux_out]
        threads.extend(self._handshake())

        for t in threads:
            t.start()
        for t in threads:
            t.join()
