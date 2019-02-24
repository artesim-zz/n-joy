import gevent
import threading
import sdl2
import sdl2.ext
import zmq.green as zmq

from njoy_core.io.sdl_joystick import SDLJoystick


class HidEventLoopException(Exception):
    """Top-level class for all exceptions raised from this module."""
    pass


class HidEventLoopQuit(HidEventLoopException):
    pass


class HidEventLoop(threading.Thread):
    def __init__(self, context, events_endpoint, requests_endpoint):
        super(HidEventLoop, self).__init__()
        self._joysticks = dict()
        self._ctx = context
        self._events_endpoint = events_endpoint
        self._requests_endpoint = requests_endpoint

    def _requests_handler(self):
        socket = self._ctx.socket(zmq.REP)
        socket.bind(self._requests_endpoint)

        while True:
            request = socket.recv_pyobj()

            if request['command'] == 'subscribe':
                joystick = SDLJoystick.open(request['device_name'])
                self._joysticks[joystick.instance_id] = joystick

                socket.send_pyobj(True)
            else:
                socket.send_pyobj(False)

    def _event_loop(self):
        socket = self._ctx.socket(zmq.PUB)
        socket.bind(self._events_endpoint)

        while gevent.sleep(0) is None:
            events = sdl2.ext.get_events()
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    raise HidEventLoopQuit()

                elif event.type == sdl2.SDL_JOYAXISMOTION:
                    socket.send_string("/{}/axes/{} = {}".format(event.jaxis.which,
                                                                 event.jaxis.axis,
                                                                 event.jaxis.value))

                elif event.type == sdl2.SDL_JOYBALLMOTION:
                    socket.send_string("/{}/balls/{} = ({}, {})".format(event.jball.which,
                                                                        event.jball.ball,
                                                                        event.jball.xrel,
                                                                        event.jball.yrel))

                elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                    socket.send_string("/{}/buttons/{} = {}".format(event.jbutton.which,
                                                                    event.jbutton.button,
                                                                    event.jbutton.state))

                elif event.type == sdl2.SDL_JOYHATMOTION:
                    socket.send_string("/{}/hats/{} = {}".format(event.jhat.which,
                                                                 event.jhat.hat,
                                                                 event.jhat.value))

    def run(self, *args, **kwargs):
        SDLJoystick.sdl_init()

        requests_server = gevent.spawn(self._requests_handler)
        event_loop = gevent.spawn(self._event_loop)
        gevent.joinall([requests_server, event_loop])

        for joystick in self._joysticks.values():
            joystick.close()

        SDLJoystick.sdl_quit()
