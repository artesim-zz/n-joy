import enum

import njoy_core.core.model.device


class ControlError(Exception):
    pass


class AutoRegisteringControl(type):
    __CONTROL_GROUP__ = NotImplemented
    __MAX_PER_DEVICE__ = NotImplemented

    def __call__(cls, *args, dev=None, ctrl=None, **kwargs):
        if isinstance(dev, str):
            device_instance = njoy_core.core.model.device.PhysicalDevice(alias=dev)
        elif issubclass(dev.__class__, njoy_core.core.model.device.AbstractDevice):
            device_instance = dev
        elif dev is not None:
            raise ControlError("dev must be a Device instance, or an alias of one")
        elif ctrl is not None:
            raise ControlError("Provided control id {} without a device : don't know where to look !".format(ctrl))
        else:
            # No device provided, just instantiate as an unassigned control and return that
            return super().__call__(*args, dev=None, ctrl=None, **kwargs)

        # At this point, we do have a device instance
        if ctrl is not None:
            # control id is also provided : looking up an existing instance in the given device
            ctrl_grp_list = getattr(device_instance, cls.__CONTROL_GROUP__)
            if ctrl < len(ctrl_grp_list):
                return ctrl_grp_list[ctrl]
            else:
                raise ControlError("No {} with id {} in {}".format(cls.__name__, ctrl, device_instance))

        # No control id provided : we're creating a new instance in the given device and registering it
        ctrl_grp_list = getattr(device_instance, cls.__CONTROL_GROUP__)
        ctrl_id = len(ctrl_grp_list)
        if ctrl_id >= cls.__MAX_PER_DEVICE__:
            raise ControlError("Reached max number of {} in {} (max {})".format(cls.__CONTROL_GROUP__,
                                                                                device_instance,
                                                                                cls.__MAX_PER_DEVICE__))
        control = super().__call__(*args, dev=device_instance, ctrl=ctrl_id, **kwargs)
        ctrl_grp_list.append(control)
        return control


class AbstractControl(metaclass=AutoRegisteringControl):
    """Represents either an axis, a button or a hat.

    -- 'dev' and 'ctrl' parameters --

    If neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created.
    >>> a1 = Axis()
    >>> a1.is_assigned
    False

    If 'dev' is specified without a 'ctrl' id, a new control instance is created and registered to the corresponding
    device, and the control id is automatically assigned.
    'dev' must be either an existing device instance, or an alias to one.
    >>> n1 = njoy_core.core.model.node.OutputNode()
    >>> d1 = njoy_core.core.model.device.VirtualDevice(node=n1)
    >>> a2 = Axis(dev=d1)
    >>> a2.is_assigned
    True
    >>> a2.id
    0

    Each device can only hold a maximum of 8 axis, 128 buttons and 4 hats.

    >>> d2 = njoy_core.core.model.device.VirtualDevice(node=n1)
    >>> for _ in range(8):
    ...     a = Axis(dev=d2)
    >>> a = Axis(dev=d2)
    Traceback (most recent call last):
      ...
    control.ControlError: Reached max number of axes in <VirtualDevice /00/01> (max 8)

    >>> for _ in range(128):
    ...     b = Button(dev=d2)
    >>> b = Button(dev=d2)
    Traceback (most recent call last):
      ...
    control.ControlError: Reached max number of buttons in <VirtualDevice /00/01> (max 128)

    >>> for _ in range(4):
    ...     h = Hat(dev=d2)
    >>> h = Hat(dev=d2)
    Traceback (most recent call last):
      ...
    control.ControlError: Reached max number of hats in <VirtualDevice /00/01> (max 4)

    If both 'dev' and 'ctrl' are specified, the corresponding control will be looked up in the given device.

    >>> control = Axis(dev=d1, ctrl=0)
    >>> control is a2
    True

    Specifying only 'ctrl' doesn't make sense, and is forbidden.

    >>> control = Axis(ctrl=0)
    Traceback (most recent call last):
      ...
    control.ControlError: Provided control id 0 without a device : don't know where to look !

    -- 'processor' and 'inputs' parameters --

    The 'processor' and 'inputs' can be left out for controls attached to a physical device ("physical controls").
    The control state is set by the core, according to the corresponding input buffer.

    If 'processor' is provided, is must be a callable taking the provided 'inputs' controls as parameters.
    The control state is set to the return value of 'processor'.
    """
    __CONTROL_GROUP__ = NotImplemented

    def __init__(self, *, dev=None, ctrl=None, processor=None, inputs=None):
        self.dev = dev
        self.id = ctrl
        self._processor = processor
        self._inputs = inputs
        self._state = None

    def __repr__(self):
        if self.is_assigned:
            return '<{} /{:02d}/{:02d}/{}/{:02d}>'.format(self.__class__.__name__,
                                                          self.dev.node.id,
                                                          self.dev.id,
                                                          self.__CONTROL_GROUP__,
                                                          self.id)
        else:
            return '<Unassigned {}>'.format(self.__class__.__name__)

    @property
    def is_assigned(self):
        return self.dev is not None and self.dev.is_assigned and self.id is not None

    @property
    def state(self):
        if self._processor is not None and self._inputs is not None:
            return self._processor(*self._inputs)
        else:
            return self._state

    @state.setter
    def state(self, value):
        self._state = value


@enum.unique
class HatState(enum.IntFlag):
    HAT_CENTER = 0
    HAT_UP = 1
    HAT_RIGHT = 2
    HAT_DOWN = 4
    HAT_LEFT = 8
    HAT_UP_RIGHT = HAT_UP | HAT_RIGHT
    HAT_UP_LEFT = HAT_UP | HAT_LEFT
    HAT_DOWN_RIGHT = HAT_DOWN | HAT_RIGHT
    HAT_DOWN_LEFT = HAT_DOWN | HAT_LEFT

    @classmethod
    def list(cls):
        return [v for v in cls]

    @classmethod
    def set(cls):
        return {v for v in cls}


class Axis(AbstractControl):
    __CONTROL_GROUP__ = 'axes'
    __MAX_PER_DEVICE__ = 8


class Button(AbstractControl):
    __CONTROL_GROUP__ = 'buttons'
    __MAX_PER_DEVICE__ = 128


class Hat(AbstractControl):
    __CONTROL_GROUP__ = 'hats'
    __MAX_PER_DEVICE__ = 4
