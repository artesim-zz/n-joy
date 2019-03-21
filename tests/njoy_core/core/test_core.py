import random
import threading
import time
import zmq

from njoy_core.common.messages import HatValue, ControlEvent
from njoy_core.common.messages import InputNodeRegisterRequest, InputNodeRegisterReply
from njoy_core.core import Core


class MockInputNode(threading.Thread):
    def __init__(self, context, requests_endpoint, events_endpoint):
        super().__init__()
        self._ctx = context
        self._requests_socket = context.socket(zmq.REQ)
        self._requests_socket.connect(requests_endpoint)
        self._events_socket = context.socket(zmq.PUSH)
        self._events_socket.connect(events_endpoint)

    def _register(self):
        # First send our list of joysticks to njoy_core
        InputNodeRegisterRequest(devices=['Joystick - HOTAS Warthog',
                                          'Throttle - HOTAS Warthog']).send(self._requests_socket)
        print("Input Node: sent request")

        # The nJoy core replies with the list of those it's interested in, if any...
        reply = InputNodeRegisterReply.recv(self._requests_socket)
        print("Input Node: Received answer")
        return reply

    def _events_loop(self):
        print("Input Node: starting event loop")
        identities = [{'node': 0, 'device': 0, 'control': i}
                      for i in range(10)]
        sent = 0
        while True:
            identity = random.choice(identities)
            if identity['control'] in {7, 8}:
                value = random.uniform(-1, 1)
            elif identity['control'] in {9}:
                value = random.choice(HatValue.list())
            else:
                value = random.choice([False, True])

            ControlEvent(**identity, value=value).send(self._events_socket)
            sent += 1
            if sent % 1000 == 0:
                print("Mux In: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Mux In: Pausing 10s...")
                time.sleep(10)
            else:
                time.sleep(0.0001)  # 100 µs

    def run(self):
        self._register()
        self._events_loop()


def main():
    random.seed()

    context = zmq.Context()

    input_node = MockInputNode(context=context,
                               requests_endpoint='inproc://requests',
                               events_endpoint='inproc://input')

    core = Core(context=context,
                input_events='inproc://input',
                output_events='inproc://output',
                requests='inproc://requests')

    input_node.start()
    core.start()

    input_node.join()
    core.join()


if __name__ == '__main__':
    main()
