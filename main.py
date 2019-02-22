from njoy_core.input_device import InputDevicesMonitor
from njoy_core.output_device import OutputDevice
import zmq


def main():
    main_ctx = zmq.Context()
    input_devices_monitor = InputDevicesMonitor(zmq_context=main_ctx,
                                                device_names=["Joystick - HOTAS Warthog",
                                                              "Throttle - HOTAS Warthog",
                                                              "MFG Crosswind V2"],
                                                output_devices=[OutputDevice(0),
                                                                OutputDevice(1),
                                                                OutputDevice(2)])

    receiver = main_ctx.socket(zmq.PULL)
    receiver.bind("inproc://input_device_monitor")
    input_devices_monitor.start()

    while input_devices_monitor.is_alive():
        s = receiver.recv_string()
        print(s)


if __name__ == "__main__":
    main()
