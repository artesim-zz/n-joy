"""Controls are the models representing the axes, buttons and hats managed by njoy.

They also are building blocks that are assembled together according to an nJoy Design, to produce the final controls
of the Virtual Devices.

They just *represent* a control, though, they do not store any state themselves.

Instead, they are used by the Core at design-parsing time, to build a set of recursive state processor functions (by
calling the 'mk_state_processor' on the top-level virtual controls). At runtime, the Actuators will call the
corresponding state processor to obtain a new state from the physical controls.

The controls are otherwise used throughout the whole application as a model, to identify and retrieve specific controls
of specific devices on any given node.

At instantiation, if neither 'dev' nor 'ctrl' is specified, a new unassigned control instance is created.

If 'dev' is specified, a new control instance is created and registered to the corresponding device, and the control
id is automatically assigned. 'dev' must be either an existing device instance, or an alias to one.

If 'ctrl_id' is also specified, the device will try to register the new control with this id (if available). If it
already exists but it's a Physical Control, then return it instead of raising an error.

Providing 'ctrl_id' without 'dev' doesn't make sense : the behavior is unspecified, but it will probably result in an
unassigned control, completely ignoring 'ctrl_id'.

If 'processor' is provided, is must be a callable taking states for the controls provided in 'inputs' as parameters.
The control state is then the return value of a call to 'processor' on 'inputs'.

The 'processor' and 'inputs' can be left out for controls registered to a physical device ("physical controls").
An anonymous lambda function will then be generated by the mk_state_processor function, which simply return the state
of the provided control.
"""

from .devices import AbstractDevice, PhysicalDevice


class ControlError(Exception):
    pass


class ControlInvalidDeviceError(ControlError):
    def __init__(self):
        super().__init__("dev must be a Device instance, or an alias of one")


class ControlProgrammingError(ControlError):
    pass


class AutoRegisteringControl(type):
    __REGISTER_METHOD__ = NotImplemented

    def __call__(cls, *args, dev=None, ctrl=None, **kwargs):
        # First create the control
        control = super().__call__(*args, **kwargs)

        # Then, if a device instance was provided, register it
        device_instance = cls._find_device(dev)
        if device_instance is not None:
            register_method = getattr(device_instance, cls.__REGISTER_METHOD__)
            if ctrl is None:
                control = register_method(control)
            else:
                control = register_method(control, ctrl=ctrl)

        return control

    @staticmethod
    def _find_device(dev):
        if isinstance(dev, str):
            return PhysicalDevice.find(alias=dev)
        if issubclass(dev.__class__, AbstractDevice):
            return dev
        if dev is not None:
            raise ControlInvalidDeviceError()
        return None


class AbstractControl(metaclass=AutoRegisteringControl):
    __REGISTER_METHOD__ = NotImplemented

    def __init__(self, *, processor=None, inputs=None, **_kwargs):
        self.dev = None  # Automatically set by the device it is assigned to
        self.id = None  # Automatically set by the device it is assigned to
        self.processor = processor
        self.input_controls = inputs

    def __repr__(self):
        if not self.is_assigned:
            return '<Unassigned {}>'.format(self.__class__.__name__)

        return '<{} /{:02d}/{:02d}/{}/{:02d}>'.format(self.__class__.__name__,
                                                      self.dev.node.id,
                                                      self.dev.id,
                                                      self.__class__.__name__.lower(),
                                                      self.id)

    def __hash__(self):
        if self.dev is None:
            return hash((self.__class__.__name__,
                         hash(self.input_controls),
                         id(self.processor),
                         self.id))

        if self.dev.node is None:
            return hash((self.__class__.__name__,
                         hash(self.input_controls),
                         id(self.processor),
                         self.dev.id,
                         self.id))

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


class Axis(AbstractControl):
    __REGISTER_METHOD__ = 'register_axis'


class Button(AbstractControl):
    __REGISTER_METHOD__ = 'register_button'


class Hat(AbstractControl):
    __REGISTER_METHOD__ = 'register_hat'
