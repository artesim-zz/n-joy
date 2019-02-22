import json
import sdl2


def guid_as_string(guid):
    size = len(guid.data)
    str_bytes = ['{:02x}'.format(guid.data[i]) for i in range(size)]
    return '-'.join([''.join(str_bytes[g*4:g*4+4])
                     for g in range(size // 4)])


def main():
    sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK)

    nb_joysticks = sdl2.SDL_NumJoysticks()
    if nb_joysticks < 0:
        raise Exception(sdl2.SDL_GetError())

    joystick_infos = []
    for i in range(nb_joysticks):
        ji = {
            'GUID': guid_as_string(sdl2.SDL_JoystickGetDeviceGUID(i))
        }

        joystick = sdl2.SDL_JoystickOpen(i)
        if not joystick:
            raise Exception(sdl2.SDL_GetError())

        ji['Name'] = sdl2.SDL_JoystickName(joystick).decode('utf-8')
        ji['Nb_Axes'] = sdl2.SDL_JoystickNumAxes(joystick)
        ji['Nb_Buttons'] = sdl2.SDL_JoystickNumButtons(joystick)
        ji['Nb_Hats'] = sdl2.SDL_JoystickNumHats(joystick)
        ji['Nb_Balls'] = sdl2.SDL_JoystickNumBalls(joystick)

        sdl2.SDL_JoystickClose(joystick)
        joystick_infos.append(ji)

    sdl2.SDL_Quit()

    print(json.dumps(joystick_infos, indent=True, sort_keys=True))


if __name__ == '__main__':
    main()
