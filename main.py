import zmq.green as zmq

from njoy_core.hid_event_loop import HidEventLoop
from njoy_core.messages import Message, HidDeviceFullStateMsg


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
        full_state_msg = Message.recv(requester)
        if isinstance(full_state_msg, HidDeviceFullStateMsg):
            for ctrl_event in full_state_msg.control_events:
                if ctrl_event in controls:
                    print("Skipping duplicate control : {}".format(ctrl_event))
                else:
                    controls[ctrl_event] = ctrl_event

    _tmp = sorted(controls.values())

    while hid_event_loop.is_alive():
        msg = Message.recv(receiver)
        print(str(msg))


if __name__ == "__main__":
    main()
