import os

from njoy_core.common.messages import CtrlKind

from .device_map import parse_device_maps


class Design:
    __BASE_DESIGNS_DIR__ = os.path.join(os.path.dirname(__file__),
                                        os.path.pardir,
                                        os.path.pardir,
                                        'njoy_designs')

    def __init__(self, design_file=None):
        if design_file is None:
            self._required_inputs, self._controls = self._make_passthrough_design(parse_device_maps())
        else:
            self._required_inputs, self._controls = dict(), list()

    @property
    def required_inputs(self):
        return self._required_inputs

    @property
    def controls(self):
        return self._controls

    def _make_passthrough_design(self, device_maps):
        required_inputs = dict()
        axes = list()
        buttons = list()
        hats = list()

        # Number of distinct input devices we've seen so far, used to come up with an internal 'njoy_device_id'.
        # The 'njoy_device_id' is to be used in the ControlEvent identity field coming from the input nodes.
        nb_input_devices = 0

        for device_name, device_map in device_maps.items():
            njoy_device_id = nb_input_devices
            nb_input_devices += 1

            required_inputs[device_name] = {'njoy_device_id': njoy_device_id,
                                            'axes': set(),
                                            'axes_by_alias': dict(),
                                            'buttons': set(),
                                            'buttons_by_alias': dict(),
                                            'hats': set(),
                                            'hats_by_alias': dict()}

            for control in device_map['controls']:
                if control['type'] == 'axis':
                    required_inputs[device_name]['axes'].add(control['id'])
                    for alias in control['aliases']:
                        required_inputs[device_name]['axes_by_alias'][alias] = control['id']
                    axes.append({'input_identities': [{'device': njoy_device_id,
                                                       'kind': CtrlKind.AXIS,
                                                       'control': control['id']}]})
                elif control['type'] == 'button':
                    required_inputs[device_name]['buttons'].add(control['id'])
                    for alias in control['aliases']:
                        required_inputs[device_name]['buttons_by_alias'][alias] = control['id']
                    buttons.append({'input_identities': [{'device': njoy_device_id,
                                                          'kind': CtrlKind.BUTTON,
                                                          'control': control['id']}],
                                    'is_pseudo_button': False})
                elif control['type'] == 'hat':
                    required_inputs[device_name]['hats'].add(control['id'])
                    for alias in control['aliases']:
                        required_inputs[device_name]['hats_by_alias'][alias] = control['id']
                    hats.append({'input_identities': [{'device': njoy_device_id,
                                                       'kind': CtrlKind.HAT,
                                                       'control': control['id']}]})
                elif control['type'] == 'pseudo_button':
                    for button_id in control['neither_ids']:
                        required_inputs[device_name]['buttons'].add(button_id)
                    for alias in control['aliases']:
                        required_inputs[device_name]['buttons_by_alias'][alias] = control['neither_ids']
                    buttons.append({'input_identities': [{'device': njoy_device_id,
                                                          'kind': CtrlKind.BUTTON,
                                                          'control': control_id}
                                                         for control_id in control['neither_ids']],
                                    'is_pseudo_button': True})

        return required_inputs, {'axes': axes, 'buttons': buttons, 'hats': hats}
