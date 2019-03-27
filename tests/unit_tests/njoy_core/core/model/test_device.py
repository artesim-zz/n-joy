import pytest

from njoy_core.core.model.node import InputNode, OutputNode, NodeError
from njoy_core.core.model.device import PhysicalDevice, VirtualDevice, DeviceError


def test_virtual_device_1():
    """The node is required and must be an existing instance of OutputNode."""
    with pytest.raises(DeviceError):
        _ = VirtualDevice()


def test_virtual_device_2():
    """The node is required and must be an existing instance of OutputNode."""
    with pytest.raises(DeviceError):
        _ = VirtualDevice(node='xxx')


def test_virtual_device_3():
    """The node is required and must be an existing instance of OutputNode."""
    with pytest.raises(NodeError):
        _ = VirtualDevice(node=0)


def test_virtual_device_4():
    """The node is required and must be an existing instance of OutputNode."""
    with pytest.raises(DeviceError):
        _ = VirtualDevice(node=InputNode())


def test_virtual_device_5():
    """It is automatically registered to the given node and receives an id from it"""
    node = OutputNode()
    device = VirtualDevice(node=node)
    assert device.id == 0
    device = VirtualDevice(node=node)
    assert device.id == 1


def test_virtual_device_6():
    """No more than 16 devices per node are allowed"""
    node = OutputNode()
    for _ in range(16):
        _ = VirtualDevice(node=node)
    with pytest.raises(NodeError):
        _ = VirtualDevice(node=node)


def test_virtual_device_7():
    """Later on at run time, we'll receive messages referencing a node_id/device_id, and we'll use that to find the
    right instance."""
    node = OutputNode()
    a = VirtualDevice(node=node)
    b = VirtualDevice(node=node)
    c = VirtualDevice(node=node)
    device = VirtualDevice(node=node, dev=1)
    assert device is b


def test_physical_device_1():
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(alias='a')


def test_physical_device_2():
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(name='n')


def test_physical_device_3():
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(guid='g')


def test_physical_device_4():
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(name='n', guid='g')


def test_physical_device_5():
    device_1 = PhysicalDevice(alias='a', name='n')
    assert device_1.alias == 'a'
    assert device_1.name == 'n'


def test_physical_device_6():
    device_2 = PhysicalDevice(alias='a2', guid='g2')
    assert device_2.alias == 'a2'
    assert device_2.guid == 'g2'


def test_physical_device_7():
    device_3 = PhysicalDevice(alias='a3', name='n3', guid='g3')
    assert device_3.alias == 'a3'
    assert device_3.name == 'n3'
    assert device_3.guid == 'g3'


def test_physical_device_8():
    _ = PhysicalDevice(alias='a', name='n')
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(alias='a', name='xxx')


def test_physical_device_9():
    device_1 = PhysicalDevice(alias='a', name='n')
    device_2 = PhysicalDevice(alias='a', guid='g')
    assert device_2.alias == 'a'
    assert device_2.name == 'n'
    assert device_2.guid == 'g'
    assert device_2 is device_1


def test_physical_device_10():
    _ = PhysicalDevice(alias='a', guid='g')
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(alias='a', guid='xxx')


def test_physical_device_11():
    device_1 = PhysicalDevice(alias='a', guid='g')
    device_2 = PhysicalDevice(alias='a', name='n')
    assert device_2.alias == 'a'
    assert device_2.name == 'n'
    assert device_2.guid == 'g'
    assert device_2 is device_1


def test_physical_device_12():
    _ = PhysicalDevice(alias='a', name='n', guid='g')
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(alias='a2', name='n2', guid='g')


def test_physical_device_13():
    _ = PhysicalDevice(alias='a', name='n', guid='g')
    _ = PhysicalDevice(alias='a2', name='n')
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(alias='a2', guid='g')


def test_physical_device_14():
    _ = PhysicalDevice(alias='a', name='n', guid='g')
    _ = PhysicalDevice(alias='a2', name='n', guid='g2')
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(name='n')


def test_physical_device_15():
    device_1 = PhysicalDevice(alias='a', name='n', guid='g')
    device_2 = PhysicalDevice(alias='a2', name='n', guid='g2')
    device = PhysicalDevice(name='n', guid='g')
    assert device is device_1
    device = PhysicalDevice(name='n', guid='g2')
    assert device is device_2


def test_physical_device_16():
    """NODE must be either an InputNode, or the id of one"""
    with pytest.raises(DeviceError):
        _ = PhysicalDevice()


def test_physical_device_17():
    """NODE must be either an InputNode, or the id of one"""
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(node='xxx')


def test_physical_device_18():
    """NODE must be either an InputNode, or the id of one"""
    with pytest.raises(NodeError):
        _ = PhysicalDevice(node=0)


def test_physical_device_19():
    """NODE must be either an InputNode, or the id of one"""
    with pytest.raises(DeviceError):
        _ = PhysicalDevice(node=OutputNode())
