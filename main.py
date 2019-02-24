from njoy_core.hid_event_loop import HidEventLoop
import zmq


def main():
    ctx = zmq.Context()
    receiver = ctx.socket(zmq.SUB)
    receiver.setsockopt(zmq.SUBSCRIBE, b'')
    receiver.connect("inproc://hid_event_loop")

    hid_event_loop = HidEventLoop(zmq_context=ctx,
                                  zmq_end_point="inproc://hid_event_loop",
                                  monitored_devices={"Joystick - HOTAS Warthog",
                                                     "Throttle - HOTAS Warthog",
                                                     "MFG Crosswind V2"})
    hid_event_loop.start()

    while hid_event_loop.is_alive():
        s = receiver.recv_string()
        print(s)


if __name__ == "__main__":
    main()
