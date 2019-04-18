#
# WARNING:
# Need to set PYSDL2_DLL_PATH=../../../lib64/sdl2 for this test
#
import pytest
import zmq

from njoy_core.input_node.hid_event_loop import HidEventLoop


@pytest.fixture(scope="module")
def context():
    return zmq.Context()


class MockInputNode:
    def __init__(self, context):
        self.context = context
        self.requests_in = context.socket(zmq.REP)
        self.events_in = context.socket(zmq.PULL)
        self.requests_out = context.socket(zmq.REQ)
        self.events_out = context.socket(zmq.PUSH)
        self.requests_in.bind('inproc://requests')
        self.events_in.bind('inproc://events')
        self.requests_out.connect('inproc://requests')
        self.events_out.connect('inproc://events')


class TestLoop:
    def test_case_1(self, mocker, context):
        input_node = MockInputNode(context)
        hid_event_loop = HidEventLoop()
        mocker.patch('sdl2.ext.get_events')
