import pytest

from njoy_core.core.model.node import NodeError
from njoy_core.core.model.device import InputNode, OutputNode


def test_instantiation_1():
    a = InputNode()
    assert a.id == 0
    a = InputNode()
    assert a.id == 1


def test_instantiation_2():
    """Ensures no more than the maximum number of active InputNode is registered."""
    for _ in range(16):
        _ = InputNode()
    with pytest.raises(NodeError):
        _ = InputNode()


def test_instantiation_3():
    """The limit is per-subclass, so even if we reached the max number of InputNode here,
     we can still add an OutputNode"""
    for _ in range(16):
        _ = InputNode()
    a = OutputNode()
    assert a.id == 0


def test_lookup():
    """Later on at run time, we'll receive messages referencing a node id, and we'll use that to find the instance."""
    a = InputNode()
    b = InputNode()
    c = InputNode()
    msg_node = InputNode(node_id=1)
    assert msg_node is b
