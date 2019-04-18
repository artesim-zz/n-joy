# pylint: skip-file
import pytest
import zmq

from njoy_core.core.multiplexers import OutputMultiplexer
from njoy_core.core.model import OutputNode
from njoy_core.core.model import VirtualDevice
from njoy_core.core.model import Axis, Button, Hat, HatState
from njoy_core.core.model import VirtualControlEvent


@pytest.fixture(scope="module")
def context():
    return zmq.Context()


@pytest.mark.ensure_clean_output_node_cache
@pytest.fixture(scope="module")
def device():
    node = OutputNode()
    device = VirtualDevice(node=node)
    node.append(device)
    return device


@pytest.fixture(scope="module",
                params=['axis', 'button', 'hat'])
def event(request, device):
    if request.param == 'axis':
        return VirtualControlEvent(control=Axis(dev=device), value=0.1)
    elif request.param == 'button':
        return VirtualControlEvent(control=Button(dev=device), value=True)
    elif request.param == 'hat':
        return VirtualControlEvent(control=Hat(dev=device), value=HatState.HAT_DOWN)


class TestMultiplexerLoop:
    @staticmethod
    def actuator_socket(context, event):
        socket = context.socket(zmq.DEALER)
        socket.set(zmq.IDENTITY, VirtualControlEvent.mk_identity(event.control))
        socket.connect('inproc://backend')
        return socket

    @staticmethod
    def node_socket(context, event):
        socket = context.socket(zmq.DEALER)
        socket.set(zmq.IDENTITY, VirtualControlEvent.mk_identity(event.control))
        socket.connect('inproc://frontend')
        return socket

    def test_case_1(self, context, event):
        """The output node is already waiting for this event, forward it immediately
        Also signal back to the backend that we treated its event
        """
        actuator_socket = self.actuator_socket(context, event)
        node_socket = self.node_socket(context, event)
        multiplexer = OutputMultiplexer(context=context,
                                        frontend='inproc://frontend',
                                        backend='inproc://backend')

        ready = VirtualControlEvent(control=event.control, value=None)

        actuator_socket.send_multipart([b'', event._serialize_value()])  # Add an empty frame to mimic a REQ socket
        multiplexer._queue[ready.control] = ready
        multiplexer.loop()

        msg_parts = node_socket.recv_multipart()
        assert len(msg_parts) == 2
        assert msg_parts[0] == b''
        assert msg_parts[1] == event._serialize_value()

        msg_parts = actuator_socket.recv_multipart()
        assert len(msg_parts) == 2
        assert msg_parts[0] == b''
        assert msg_parts[1] == ready._serialize_value()

    def test_case_2(self, context, event):
        """The output node is not ready for this event yet, queue it"""
        actuator_socket = self.actuator_socket(context, event)
        multiplexer = OutputMultiplexer(context=context,
                                        frontend='inproc://frontend',
                                        backend='inproc://backend')

        assert len(multiplexer._queue) == 0

        actuator_socket.send_multipart([b'', event._serialize_value()])  # Add an empty frame to mimic a REQ socket
        multiplexer.loop()

        assert len(multiplexer._queue) == 1
        assert event.control in multiplexer._queue.keys()
        assert multiplexer._queue[event.control] == event

    def test_case_3(self, context, event):
        """The backend has already sent an event for this control, forward it immediately
        Also signal back to the backend that we treated its event
        """
        actuator_socket = self.actuator_socket(context, event)
        node_socket = self.node_socket(context, event)
        multiplexer = OutputMultiplexer(context=context,
                                        frontend='inproc://frontend',
                                        backend='inproc://backend')

        ready = VirtualControlEvent(control=event.control, value=None)

        node_socket.send_multipart([b'', ready._serialize_value()])  # Add an empty frame to mimic a REQ socket
        multiplexer._queue[event.control] = event
        multiplexer.loop()

        msg_parts = node_socket.recv_multipart()
        assert len(msg_parts) == 2
        assert msg_parts[0] == b''
        assert msg_parts[1] == event._serialize_value()

        msg_parts = actuator_socket.recv_multipart()
        assert len(msg_parts) == 2
        assert msg_parts[0] == b''
        assert msg_parts[1] == ready._serialize_value()

    def test_case_4(self, context, event):
        """The backend hasn't sent any event for this control yet, queue the request"""
        node_socket = self.node_socket(context, event)
        multiplexer = OutputMultiplexer(context=context,
                                        frontend='inproc://frontend',
                                        backend='inproc://backend')

        ready = VirtualControlEvent(control=event.control, value=None)

        assert len(multiplexer._queue) == 0

        node_socket.send_multipart([b'', ready._serialize_value()])  # Add an empty frame to mimic a REQ socket
        multiplexer.loop()

        assert len(multiplexer._queue) == 1
        assert event.control in multiplexer._queue.keys()
        assert multiplexer._queue[event.control] == ready
