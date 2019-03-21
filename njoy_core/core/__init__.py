import gevent.pool
import zmq.green as zmq

from njoy_core.common import messages
from njoy_core.parsers.design import Design
from .multiplexers import InputMultiplexer, OutputMultiplexer
from .actuators import AxisActuator, ButtonActuator, HatActuator


class CoreException(Exception):
    pass


class Core(gevent.Greenlet):
    def __init__(self, context, input_events_endpoint, output_events_endpoint, requests_endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.REP)
        self._socket.bind(requests_endpoint)
        self._mux_in = InputMultiplexer(context=self._ctx,
                                        internal_endpoint='inproc://core/internal/mux_in',
                                        external_endpoint=input_events_endpoint)
        self._mux_out = OutputMultiplexer(context=self._ctx,
                                          internal_endpoint='inproc://core/internal/mux_out',
                                          external_endpoint=output_events_endpoint)
        self._design = Design()

    def _assign_actuators(self, device_capabilities):
        def _to_ctrl_assignment(_ctrl):
            event_kind = {AxisActuator: messages.ControlEventKind.AXIS,
                          ButtonActuator: messages.ControlEventKind.BUTTON,
                          HatActuator: messages.ControlEventKind.HAT}
            return {'event_kind': event_kind[_ctrl], 'ctrl_id': _ctrl.actuator.ctrl_id}

        remaining_axes = list(filter(lambda c: isinstance(c, AxisActuator), self._controls))
        remaining_buttons = list(filter(lambda c: isinstance(c, ButtonActuator), self._controls))
        remaining_hats = list(filter(lambda c: isinstance(c, HatActuator), self._controls))

        # TODO: robustness : check if all the controls were assigned or not
        return [  # Build an assignment structure for each device
                {'device_id': _id,
                 'controls': [_to_ctrl_assignment(c)
                              for c in ([remaining_axes.pop() for _ in range(nb_axes)] +
                                        [remaining_buttons.pop() for _ in range(nb_buttons)] +
                                        [remaining_hats.pop() for _ in range(nb_hats)])]}

                # Get as many unassigned actuators as possible, according to each device capabilities
                for (_id, nb_axes, nb_buttons, nb_hats) in [(dc['device_id'],
                                                             min(len(remaining_axes), dc['max_nb_axes']),
                                                             min(len(remaining_buttons), dc['max_nb_buttons']),
                                                             min(len(remaining_hats), dc['max_nb_hats']))
                                                            for dc in device_capabilities]]

    def _setup_external_nodes(self, design):
        nb_registered_nodes = 0
        unassigned_inputs = design.required_inputs
        unassigned_controls = list()  # design.controls : XXX: For now, skip output nodes registration

        # Only accepts requests as long as there's still something to be assigned.
        while unassigned_inputs or unassigned_controls:
            request = messages.CoreRequest.recv(self._socket)
            print("Core: received request")

            if isinstance(request, messages.InputNodeRegisterRequest):
                # XXX: How do we know we didn't already have a register request for this particular node ?
                #      Maybe switch to a ROUTER socket instead, and grab the peer socket identity
                #      For now, just rely on the fact that the InputNode only registers once, before starting its loop.
                #      So just keep count of the number of registered nodes and use that as a make-shift node_id.
                node_id = nb_registered_nodes
                nb_registered_nodes += 1

                # XXX: At some point, we should tell the node that we're only interested in a subset of its controls
                #      For now, just accepts whole devices
                # XXX: Also, how do we handle multiple devices with the same name ?
                #    : How unique really are the device GUIDs ?
                device_ids_map = dict()
                for device_name in request.devices:
                    if device_name in unassigned_inputs:
                        device_ids_map[unassigned_inputs[device_name]['njoy_device_id']] = device_name
                        del unassigned_inputs[device_name]

                messages.InputNodeRegisterReply(node_id=node_id, device_ids_map=device_ids_map).send(self._socket)
                print("Core: sent reply")

            else:
                raise CoreException("Unexpected request : {}".format(request.command))

        print("Core: done registering")
        gevent.sleep(0.001)

    def _run(self):
        # XXX: stubbed for now : will return a passthrough design with all controls of all known devices
        # designs can include "from ... import ... as ..." to use device maps
        # parse design and associated device maps
        self._setup_external_nodes(self._design)

        print("Starting Muxes")
        grp = gevent.pool.Group()
        grp.start(self._mux_in)
        grp.start(self._mux_out)
        # for control in design.controls:
        #     grp.start(control)
        grp.join()

# EOF
