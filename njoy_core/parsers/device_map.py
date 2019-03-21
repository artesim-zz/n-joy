import glob
import lark
import os


__BASE_DEVICE_MAPS_DIR__ = os.path.join(os.path.dirname(__file__),
                                        os.path.pardir,
                                        os.path.pardir,
                                        'njoy_device_maps')

__PARSER__ = lark.Lark(r"""
    ?start: device*

    device: "nJoyDeviceMap" name ":" controls
    name: ESCAPED_STRING
    controls: control*

    control: "axis"                             id           "=>" aliases -> axis
           | "hat"                              id direction "=>" aliases -> hat
           | "button"                           id           "=>" aliases -> button
           | ("not button" | "neither buttons") neither_ids  "=>" aliases -> pseudo_button

    neither_ids: INT+
    id: INT
    direction: /(up|down)(-(left|right))?|(left|right)/
    aliases: ALIAS ("," ALIAS)*
    ALIAS: /\w+/

    %import common.ESCAPED_STRING
    %import common.INT
    %import common.WS
    %ignore WS

    _COMMENT: /#.*/
    %ignore _COMMENT
""", parser='lalr')


class DeviceMapException(Exception):
    pass


class DeviceMapParser(lark.Transformer):
    start = list

    @lark.v_args(inline=True)
    def device(self, name, controls):
        return {
            'name': name,
            'controls': controls
        }

    @lark.v_args(inline=True)
    def name(self, name):
        return str(name[1:-1])

    controls = list

    @lark.v_args(inline=True)
    def axis(self, _id, aliases):
        return {
            'type': 'axis',
            'id': _id,
            'aliases': aliases
        }

    @lark.v_args(inline=True)
    def button(self, _id, aliases):
        return {
            'type': 'button',
            'id': _id,
            'aliases': aliases
        }

    @lark.v_args(inline=True)
    def pseudo_button(self, neither_ids, aliases):
        return {
            'type': 'pseudo_button',
            'neither_ids': neither_ids,
            'aliases': aliases
        }

    @lark.v_args(inline=True)
    def hat(self, _id, direction, aliases):
        return {
            'type': 'hat',
            'id': _id,
            'direction': direction,
            'aliases': aliases
        }

    @lark.v_args(inline=True)
    def id(self, _id):
        return int(_id)

    @staticmethod
    def neither_ids(ids):
        return [int(i) for i in ids]

    @lark.v_args(inline=True)
    def direction(self, direction):
        return str(direction)

    @staticmethod
    def aliases(aliases):
        return [str(alias) for alias in aliases]


def parse_device_maps(*device_map_files):
    map_files = device_map_files or glob.glob(os.path.join(__BASE_DEVICE_MAPS_DIR__, '*.njoy-device-map'))
    device_maps = dict()
    for map_file in map_files:
        with open(map_file) as f:
            for device_map in DeviceMapParser().transform(__PARSER__.parse(f.read())):
                if device_map['name'] in device_maps:
                    raise DeviceMapException("Duplicate device map for {}".format(device_map['name']))
                device_maps[device_map['name']] = device_map
    return device_maps

# EOF
