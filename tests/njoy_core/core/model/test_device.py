# pylint: skip-file
import pytest

from njoy_core.core.model import InputNode, OutputNode
from njoy_core.core.model import PhysicalDevice, VirtualDevice
from njoy_core.core.model import DeviceInvalidNodeError, DeviceNotFoundError
from njoy_core.core.model import DeviceInvalidParamsError, DeviceAliasNotFoundError, DeviceGuidNotFoundError
from njoy_core.core.model import DeviceNameNotFoundError, DeviceAmbiguousNameError, DeviceInvalidLookupError
from njoy_core.core.model import DeviceDuplicateAliasError, DeviceDuplicateGuidError, DeviceOverflowError


@pytest.fixture(scope="function",
                params=['input_node_instance', 'input_node_id'])
def input_node(request):
    if request.param == 'input_node_instance':
        yield InputNode()
    elif request.param == 'input_node_id':
        node = InputNode()
        yield node.id


@pytest.fixture(scope="function",
                params=['output_node_instance', 'output_node_id'])
def output_node(request):
    if request.param == 'output_node_instance':
        yield OutputNode()
    elif request.param == 'output_node_id':
        node = OutputNode()
        yield node.id


@pytest.mark.ensure_clean_output_node_cache
class TestVirtualDeviceInstantiation:
    def test_case_1(self):
        """The node parameter is required and must be an existing instance of an OutputNode, or an id of one."""
        with pytest.raises(DeviceInvalidNodeError):
            _ = VirtualDevice()

    def test_case_2(self):
        """The node parameter is required and must be an existing instance of an OutputNode, or an id of one."""
        with pytest.raises(DeviceInvalidNodeError):
            _ = VirtualDevice(node='xxx')

    def test_case_3(self):
        """The node parameter is required and must be an existing instance of an OutputNode, or an id of one."""
        with pytest.raises(DeviceInvalidNodeError):
            _ = VirtualDevice(node=0)

    def test_case_4(self, input_node):
        """The node parameter is required and must be an existing instance of an OutputNode, or an id of one."""
        with pytest.raises(DeviceInvalidNodeError):
            _ = VirtualDevice(node=input_node)

    def test_case_5(self, output_node):
        """The new VirtualDevice is automatically registered to the given node and receives an id from it"""
        device = VirtualDevice(node=output_node)
        assert device.id == 0
        device = VirtualDevice(node=output_node)
        assert device.id == 1


@pytest.mark.ensure_clean_output_node_cache
class TestVirtualDeviceLookup:
    def test_case_1(self, output_node):
        """Later on at run time, we'll receive messages referencing a node_id/device_id,
         and we'll use that to find the right instance."""
        _ = VirtualDevice(node=output_node)
        b = VirtualDevice(node=output_node)
        _ = VirtualDevice(node=output_node)
        device = VirtualDevice.find(node=output_node, dev=1)
        assert device is b

    def test_case_2(self, output_node):
        """Later on at run time, we'll receive messages referencing a node_id/device_id,
         and we'll use that to find the right instance."""
        with pytest.raises(DeviceNotFoundError):
            _ = VirtualDevice.find(node=output_node, dev=1)


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_physical_device_cache
class TestPhysicalDeviceInstantiation:
    def test_case_1(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        with pytest.raises(DeviceInvalidParamsError):
            _ = PhysicalDevice()

    def test_case_2(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        with pytest.raises(DeviceInvalidParamsError):
            _ = PhysicalDevice(alias='alias')

    def test_case_3(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        with pytest.raises(DeviceInvalidParamsError):
            _ = PhysicalDevice(guid='guid')

    def test_case_4(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        with pytest.raises(DeviceInvalidParamsError):
            _ = PhysicalDevice(name='name')

    def test_case_5(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        with pytest.raises(DeviceInvalidParamsError):
            _ = PhysicalDevice(guid='guid', name='name')

    def test_case_6(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        _ = PhysicalDevice(alias='alias', guid='guid')

    def test_case_7(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        _ = PhysicalDevice(alias='alias', name='name')

    def test_case_8(self):
        """A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID
        (or both), instead of a node."""
        _ = PhysicalDevice(alias='alias', guid='guid', name='name')

    def test_case_9(self):
        """The alias and the GUID must be unique."""
        _ = PhysicalDevice(alias='alias', guid='guid_1')
        with pytest.raises(DeviceDuplicateAliasError):
            _ = PhysicalDevice(alias='alias', guid='guid_2')

    def test_case_10(self):
        """The alias and the GUID must be unique."""
        _ = PhysicalDevice(alias='alias', guid='guid')
        with pytest.raises(DeviceDuplicateGuidError):
            _ = PhysicalDevice(alias='alias_2', guid='guid')

    def test_case_11(self):
        """The alias and the GUID must be unique."""
        _ = PhysicalDevice(alias='alias', guid='guid_1')
        _ = PhysicalDevice(alias='alias_2', guid='guid_2')

    def test_case_12(self):
        """The name may not be unique, but must be disambiguated by a GUID (existing instances also checked)."""
        _ = PhysicalDevice(alias='alias', name='name')
        with pytest.raises(DeviceAmbiguousNameError):
            _ = PhysicalDevice(alias='alias_2', name='name')

    def test_case_13(self):
        """The name may not be unique, but must be disambiguated by a GUID (existing instances also checked)."""
        _ = PhysicalDevice(alias='alias', name='name')
        with pytest.raises(DeviceAmbiguousNameError):
            _ = PhysicalDevice(alias='alias_2', name='name', guid='guid')

    def test_case_14(self):
        """The name may not be unique, but must be disambiguated by a GUID (existing instances also checked)."""
        _ = PhysicalDevice(alias='alias', name='name', guid='guid_1')
        _ = PhysicalDevice(alias='alias_2', name='name', guid='guid_2')

    def test_case_99(self, input_node):
        """The PhysicalDevice is then considered unassigned until it is registered to a node during the handshake phase.
        """
        device = PhysicalDevice(alias='alias', name='name')
        assert device.is_assigned is False
        InputNode().append(device)
        assert device.is_assigned is True


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_physical_device_cache
class TestPhysicalDeviceLookup:
    def test_case_1(self):
        """When parsing the controls, the PhysicalDevices will typically be retrieved by alias."""
        with pytest.raises(DeviceInvalidLookupError):
            _ = PhysicalDevice.find()

    def test_case_2(self):
        """When parsing the controls, the PhysicalDevices will typically be retrieved by alias."""
        with pytest.raises(DeviceAliasNotFoundError):
            _ = PhysicalDevice.find(alias='alias_1')

    def test_case_3(self):
        """When parsing the controls, the PhysicalDevices will typically be retrieved by alias."""
        _ = PhysicalDevice(alias='alias_1', guid='guid_1')
        b = PhysicalDevice(alias='alias_2', guid='guid_2')
        _ = PhysicalDevice(alias='alias_3', guid='guid_3')
        device = PhysicalDevice.find(alias='alias_2')
        assert device is b

    def test_case_4(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        with pytest.raises(DeviceGuidNotFoundError):
            _ = PhysicalDevice.find(guid='guid')

    def test_case_5(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        _ = PhysicalDevice(alias='alias_1', guid='guid_1')
        b = PhysicalDevice(alias='alias_2', guid='guid_2')
        _ = PhysicalDevice(alias='alias_3', guid='guid_3')
        device = PhysicalDevice.find(guid='guid_2')
        assert device is b

    def test_case_6(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        with pytest.raises(DeviceNameNotFoundError):
            _ = PhysicalDevice.find(name='name')

    def test_case_7(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        _ = PhysicalDevice(alias='alias_1', name='name_1')
        b = PhysicalDevice(alias='alias_2', name='name_2')
        _ = PhysicalDevice(alias='alias_3', name='name_3')
        device = PhysicalDevice.find(name='name_2')
        assert device is b

    def test_case_8(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        _ = PhysicalDevice(alias='alias_1', name='name', guid='guid_1')
        _ = PhysicalDevice(alias='alias_2', name='name', guid='guid_2')
        _ = PhysicalDevice(alias='alias_3', name='name', guid='guid_3')
        with pytest.raises(DeviceAmbiguousNameError):
            _ = PhysicalDevice.find(name='name')

    def test_case_9(self):
        """During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name."""
        _ = PhysicalDevice(alias='alias_1', name='name', guid='guid_1')
        b = PhysicalDevice(alias='alias_2', name='name', guid='guid_2')
        _ = PhysicalDevice(alias='alias_3', name='name', guid='guid_3')
        device = PhysicalDevice.find(name='name', guid='guid_2')
        assert device is b

    def test_case_10(self, input_node):
        """Finally at run time, the PhysicalDevices will be retrieved node_id/device_id from the event messages."""
        with pytest.raises(DeviceNotFoundError):
            _ = PhysicalDevice.find(node=input_node, dev=1)

    def test_case_11(self, input_node):
        """Finally at run time, the PhysicalDevices will be retrieved node_id/device_id from the event messages."""
        node = InputNode.find(node=input_node) if isinstance(input_node, int) else input_node
        node.append(PhysicalDevice(alias='alias_1', guid='guid_1'))
        b = PhysicalDevice(alias='alias_2', guid='guid_2')
        node.append(b)
        node.append(PhysicalDevice(alias='alias_3', guid='guid_3'))
        device = PhysicalDevice.find(node=node, dev=1)
        assert device is b


class MockAxis:
    def __init__(self, dev):
        self.dev = None
        self.id = None
        dev.register_axis(self)


class MockButton:
    def __init__(self, dev):
        self.dev = None
        self.id = None
        dev.register_button(self)


class MockHat:
    def __init__(self, dev):
        self.dev = None
        self.id = None
        dev.register_hat(self)


class TestContainer:
    @pytest.mark.parametrize("control_cls,nb_controls", [(MockAxis, 8), (MockButton, 128), (MockHat, 4)])
    def test_case_1(self, control_cls, nb_controls):
        """PhysicalDevices and VirtualDevices are containers for up to 8 Axis, 128 Button and 4 Hat instances."""
        device = PhysicalDevice(alias='alias', name='name')
        for _ in range(nb_controls):
            control_cls(dev=device)
        with pytest.raises(DeviceOverflowError):
            control_cls(dev=device)

    @pytest.mark.parametrize("control_cls,nb_controls", [(MockAxis, 8), (MockButton, 128), (MockHat, 4)])
    def test_case_1(self, control_cls, nb_controls):
        """PhysicalDevices and VirtualDevices are containers for up to 8 Axis, 128 Button and 4 Hat instances."""
        device = VirtualDevice(node=OutputNode())
        for _ in range(nb_controls):
            control_cls(dev=device)
        with pytest.raises(DeviceOverflowError):
            control_cls(dev=device)
