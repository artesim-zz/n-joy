import pytest

from njoy_core.core.model import InputNode, OutputNode
from njoy_core.core.model import PhysicalDevice, VirtualDevice
from njoy_core.core.model import DeviceAliasNotFoundError, DeviceRegisterControlError
from njoy_core.core.model import ControlInvalidDeviceError, Axis, Button, Hat


@pytest.fixture(scope="function")
def input_node():
    return InputNode()


@pytest.fixture(scope="function")
def output_node():
    return OutputNode()


@pytest.fixture(scope="function",
                params=['physical_device_instance', 'physical_device_alias', 'virtual_device'])
def device(request, input_node, output_node):
    if request.param == 'physical_device_instance':
        device = PhysicalDevice(alias='physical_device', name='physical_device')
        input_node.append(device)
        return device

    elif request.param == 'physical_device_alias':
        device = PhysicalDevice(node=input_node, alias='physical_device', name='physical_device')
        input_node.append(device)
        return 'physical_device'

    elif request.param == 'virtual_device':
        return VirtualDevice(node=output_node)


@pytest.fixture(scope="module",
                params=[Axis, Button, Hat])
def control_cls(request):
    return request.param


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_output_node_cache
@pytest.mark.ensure_clean_physical_device_cache
class TestInstantiation:
    def test_case_1(self, control_cls):
        """If neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created."""
        control = control_cls()
        assert control.is_assigned is False

    def test_case_2(self, control_cls):
        """If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the
         control id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.
        """
        with pytest.raises(DeviceAliasNotFoundError):
            _ = control_cls(dev='xxx')

    def test_case_3(self, control_cls):
        """If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the
         control id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.
        """
        with pytest.raises(ControlInvalidDeviceError):
            _ = control_cls(dev=1)

    def test_case_4(self, control_cls):
        """If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the
         control id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.
        """
        with pytest.raises(ControlInvalidDeviceError):
            _ = control_cls(dev=object())

    def test_case_5(self, device, control_cls):
        """If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the
         control id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.
        """
        control = control_cls(dev=device)
        assert control.is_assigned is True
        assert control.id == 0
        control = control_cls(dev=device)
        assert control.is_assigned is True
        assert control.id == 1

    def test_case_6(self, device, control_cls):
        """If 'ctrl_id' is also specified, the device will try to register the new control with this id (if available).
        """
        _ = control_cls(dev=device)
        _ = control_cls(dev=device)
        _ = control_cls(dev=device)
        with pytest.raises(DeviceRegisterControlError):
            _ = control_cls(dev=device, ctrl_id=1)

    def test_case_7(self, device, control_cls):
        """If 'ctrl_id' is also specified, the device will try to register the new control with this id (if available).
        """
        control = control_cls(dev=device, ctrl_id=3)
        assert control.is_assigned is True
        assert control.id == 3

    @pytest.mark.parametrize("device,expected", [(PhysicalDevice(alias='a', name='n'), True),
                                                 (VirtualDevice(node=OutputNode()), False)])
    def test_case_8(self, device, expected, control_cls):
        """[...] for controls registered to a physical device ("physical controls")"""
        control = control_cls(dev=device)
        assert control.is_physical_control == expected
