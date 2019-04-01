"""AbstractNode should not be instantiated directly, use InputNode or OutputNode instead.

Represents a registered input or output node.

Automatically assigns itself an id, to be given back to the node during the Handshake phase.

Ensures no more than the maximum number of active InputNode is registered.

The limit is per-subclass, so even if we reached the max number of InputNode here, we can still add an OutputNode.

Later on at run time, we'll receive messages referencing a node id, and we'll use that to find the instance.

A node is a container for up to 16 devices.

"""
import abc
import collections


class NodeError(Exception):
    pass


class NodeOverflowError(NodeError):
    def __init__(self, node_class):
        self.message = "Reached max number of {} (max {})".format(node_class.__name__, node_class.__MAX_NODES__)


class NodeDeviceOverflowError(NodeError):
    def __init__(self, node):
        self.message = "Reached max number of devices for {} (max {})".format(node.__class__.__name__,
                                                                              node.__MAX_DEVICES__)


class NodeNotFoundError(NodeError):
    def __init__(self, node_class, node_id):
        self.message = "No existing {} with id {}".format(node_class.__name__, node_id)


class AutoIndexingNode(abc.ABCMeta):
    __NODES__ = collections.defaultdict(list)
    __MAX_NODES__ = NotImplemented

    def __call__(cls, *args, **kwargs):
        node_id = len(cls.__NODES__[cls])
        if node_id == cls.__MAX_NODES__:
            raise NodeOverflowError(cls)
        node = super().__call__(*args, **kwargs)
        node.id = node_id
        cls.__NODES__[cls].append(node)
        return node


class AbstractNode(collections.MutableSequence, metaclass=AutoIndexingNode):
    __MAX_DEVICES__ = 16

    @classmethod
    def find(cls, *, node_id):
        if node_id < len(cls.__NODES__[cls]):
            return cls.__NODES__[cls][node_id]
        else:
            raise NodeNotFoundError(cls, node_id)

    def __init__(self):
        self._devices = list()
        self.id = None  # Automatically set by the metaclass when instantiated

    def __repr__(self):
        return '<{} {:02d}>'.format(self.__class__.__name__, getattr(self, 'id'))

    def __getitem__(self, item):
        return self._devices.__getitem__(item)

    def __setitem__(self, key, value):
        self._devices.__setitem__(key, value)

    def __delitem__(self, key):
        self._devices.__delitem__(key)

    def __len__(self):
        return len(self._devices)

    def insert(self, index, device):
        device_id = len(self._devices)
        if device_id == self.__MAX_DEVICES__:
            raise NodeDeviceOverflowError(self)
        setattr(device, 'node', self)
        setattr(device, 'id', device_id)
        self._devices.insert(index, device)


class InputNode(AbstractNode):
    __MAX_NODES__ = 16


class OutputNode(AbstractNode):
    __MAX_NODES__ = 16
