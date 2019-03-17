import glob
import lark
import os


__BASE_MAPPINGS_DIR__ = os.path.join(os.path.dirname(__file__),
                                     os.path.pardir,
                                     os.path.pardir,
                                     'njoy_mappings')

__PARSER__ = lark.Lark(r"""
    ?start: device*

    device: "InputDeviceMapping" name ":" controls
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


class DeviceMappingException(Exception):
    pass


class ObjectsTreeTransformer(lark.Transformer):
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


def parse_device_mappings():
    mappings = dict()
    for mapping_file in glob.glob(os.path.join(__BASE_MAPPINGS_DIR__, '*.njoy-mapping')):
        with open(mapping_file) as f:
            for mapping in ObjectsTreeTransformer().transform(__PARSER__.parse(f.read())):
                if mapping['name'] in mappings:
                    raise DeviceMappingException("Duplicate device mapping for {}".format(mapping['name']))
                mappings[mapping['name']] = mapping
    return mappings
