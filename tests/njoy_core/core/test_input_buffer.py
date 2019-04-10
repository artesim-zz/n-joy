import pytest
import zmq

from njoy_core.core.input_buffer import InputBuffer
from njoy_core.core.model import InputNode
from njoy_core.core.model import PhysicalDevice
from njoy_core.core.model import Axis, Button, Hat, HatState
from njoy_core.core.model import PhysicalControlEvent


@pytest.fixture(scope="module")
def context():
    return zmq.Context()


@pytest.fixture(scope="module")
def controls():
    node = InputNode()
    device = PhysicalDevice(node=node, alias='a', name='n')
    node.append(device)
    return {'axis': Axis(dev=device),
            'button': Button(dev=device),
            'hat': Hat(dev=device)}


def initial_loop_recv(input_buffer, control, value):
    event = PhysicalControlEvent(control=control, value=value)
    input_buffer._socket.recv_multipart.return_value = event._serialize_control() + event._serialize_value()
    input_buffer.initial_loop()


def loop_recv(input_buffer, control, value):
    event = PhysicalControlEvent(control=control, value=value)
    input_buffer._socket.recv_multipart.return_value = event._serialize_control() + event._serialize_value()
    input_buffer.loop()


@pytest.mark.ensure_clean_physical_device_cache
class TestInitialLoop:
    @pytest.mark.parametrize("ctrl,expected", [('axis', 0.1),
                                               ('button', True),
                                               ('hat', HatState.HAT_DOWN)])
    def test_case_1(self, mocker, context, controls, ctrl, expected):
        """The initial loop collects events until we have a full set of control values.
        When we do, this full state is put in an internal queue, so it can be consumed
        when reading the state property.
        The internal queue remains empty during this phase."""
        control = controls[ctrl]
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=[control])
        mocker.patch.object(input_buffer._socket, 'recv_multipart', autospec=True)

        initial_loop_recv(input_buffer, controls[ctrl], expected)
        state = input_buffer.state
        assert state is not None
        assert state[control] == expected

    def test_case_2(self, mocker, context, controls):
        """The initial loop collects events until we have a full set of control values.
        When we do, this full state is put in an internal queue, so it can be consumed
        when reading the state property.
        The internal queue remains empty during this phase."""
        expected = {controls['axis']: 0.1,
                    controls['button']: True,
                    controls['hat']: HatState.HAT_DOWN}
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=list(expected.keys()))
        mocker.patch.object(input_buffer._socket, 'recv_multipart', autospec=True)

        initial_loop_recv(input_buffer, controls['axis'], expected[controls['axis']])
        assert len(input_buffer._state_queue) == 0

        initial_loop_recv(input_buffer, controls['button'], expected[controls['button']])
        assert len(input_buffer._state_queue) == 0

        initial_loop_recv(input_buffer, controls['hat'], expected[controls['hat']])
        state = input_buffer.state
        assert state is not None
        assert len(state) == len(expected)
        for (k, v) in state.items():
            assert expected[k] == v


@pytest.mark.ensure_clean_physical_device_cache
class TestLoop:
    def test_case_1(self, mocker, context, controls):
        """The main loop collects events as fast as it can, but only publishes a new state when something changed."""
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=[controls[k] for k in ['axis', 'button', 'hat']])
        mocker.patch.object(input_buffer._socket, 'recv_multipart', autospec=True)

        initial_loop_recv(input_buffer, controls['axis'], 0.1)
        initial_loop_recv(input_buffer, controls['button'], True)
        initial_loop_recv(input_buffer, controls['hat'], HatState.HAT_DOWN)
        assert input_buffer.state is not None

        loop_recv(input_buffer, controls['axis'], 0.1)
        assert len(input_buffer._state_queue) == 0

        loop_recv(input_buffer, controls['button'], True)
        assert len(input_buffer._state_queue) == 0

        loop_recv(input_buffer, controls['hat'], HatState.HAT_DOWN)
        assert len(input_buffer._state_queue) == 0

    @pytest.mark.parametrize("ctrl,expected", [('axis', 0.2),
                                               ('button', False),
                                               ('hat', HatState.HAT_UP)])
    def test_case_2(self, mocker, context, controls, ctrl, expected):
        """The main loop collects events as fast as it can, but only publishes a new state when something changed."""
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=[controls[k] for k in ['axis', 'button', 'hat']])
        mocker.patch.object(input_buffer._socket, 'recv_multipart', autospec=True)

        initial_loop_recv(input_buffer, controls['axis'], 0.1)
        initial_loop_recv(input_buffer, controls['button'], True)
        initial_loop_recv(input_buffer, controls['hat'], HatState.HAT_DOWN)
        assert input_buffer.state is not None

        loop_recv(input_buffer, controls[ctrl], expected)
        state = input_buffer.state
        assert state is not None
        assert len(state) == 3
        assert state[controls[ctrl]] == expected


@pytest.mark.ensure_clean_physical_device_cache
class TestState:
    @pytest.mark.parametrize("ctrl", ['axis', 'button', 'hat'])
    def test_case_1(self, context, controls, ctrl):
        """Reading a state pops it from the internal queue, so each state change can only be consumed once."""
        control = controls[ctrl]
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=[control])
        assert len(input_buffer._state_queue) == 0

    @pytest.mark.parametrize("ctrl,value", [('axis', 0.1),
                                            ('button', True),
                                            ('hat', HatState.HAT_DOWN)])
    def test_case_2(self, mocker, context, controls, ctrl, value):
        """Reading a state pops it from the internal queue, so each state change can only be consumed once."""
        control = controls[ctrl]
        input_buffer = InputBuffer(context=context,
                                   input_endpoint='inproc://input',
                                   physical_controls=[control])
        mocker.patch.object(input_buffer._socket, 'recv_multipart', autospec=True)

        initial_loop_recv(input_buffer, controls[ctrl], value)
        assert input_buffer.state is not None
        assert len(input_buffer._state_queue) == 0
