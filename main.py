from njoy_core.io.hid_input import HidEventLoop
from njoy_core.io.virtual_output import OutputDevice
import zmq


def main():
    main_ctx = zmq.Context()
    receiver = main_ctx.socket(zmq.PULL)
    receiver.bind("inproc://main")

    hid_event_loop = HidEventLoop(zmq_context=main_ctx,
                                  zmq_end_point="inproc://main",
                                  monitored_devices={"Joystick - HOTAS Warthog",
                                                     "Throttle - HOTAS Warthog",
                                                     "MFG Crosswind V2"})
    hid_event_loop.start()

    while hid_event_loop.is_alive():
        s = receiver.recv_string()
        print(s)


if __name__ == "__main__":
    main()
