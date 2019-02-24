import zmq.green as zmq

from njoy_core.hid_event_loop import HidEventLoop
from njoy_core.messages import HidEvent


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

    controls = dict()
    for joystick in ["Joystick - HOTAS Warthog",
                     "Throttle - HOTAS Warthog",
                     "MFG Crosswind V2",
                     "Saitek Pro Flight Throttle Quadrant"]:
        requester.send_multipart([b'open', joystick.encode('utf-8')])
        full_state = requester.recv_pyobj()
        if full_state is not None:
            for ctrl_state in full_state:
                ctrl_id = ctrl_state[0:3]
                if ctrl_id in controls:
                    print("Skipping duplicate control : {}".format(ctrl_id))
                else:
                    controls[ctrl_id] = ctrl_state

    _tmp = sorted(controls.values(), key=lambda c: c[0:3])

    while hid_event_loop.is_alive():
        msg = HidEvent.recv(receiver)
        print(str(msg))


if __name__ == "__main__":
    main()
