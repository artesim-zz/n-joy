"""Controls are the models representing the axes, buttons and hats managed by njoy.

They also are building blocks that are assembled together according to an nJoy Design, to produce the final controls
of the Virtual Devices.

If neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created.

If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the control
id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.

If 'ctrl_id' is also specified, the device will try to register the new control with this id (if available).

Providing 'ctrl_id' without 'dev' doesn't make sense : the behavior is unspecified, but it will probably result in an
unassigned control, completely ignoring 'ctrl_id'.

The 'processor' and 'inputs' can be left out for controls registered to a physical device ("physical controls").
The control state is set by the Core (actually, the Actuator), when the corresponding input buffer has changed.

If 'processor' is provided, is must be a callable taking the controls provided in 'inputs' as parameters.
The control state is then set to the return value of 'processor'.
"""

from .devices import AbstractDevice, PhysicalDevice


class ControlError(Exception):
    pass


class ControlInvalidDeviceError(ControlError):
    def __init__(self):
        self.message = "dev must be a Device instance, or an alias of one"


class AutoRegisteringControl(type):
    __REGISTER_METHOD__ = NotImplemented

    def __call__(cls, *args, dev=None, ctrl_id=None, **kwargs):
        # First create the control
        control = super().__call__(*args, **kwargs)

        # Then, if a device instance was provided, register it
        device_instance = cls._find_device(dev)
        if device_instance is not None:
            register_method = getattr(device_instance, cls.__REGISTER_METHOD__)
            if ctrl_id is None:
                register_method(control)
            else:
                register_method(control, ctrl_id=ctrl_id)

        return control

    @staticmethod
    def _find_device(dev):
        if isinstance(dev, str):
            return PhysicalDevice.find(alias=dev)
        elif issubclass(dev.__class__, AbstractDevice):
            return dev
        elif dev is not None:
            raise ControlInvalidDeviceError()
        else:
            return None


class AbstractControl(metaclass=AutoRegisteringControl):
    __REGISTER_METHOD__ = NotImplemented

    def __init__(self, *, processor=None, inputs=None, **_kwargs):
        self.dev = None  # Automatically set by the device it is assigned to
        self.id = None  # Automatically set by the device it is assigned to
        self.processor = processor
        self._input_controls = inputs or list()

    def __repr__(self):
        if self.is_assigned:
            return '<{} /{:02d}/{:02d}/{}/{:02d}>'.format(self.__class__.__name__,
                                                          self.dev.node.id,
                                                          self.dev.id,
                                                          self.__class__.__name__.lower(),
                                                          self.id)
        else:
            return '<Unassigned {}>'.format(self.__class__.__name__)

    def __hash__(self):
        if self.dev is None:
            return hash((self.__class__.__name__,
                         hash(self._input_controls),
                         id(self.processor),
                         self.id))
        elif self.dev.node is None:
            return hash((self.__class__.__name__,
                         hash(self._input_controls),
                         id(self.processor),
                         self.dev.id,
                         self.id))
        else:
            return hash((self.__class__.__name__,
                         self.dev.node.id,
                         self.dev.id,
                         self.id))

    @property
    def is_assigned(self):
        return self.dev is not None and self.dev.is_assigned and self.id is not None

    @property
    def is_physical_control(self):
        return self.dev is not None and isinstance(self.dev, PhysicalDevice)

    @property
    def physical_inputs(self):
        inputs = set()
        for control in self._input_controls:
            if control.is_physical_control:
                inputs.add(control)
            else:
                inputs.update(control.physical_inputs)
        return inputs

    @property
    def state(self):
        return self.processor(*self._input_controls)


class Axis(AbstractControl):
    __REGISTER_METHOD__ = 'register_axis'


class Button(AbstractControl):
    __REGISTER_METHOD__ = 'register_button'


class Hat(AbstractControl):
    __REGISTER_METHOD__ = 'register_hat'
