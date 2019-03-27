"""Controls are the models representing the axes, buttons and hats managed by njoy.

They also are building blocks that are assembled together according to the nJoy Design, to produce the final controls
of the Virtual Devices.

-- 'dev' and 'ctrl' parameters --

If neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created.

If 'dev' is specified without a 'ctrl' id, a new control instance is created and registered to the corresponding
device, and the control id is automatically assigned. 'dev' must be either an existing device instance, or an alias
to one.

Each device can only hold a maximum of 8 axis, 128 buttons and 4 hats.

If both 'dev' and 'ctrl' are specified, the corresponding control will be looked up in the given device.

Special case : if 'dev' is a physical device and the provided control doesn't exist, it will instead be created
with the given id.

Specifying only 'ctrl' doesn't make sense, and will raise an error (we wouldn't know where to look for it).

-- 'processor' and 'inputs' parameters --

The 'processor' and 'inputs' can be left out for controls attached to a physical device ("physical controls").
The control state is then set by the core, according to the corresponding input buffer.

If 'processor' is provided, is must be a callable taking the controls provided in 'inputs' as parameters.
The control state is then set to the return value of 'processor'.
"""
import enum

from .device import AbstractDevice, PhysicalDevice


class ControlError(Exception):
    pass


class AutoRegisteringControl(type):
    __CONTROL_GROUP_ATTRIBUTE__ = NotImplemented
    __MAX_PER_DEVICE__ = NotImplemented

    def __call__(cls, *args, dev=None, ctrl=None, **kwargs):
        if isinstance(dev, str):
            device_instance = PhysicalDevice(alias=dev)
        elif issubclass(dev.__class__, AbstractDevice):
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
            ctrl_group = getattr(device_instance, cls.__CONTROL_GROUP_ATTRIBUTE__)
            if ctrl in ctrl_group:
                return ctrl_group[ctrl]
            elif isinstance(device_instance, PhysicalDevice):
                # No control with this id in the device, but it's a PhysicalDevice so we'll create it right away
                if ctrl < cls.__MAX_PER_DEVICE__:
                    control = super().__call__(*args, dev=device_instance, ctrl=ctrl, **kwargs)
                    ctrl_group[ctrl] = control
                    return control
                else:
                    raise ControlError("Max number of {} in {} is {}".format(cls.__CONTROL_GROUP_ATTRIBUTE__,
                                                                             device_instance,
                                                                             cls.__MAX_PER_DEVICE__))
            else:
                raise ControlError("No {} with id {} in {}".format(cls.__name__, ctrl, device_instance))

        # No control id provided : we're creating a new instance in the given device and registering it
        ctrl_group = getattr(device_instance, cls.__CONTROL_GROUP_ATTRIBUTE__)
        ctrl_id = len(ctrl_group)
        if ctrl_id >= cls.__MAX_PER_DEVICE__:
            raise ControlError("Reached max number of {} in {} (max {})".format(cls.__CONTROL_GROUP_ATTRIBUTE__,
                                                                                device_instance,
                                                                                cls.__MAX_PER_DEVICE__))
        control = super().__call__(*args, dev=device_instance, ctrl=ctrl_id, **kwargs)
        ctrl_group[ctrl_id] = control
        return control


class AbstractControl(metaclass=AutoRegisteringControl):
    __CONTROL_GROUP_ATTRIBUTE__ = NotImplemented

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
                                                          self.__CONTROL_GROUP_ATTRIBUTE__,
                                                          self.id)
        else:
            return '<Unassigned {}>'.format(self.__class__.__name__)

    def __hash__(self):
        if self.is_assigned:
            return hash((self.__class__.__name__, self.dev.node.id, self.dev.id, self.id))
        else:
            return NotImplemented

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
    __CONTROL_GROUP_ATTRIBUTE__ = 'axes'
    __MAX_PER_DEVICE__ = 8


class Button(AbstractControl):
    __CONTROL_GROUP_ATTRIBUTE__ = 'buttons'
    __MAX_PER_DEVICE__ = 128


class Hat(AbstractControl):
    __CONTROL_GROUP_ATTRIBUTE__ = 'hats'
    __MAX_PER_DEVICE__ = 4
