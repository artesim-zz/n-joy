import zmq.green as zmq

from njoy_core.combined_joysticks import CombinedJoystick
from njoy_core.input_node.hid_event_loop import HidEventLoop


def main():
    ctx = zmq.Context()

    hid_event_loop = HidEventLoop(context=ctx,
                                  events_endpoint="inproc://hid_event_loop",
                                  requests_endpoint="inproc://hid_event_loop_requests")

    ctrl_pool = CombinedJoystick(hid_event_loop)

    hid_event_loop.start()
    ctrl_pool.start()
    ctrl_pool.join()


if __name__ == "__main__":
    main()
