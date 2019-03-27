from njoy_core.core.model.node import InputNode, OutputNode
from njoy_core.core.model.device import PhysicalDevice, VirtualDevice
from njoy_core.core.model.control import ControlError, Axis, Button, Hat

import pytest


# -- 'dev' and 'ctrl' parameters --

def test_axis_instantiation_1():
    """If neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created."""
    axis = Axis()
    assert axis.is_assigned is False


def test_axis_instantiation_2():
    """If 'dev' is specified without a 'ctrl' id, a new control instance is created and registered to the corresponding
    device, and the control id is automatically assigned.
    'dev' must be either an existing device instance, or an alias to one.
    """
    dev = VirtualDevice(node=OutputNode())
    axis = Axis(dev=dev)
    assert axis.is_assigned is True
    assert axis.id == 0


def test_axis_instantiation_3():
    """If 'dev' is specified without a 'ctrl' id, a new control instance is created and registered to the corresponding
    device, and the control id is automatically assigned.
    'dev' must be either an existing device instance, or an alias to one.
    """
    PhysicalDevice(alias='dev', name='dev', node=InputNode())
    axis = Axis(dev='dev')
    assert axis.is_assigned is True
    assert axis.id == 0


def test_axis_instantiation_4():
    """Each device can only hold a maximum of 8 axis, 128 buttons and 4 hats."""
    dev = VirtualDevice(node=OutputNode())
    for _ in range(8):
        Axis(dev=dev)
    with pytest.raises(ControlError):
        Axis(dev=dev)


def test_axis_instantiation_5():
    """Each device can only hold a maximum of 8 axis, 128 buttons and 4 hats."""
    dev = VirtualDevice(node=OutputNode())
    for _ in range(128):
        Button(dev=dev)
    with pytest.raises(ControlError):
        Button(dev=dev)


def test_axis_instantiation_6():
    """Each device can only hold a maximum of 8 axis, 128 buttons and 4 hats."""
    dev = VirtualDevice(node=OutputNode())
    for _ in range(4):
        Hat(dev=dev)
    with pytest.raises(ControlError):
        Hat(dev=dev)


def test_axis_lookup():
    """If both 'dev' and 'ctrl' are specified, the corresponding control will be looked up in the given device."""
    dev = VirtualDevice(node=OutputNode())
    axis = Axis(dev=dev)
    control = Axis(dev=dev, ctrl=0)
    assert control is axis


def test_axis_lookup_instantiation():
    """Special case : if 'dev' is a physical device and the provided control doesn't exist, it will be created with the
       given id."""
    dev = PhysicalDevice(node=InputNode())
    axis = Axis(dev=dev, ctrl=3)
    assert axis.id == 3


def test_axis_lookup_instantiation_2():
    """Special case : if 'dev' is a physical device and the provided control doesn't exist, it will be created with the
       given id."""
    dev = PhysicalDevice(node=InputNode())
    with pytest.raises(ControlError):
        Axis(dev=dev, ctrl=8)


def test_axis_lookup_2():
    """Specifying only 'ctrl' doesn't make sense, and will raise an error."""
    with pytest.raises(ControlError):
        Axis(ctrl=2)
