# pylint: skip-file
import pytest

from njoy_core.core.model import InputNode, OutputNode
from njoy_core.core.model import PhysicalDevice, VirtualDevice
from njoy_core.core.model import Axis, Button, Hat
from njoy_core.core.model import ControlEvent
from njoy_core.core.model import MessageIdentityError


@pytest.fixture(scope="module",
                params=[Axis, Button, Hat])
def unassigned_control(request):
    return request.param()


@pytest.fixture(scope="module",
                params=[Axis, Button, Hat])
def physical_control(request):
    node = InputNode()
    device = PhysicalDevice(node=node, alias='alias', name='name')
    return request.param(dev=device)


@pytest.fixture(scope="module",
                params=[Axis, Button, Hat])
def virtual_control(request):
    node = OutputNode()
    device = VirtualDevice(node=node)
    return request.param(dev=device)


class TestControlEvent:
    def test_case_1_mk_identity(self):
        with pytest.raises(MessageIdentityError):
            _ = ControlEvent.mk_identity('x')

    def test_case_2_mk_identity(self, unassigned_control):
        with pytest.raises(MessageIdentityError):
            _ = ControlEvent.mk_identity(unassigned_control)
