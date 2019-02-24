from njoy_core.hid_event_loop import HidEventLoop
import zmq.green as zmq


def main():
    ctx = zmq.Context()
    receiver = ctx.socket(zmq.SUB)
    receiver.setsockopt(zmq.SUBSCRIBE, b'')
    receiver.connect("inproc://hid_event_loop")

    hid_event_loop = HidEventLoop(context=ctx,
                                  events_endpoint="inproc://hid_event_loop",
                                  requests_endpoint="inproc://hid_event_loop_requests")
    hid_event_loop.start()

    requester = ctx.socket(zmq.REQ)
    requester.connect("inproc://hid_event_loop_requests")

    for joystick in ["Joystick - HOTAS Warthog", "Throttle - HOTAS Warthog", "MFG Crosswind V2"]:
        requester.send_pyobj({
            'command': 'subscribe',
            'device_name': joystick
        })
        answer = requester.recv_pyobj()

    while hid_event_loop.is_alive():
        s = receiver.recv_string()
        print(s)


if __name__ == "__main__":
    main()
