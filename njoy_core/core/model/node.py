"""AbstractNode should not be instantiated directly, use InputNode or OutputNode instead.

Represents a registered input or output node.

Automatically assigns itself an id, to be given back to the node during the Handshake phase.

Ensures no more than the maximum number of active InputNode is registered.

The limit is per-subclass, so even if we reached the max number of InputNode here, we can still add an OutputNode.

Later on at run time, we'll receive messages referencing a node id, and we'll use that to find the instance.

"""
import abc
import collections


class NodeError(Exception):
    pass


class AutoIndexingNode(abc.ABCMeta):
    __NODES__ = collections.defaultdict(list)
    __MAX_NODES__ = NotImplemented

    def __call__(cls, *args, node_id=None, **kwargs):
        if node_id is None:
            node_id = len(cls.__NODES__[cls])
            if node_id == cls.__MAX_NODES__:
                raise NodeError("Reached maximum number of {} (max {})".format(cls.__name__, cls.__MAX_NODES__))
            node = super().__call__(*args, node_id=node_id, **kwargs)
            cls.__NODES__[cls].append(node)
            return node
        elif node_id < len(cls.__NODES__[cls]):
            return cls.__NODES__[cls][node_id]
        else:
            raise NodeError("No existing {} with id {}".format(cls.__name__, node_id))


class AbstractNode(collections.MutableSequence, metaclass=AutoIndexingNode):
    __MAX_DEVICES__ = 16

    def __init__(self, *, node_id=None):
        self.id = node_id
        self._devices = list()

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
            raise NodeError("Reached max number of devices in {} (max {})".format(self, self.__MAX_DEVICES__))
        setattr(device, 'node', self)
        setattr(device, 'id', device_id)
        self._devices.insert(index, device)


class InputNode(AbstractNode):
    __MAX_NODES__ = 16


class OutputNode(AbstractNode):
    __MAX_NODES__ = 16
