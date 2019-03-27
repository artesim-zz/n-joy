import collections

from .node import InputNode, OutputNode


class DeviceError(Exception):
    pass


class AutoRegisteringDevice(type):
    __NODE_CLASS__ = OutputNode

    def __call__(cls, *args, node=None, dev=None, enforce_node=True, **kwargs):
        if isinstance(node, int):
            node_instance = cls.__NODE_CLASS__(node_id=node)
        elif isinstance(node, cls.__NODE_CLASS__):
            node_instance = node
        elif enforce_node:
            raise DeviceError("NODE must be either an {}, or the id of one".format(cls.__NODE_CLASS__.__name__))
        else:
            node_instance = None

        if dev is not None:
            # device id is provided : looking up an existing instance in the given node
            if dev < len(node_instance):
                return node_instance[dev]
            else:
                raise DeviceError("No existing {} with id {} in {}".format(cls.__name__, dev, node_instance))

        # No device id provided : we're creating a new instance in the given node
        device = super().__call__(*args, node=node_instance, dev=dev, **kwargs)

        # And register it to the node, if we have one
        if node_instance is not None:
            node_instance.append(device)

        return device


class AbstractDevice:
    def __init__(self, *, node=None, dev=None):
        self.node = node
        self.id = dev
        self.axes = dict()
        self.buttons = dict()
        self.hats = dict()

    def __repr__(self):
        if self.is_assigned:
            return '<{} /{:02d}/{:02d}>'.format(self.__class__.__name__,
                                                self.node.id,
                                                self.id)
        else:
            return '<Unassigned {}>'.format(self.__class__.__name__)

    @property
    def is_assigned(self):
        return self.node is not None and self.id is not None


class VirtualDevice(AbstractDevice, metaclass=AutoRegisteringDevice):
    """Represents a physical device, on a physical input node.

    The node is required and must be an existing instance of OutputNode.

    It is automatically registered to the given node and receives an id from it

    No more than 16 devices per node are allowed :

    Later on at run time, we'll receive messages referencing a node_id/device_id, and we'll use that to find the
    right instance.
    """


class AutoRegisteringPhysicalDevice(AutoRegisteringDevice):
    __NODE_CLASS__ = InputNode
    __DEVICES__ = dict()
    __NAME_INDEX__ = collections.defaultdict(list)  # Allow for several devices with the same name (but distinct GUID)
    __GUID_INDEX__ = dict()
    __MAX_DEVICES__ = 256

    def __call__(cls, *args, node=None, dev=None, alias=None, name=None, guid=None, **kwargs):
        if alias is not None:
            # The alias is provided : could be for lookup or creation...

            # Option 1 : Only the alias is provided : we're looking for that particular instance, return it
            if name is None and guid is None:
                if alias not in cls.__DEVICES__:
                    raise DeviceError("No existing device with alias {}".format(alias))
                return cls.__DEVICES__[alias]

            # Option 2 : An existing alias is provided, with a name or GUID : we're updating the existing device
            if alias in cls.__DEVICES__:
                device = cls.__DEVICES__[alias]
                if name is not None:
                    if device.name is not None:
                        raise DeviceError("Cannot change the name of an existing device, only add it.")
                    device.name = name
                    cls.__NAME_INDEX__[name].append(device)
                if guid is not None:
                    if guid in cls.__GUID_INDEX__:
                        raise DeviceError("Already have a device with GUID {}".format(guid))
                    if device.guid is not None:
                        raise DeviceError("Cannot change the GUID of an existing device, only add it.")
                    device.guid = guid
                    cls.__GUID_INDEX__[guid] = device
                return device

            # Option 3 : A new alias is provided with a name, GUID or both : we're creating an instance with that alias
            if len(cls.__DEVICES__) == cls.__MAX_DEVICES__:
                raise DeviceError("Reached maximum number of {} (max {})".format(cls.__name__, cls.__MAX_DEVICES__))

            # Ensure the GUID is really unique to us
            if guid is not None and guid in cls.__GUID_INDEX__:
                raise DeviceError("Already have a device with GUID {}".format(guid))

            # Now we can safely create the new instance
            device = super().__call__(*args,
                                      node=node, dev=dev, alias=alias, name=name, guid=guid, enforce_node=False,
                                      **kwargs)
            cls.__DEVICES__[alias] = device

            # Add it to the name and guid indexes
            if name is not None:
                cls.__NAME_INDEX__[name].append(device)
            if guid is not None:
                cls.__GUID_INDEX__[guid] = device

            # Finally, return the new instance
            return device

        # No alias were provided : search by GUID if provided (fastest)
        elif guid is not None:
            if guid not in cls.__GUID_INDEX__:
                raise DeviceError("No existing device with GUID {}".format(guid))
            return cls.__GUID_INDEX__[guid]

        # Or try searching by name, but must be unambiguous
        elif name is not None:
            if len(cls.__NAME_INDEX__[name]) == 0:
                raise DeviceError("No existing device with name {}".format(name))
            elif len(cls.__NAME_INDEX__[name]) > 1:
                raise DeviceError("Ambiguous lookup : several devices with name {}".format(name))
            else:
                return cls.__NAME_INDEX__[name]

        # If everything fails, try the super-metaclass (searching by node_id/dev_id)
        else:
            return super().__call__(*args, node=node, dev=dev, **kwargs)


class PhysicalDevice(AbstractDevice, metaclass=AutoRegisteringPhysicalDevice):
    """Represents a physical device in a physical input node.

    Unlike VirtualDevices, a PhysicalDevice doesn't strictly require a node if it is created while parsing a design.
    But in this case it still requires an alias, and either a name or a GUID (or both).

    When parsing the controls, the PhysicalDevices will typically be retrieved by alias.

    At this stage the PhysicalDevices are still considered unassigned.

    During the handshake phase, the PhysicalDevices are assigned to the newly registered nodes, and will be retrieved
    by GUID or by name.

    Finally at run time, we'll receive messages referencing a node/device and we'll use that to find the right instance.

    When no alias, name or GUID is provided, a node is required and must be an existing instance of InputNode :

    It is automatically registered to the given node and receives an id from it

    No more than 16 devices per node are allowed :

    Later on at run time, we'll receive messages referencing a node_id/device_id, and we'll use that to find the
    right instance.
    """
    def __init__(self, *, node=None, dev=None, alias=None, name=None, guid=None):
        super().__init__(node=node, dev=dev)
        self.alias = alias
        self.name = name
        self.guid = guid
