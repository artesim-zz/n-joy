import pytest

from njoy_core.core.model import NodeOverflowError, NodeDeviceOverflowError, NodeNotFoundError
from njoy_core.core.model import InputNode, OutputNode
from njoy_core.core.model import PhysicalDevice, VirtualDevice


@pytest.fixture(scope="module",
                params=[InputNode, OutputNode])
def node_cls(request):
    return request.param


@pytest.fixture(scope="module")
def node_cls_tuple(node_cls):
    if node_cls is InputNode:
        return InputNode, OutputNode
    elif node_cls is OutputNode:
        return OutputNode, InputNode


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_output_node_cache
class TestInstantiation:
    def test_case_1(self, node_cls):
        """Automatically assigns itself an id, to be given back to the node during the Handshake phase."""
        a = node_cls()
        assert a.id == 0
        a = node_cls()
        assert a.id == 1

    def test_case_2(self, node_cls):
        """Ensures no more than the maximum number of active InputNode is registered."""
        for _ in range(16):
            _ = node_cls()
        with pytest.raises(NodeOverflowError):
            _ = node_cls()

    def test_case_3(self, node_cls_tuple):
        """The limit is per-subclass, so even if we reached the max number of InputNode here,
        we can still add an OutputNode, and vice-versa"""
        for _ in range(16):
            _ = node_cls_tuple[0]()
        a = node_cls_tuple[1]()
        assert a.id == 0


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_output_node_cache
class TestLookup:
    def test_case_1(self, node_cls):
        """Later on at run time, we'll receive messages referencing a node id, and we'll use that to find the instance.
        """
        _ = node_cls()
        b = node_cls()
        _ = node_cls()
        msg_node = node_cls.find(node_id=1)
        assert msg_node is b

    def test_case_2(self, node_cls):
        with pytest.raises(NodeNotFoundError):
            node_cls.find(node_id=0)


@pytest.mark.ensure_clean_input_node_cache
@pytest.mark.ensure_clean_output_node_cache
class TestContainer:
    def test_case_1(self):
        """A node is a container for up to 16 devices."""
        node = InputNode()
        for i in range(16):
            node.append(PhysicalDevice(alias=str(i), name=str(i)))
        with pytest.raises(NodeDeviceOverflowError):
            node.append(PhysicalDevice(alias=16, name=16))

    def test_case_2(self):
        """A node is a container for up to 16 devices."""

        # VirtualDevices require a Node, so we have to test it the other way around
        node = OutputNode()
        for _ in range(16):
            VirtualDevice(node=node)
        with pytest.raises(NodeDeviceOverflowError):
            VirtualDevice(node=node)
