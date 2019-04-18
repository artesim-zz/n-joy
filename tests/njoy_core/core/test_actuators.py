# pylint: skip-file
import unittest.mock as mock
import pytest
import zmq

from njoy_core.core.actuator import Actuator
from njoy_core.core.model import InputNode, OutputNode
from njoy_core.core.model import PhysicalDevice, VirtualDevice
from njoy_core.core.model import Axis, Button, Hat, HatState
from njoy_core.core.model import VirtualControlEvent
from njoy_core.core.toolbox.essential_toolbox import EssentialToolbox


@pytest.fixture(scope="module")
def context():
    return zmq.Context()


@pytest.fixture(scope="module")
def physical_controls():
    node = InputNode()
    device = PhysicalDevice(node=node, alias='a', name='n')
    node.append(device)
    return {'axis': Axis(dev=device),
            'button': Button(dev=device),
            'hat': Hat(dev=device)}


@pytest.fixture(scope="module")
def virtual_controls(physical_controls):
    node = OutputNode()
    device = VirtualDevice(node=node)
    node.append(device)
    return {'axis': {'virtual_control': Axis(dev=device,
                                             processor=EssentialToolbox.passthrough,
                                             inputs=[physical_controls['axis']]),
                     'physical_control': physical_controls['axis']},
            'button': {'virtual_control': Button(dev=device,
                                                 processor=EssentialToolbox.passthrough,
                                                 inputs=[physical_controls['button']]),
                       'physical_control': physical_controls['button']},
            'hat': {'virtual_control': Hat(dev=device,
                                           processor=EssentialToolbox.passthrough,
                                           inputs=[physical_controls['hat']]),
                    'physical_control': physical_controls['hat']}}


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_output_node_cache
@pytest.mark.ensure_clean_physical_device_cache
class TestActuatorLoop:
    def test_case_1(self, mocker, context):
        node = InputNode()
        device = PhysicalDevice(node=node, alias='a', name='n')
        node.append(device)
        axis = Axis(dev=device)

        node = OutputNode()
        device = VirtualDevice(node=node)
        node.append(device)
        virtual_axis = Axis(dev=device,
                            processor=EssentialToolbox.passthrough,
                            inputs=[axis])

        actuator = Actuator(context=context,
                            input_endpoint='inproc://input',
                            output_endpoint='inproc://output',
                            virtual_control=virtual_axis)
        mocker.patch.object(actuator._socket, 'send_multipart', autospec=True)
        mocker.patch.object(actuator._socket, 'recv_multipart', autospec=True)
        with mock.patch('njoy_core.core.input_buffer.InputBuffer.state', new_callable=mocker.PropertyMock) as state:
            state.return_value = {axis: 0.1}
            actuator._socket.recv_multipart.return_value = [VirtualControlEvent(value=None)._serialize_value()]
            actuator.loop()
        actuator._socket.send_multipart.assert_called_with([VirtualControlEvent(value=0.1)._serialize_value()])

