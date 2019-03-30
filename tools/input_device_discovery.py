import json

from njoy_core.input_node.sdl_joystick import SDLJoystick


def main():
    SDLJoystick.sdl_init()

    devices = []
    for guid, name in SDLJoystick.device_list(exclude_list=['vJoy Device']):
        device = SDLJoystick.open(guid)
        devices.append({
            'GUID': SDLJoystick.to_guid_hex_str(guid),
            'Name': name.decode('utf-8'),
            'Nb_Axes': device.nb_axes,
            'Nb_Buttons': device.nb_buttons,
            'Nb_Balls': device.nb_balls,
            'Nb_Hats': device.nb_hats
        })

    print(json.dumps(devices, indent=True, sort_keys=True))


if __name__ == '__main__':
    main()
