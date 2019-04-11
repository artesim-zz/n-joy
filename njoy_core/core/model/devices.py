import collections

from .nodes import InputNode, OutputNode, NodeNotFoundError


class DeviceError(Exception):
    pass


class DeviceInvalidNodeError(DeviceError):
    def __init__(self, device_class):
        self.message = "The provided Node must be either an {}, " \
                       "or the id of one".format(device_class.__NODE_CLASS__.__name__)


class DeviceNotFoundError(DeviceError):
    def __init__(self, device_class, dev, node):
        self.message = "No existing {} with id {} in {}".format(device_class.__name__, dev, node)


class DeviceInvalidParamsError(DeviceError):
    def __init__(self):
        self.message = "Invalid params : must provided an alias, and either a guid or a name (or both)."


class DeviceAliasNotFoundError(DeviceError):
    def __init__(self, device_class, alias):
        self.message = "No existing {} with alias {}".format(device_class.__name__, alias)


class DeviceGuidNotFoundError(DeviceError):
    def __init__(self, device_class, guid):
        self.message = "No existing {} with GUID {}".format(device_class.__name__, guid)


class DeviceNameNotFoundError(DeviceError):
    def __init__(self, device_class, name):
        self.message = "No existing {} with name {}".format(device_class.__name__, name)


class DeviceAmbiguousNameError(DeviceError):
    def __init__(self, device_class, name):
        self.message = "Found several {} with name {}, please also provide a GUID".format(device_class.__name__, name)


class DeviceInvalidLookupError(DeviceError):
    def __init__(self):
        self.message = "Invalid lookup : must provided either a (node, dev) couple, an alias, a guid or a name."


class DeviceDuplicateAliasError(DeviceError):
    def __init__(self, device_class, alias):
        self.message = "We already have a {} with the alias {}".format(device_class.__name__, alias)


class DeviceDuplicateGuidError(DeviceError):
    def __init__(self, device_class, guid):
        self.message = "We already have a {} with the GUID {}".format(device_class.__name__, guid)


class DeviceOverflowError(DeviceError):
    def __init__(self, control, device, limit):
        self.message = "Reached max number of {} for {} (max {})".format(control.__class__.__name__, device, limit)


class DeviceRegisterControlError(DeviceError):
    def __init__(self, control, ctrl_id, device):
        self.message = "Couldn't register the {} with id {}, {} already has one.".format(control.__class__.__name__,
                                                                                         ctrl_id,
                                                                                         device)


class AutoRegisteringDevice(type):
    __NODE_CLASS__ = NotImplemented

    def __call__(cls, *args, node=None, enforce_node=True, **kwargs):
        node_instance = cls._find_node(node, enforce_node)

        # Create a new instance in the given node
        device = super().__call__(*args, **kwargs)

        # And register it to the node, if we have one
        if node_instance is not None:
            node_instance.append(device)

        return device

    def _find_node(cls, node, raise_error=False):
        if isinstance(node, int):
            try:
                return cls.__NODE_CLASS__.find(node_id=node)
            except NodeNotFoundError:
                raise DeviceInvalidNodeError(cls)
        elif isinstance(node, cls.__NODE_CLASS__):
            return node
        elif raise_error:
            raise DeviceInvalidNodeError(cls)
        else:
            return None

    def _find_device_by_id(cls, *, node, dev):
        node_instance = cls._find_node(node, raise_error=True)
        if dev < len(node_instance):
            return node_instance[dev]
        else:
            raise DeviceNotFoundError(cls, dev, node_instance)

    def find(cls, *, node, dev):
        return cls._find_device_by_id(node=node, dev=dev)


class AbstractDevice:
    __MAX_NB_AXIS__ = 8
    __MAX_NB_BUTTONS__ = 128
    __MAX_NB_HATS__ = 4

    def __init__(self, *args, **kwargs):
        self.node = None  # Automatically set by the node it is assigned to
        self.id = None  # Automatically set by the node it is assigned to
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

    def __hash__(self):
        return hash((self.node.id if self.node is not None else None, self.id))

    @property
    def is_assigned(self):
        return self.node is not None and self.id is not None

    def register_axis(self, axis, *, ctrl_id=None):
        if ctrl_id is not None and ctrl_id in self.axes:
            raise DeviceRegisterControlError(axis, ctrl_id, self)
        if len(self.axes) == self.__MAX_NB_AXIS__:
            raise DeviceOverflowError(axis, self, self.__MAX_NB_AXIS__)
        setattr(axis, 'dev', self)
        setattr(axis, 'id', ctrl_id or len(self.axes))
        self.axes[axis.id] = axis

    def register_button(self, button, *, ctrl_id=None):
        if ctrl_id is not None and ctrl_id in self.buttons:
            raise DeviceRegisterControlError(button, ctrl_id, self)
        if len(self.buttons) == self.__MAX_NB_BUTTONS__:
            raise DeviceOverflowError(button, self, self.__MAX_NB_BUTTONS__)
        setattr(button, 'dev', self)
        setattr(button, 'id', ctrl_id or len(self.buttons))
        self.buttons[button.id] = button

    def register_hat(self, hat, *, ctrl_id=None):
        if ctrl_id is not None and ctrl_id in self.hats:
            raise DeviceRegisterControlError(hat, ctrl_id, self)
        if len(self.hats) == self.__MAX_NB_HATS__:
            raise DeviceOverflowError(hat, self, self.__MAX_NB_HATS__)
        setattr(hat, 'dev', self)
        setattr(hat, 'id', ctrl_id or len(self.hats))
        self.hats[hat.id] = hat


class VirtualDevice(AbstractDevice, metaclass=AutoRegisteringDevice):
    """Represents a virtual device, on a virtual input node.

    The node parameter is required and must be an existing instance of an OutputNode, or an id of one.

    The new VirtualDevice is automatically registered to the given VirtualNode and receives an id from it

    Later on at run time, we'll receive messages referencing a node_id/device_id, and we'll use that to find the
    right instance.

    A VirtualDevice is a container for up to 8 Axis, 128 Button and 4 Hat instances.
    """
    __NODE_CLASS__ = OutputNode


class AutoRegisteringPhysicalDevice(AutoRegisteringDevice):
    def __call__(cls, *args, alias=None, guid=None, name=None, **kwargs):
        if alias is None or (guid is None and name is None):
            raise DeviceInvalidParamsError()
        return super().__call__(*args, node=None, enforce_node=False, alias=alias, guid=guid, name=name)


class PhysicalDevice(AbstractDevice, metaclass=AutoRegisteringPhysicalDevice):
    """Represents a physical device in a physical input node.

    A PhysicalDevice is created while parsing a design and requires an alias and either a name or a GUID (or both),
    instead of a node.
    The alias and the GUID must be unique.
    The name may not be unique, but must be disambiguated by a GUID (existing instances also checked).
    The PhysicalDevice is then considered unassigned until it is registered to a node during the handshake phase.

    When parsing the controls, the PhysicalDevices will typically be retrieved by alias.
    During the handshake phase, the PhysicalDevices will be retrieved by GUID or by name.
    Finally at run time, the PhysicalDevices will be retrieved node_id/device_id from the event messages.

    A PhysicalDevice is a container for up to 8 Axis, 128 Button and 4 Hat instances.
    """
    __NODE_CLASS__ = InputNode
    __ALIAS_INDEX__ = dict()
    __NAME_INDEX__ = collections.defaultdict(list)  # Allow for several devices with the same name (but distinct GUID)
    __GUID_INDEX__ = dict()

    def __init__(self, *args, alias=None, guid=None, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias = alias
        self.guid = guid
        self.name = name

    def __setattr__(self, key, value):
        if key == 'alias' and value is not None:
            if value in self.__ALIAS_INDEX__:
                raise DeviceDuplicateAliasError(self.__class__, value)
            self.__ALIAS_INDEX__[value] = self

        elif key == 'guid' and value is not None:
            if value in self.__GUID_INDEX__:
                raise DeviceDuplicateGuidError(self.__class__, value)
            self.__GUID_INDEX__[value] = self

        elif key == 'name' and value is not None:
            if len(self.__NAME_INDEX__[value]) > 0 and \
                    (self.guid is None or any([d.guid is None for d in self.__NAME_INDEX__[value]])):
                raise DeviceAmbiguousNameError(self.__class__, value)
            self.__NAME_INDEX__[value].append(self)

        super().__setattr__(key, value)

    def __hash__(self):
        return hash((self.node.id if self.node is not None else None,
                     self.id,
                     self.alias,
                     self.name,
                     self.guid))

    @classmethod
    def find(cls, *, node=None, dev=None, alias=None, guid=None, name=None):
        if node is not None and dev is not None:
            return cls._find_device_by_id(node=node, dev=dev)

        if alias is not None:
            if alias in cls.__ALIAS_INDEX__:
                return cls.__ALIAS_INDEX__[alias]
            elif guid is None and name is None:
                raise DeviceAliasNotFoundError(cls, alias)

        if guid is not None:
            if guid in cls.__GUID_INDEX__:
                return cls.__GUID_INDEX__[guid]
            elif name is None:
                raise DeviceGuidNotFoundError(cls, guid)

        if name is not None:
            if name in cls.__NAME_INDEX__:
                devices = cls.__NAME_INDEX__[name]
                if len(devices) > 1:
                    raise DeviceAmbiguousNameError(cls, name)
                else:
                    device = devices[0]

                    # If we found it by (unique) name despite the fact that a guid was provided, this means we didn't
                    # know about that guid before hand : update the device before returning it
                    if guid is not None:
                        device.guid = guid

                    return device
            else:
                raise DeviceNameNotFoundError(cls, name)

        raise DeviceInvalidLookupError()
