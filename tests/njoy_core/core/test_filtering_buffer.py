import pytest
import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.filtering_buffer import FilteringBuffer
from njoy_core.common.messages import NamedControlEvent

ZMQ_CONTEXT = zmq.Context()


@pytest.fixture
def filtering_buffer():
    return FilteringBuffer(context=ZMQ_CONTEXT,
                           input_endpoint='inproc://input',
                           input_identities=[i.encode('utf-8') for i in ['id1', 'id2', 'id3']])


def test_initial_state(filtering_buffer):
    assert filtering_buffer.input_values is None


def test_simple_transmission(pseudo_router, filtering_buffer):
    filtering_buffer.start()
    input_states = [True, False, True]
    pseudo_router(input_states)
    assert pseudo_router.states == input_states


class MockRouter(gevent.Greenlet):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.PUB)
        self._socket.bind(endpoint)

    def _run(self):
        identities = ['id{:d}'.format(1 + i) for i in range(6)]
        sent = 0
        while True:
            for identity in random.choices(identities, k=3):
                state = 1 == random.randint(0, 1)
                NamedControlEvent(identity, state).send(self._socket)
                sent += 1
                if sent % 1000 == 0:
                    print("Router: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Router: Pausing 10s...")
                gevent.sleep(10)
            else:
                gevent.sleep(0.001)


class MockControl(gevent.Greenlet):
    def __init__(self, context, input_endpoint, input_identities):
        super().__init__()
        self._filter = FilteringBuffer(context=context,
                                       input_endpoint=input_endpoint,
                                       input_identities=input_identities)
        self._value = None

    def _run(self):
        self._filter.start()

        received = 0
        while True:
            states = self._filter.input_values
            if states is not None:
                received += 1
                if received % 100 == 0:
                    print("Control: received {} messages".format(received))
            i = 0
            for _ in range(random.randint(10000,
                                          11000)):
                i += 1

            gevent.sleep(0.001)


if __name__ == '__main__':
    random.seed()

    router = MockRouter(context=ZMQ_CONTEXT,
                        endpoint='inproc://input')

    control = MockControl(context=ZMQ_CONTEXT,
                          input_endpoint='inproc://input',
                          input_identities=['id1', 'id2', 'id3'])

    grp = gevent.pool.Group()
    grp.start(router)
    grp.start(control)
    grp.join()

# EOF
