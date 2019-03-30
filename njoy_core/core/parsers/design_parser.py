import lark
import os

from njoy_core.core.model import PhysicalDevice, Axis, Button, Hat
from njoy_core.core.toolbox.essential_toolbox import EssentialToolbox


__BASE_DESIGNS_DIR__ = os.path.join(os.path.dirname(__file__),
                                    os.path.pardir,
                                    os.path.pardir,
                                    'njoy_designs')

# __PARSER__ = lark.Lark(r"""
#     ?start: device*
#
#     model: "nJoyDesign" name ":" instructions
#     name: ESCAPED_STRING
#
#     instructions: instruction*
#     instruction: mapping_import | device_import | control_def
#
#     mapping_imports: mapping_import
#
#     controls: control*
#
#     control: "axis"                             id           "=>" aliases -> axis
#            | "hat"                              id direction "=>" aliases -> hat
#            | "button"                           id           "=>" aliases -> button
#            | ("not button" | "neither buttons") neither_ids  "=>" aliases -> pseudo_button
#
#     neither_ids: INT+
#     id: INT
#     direction: /(up|down)(-(left|right))?|(left|right)/
#     aliases: ALIAS ("," ALIAS)*
#     ALIAS: /\w+/
#
#     %import common.ESCAPED_STRING
#     %import common.INT
#     %import common.WS
#     %ignore WS
#
#     _COMMENT: /#.*/
#     %ignore _COMMENT
# """, parser='lalr')


def parse_design(design_file=None):
    # XXX: stubbed: do as if we parsed the model file, we should get a tree like this one
    input_devices = [
        PhysicalDevice(alias='thr',
                       name="Throttle - HOTAS Warthog"),
        PhysicalDevice(alias='joy',
                       name="Joystick - HOTAS Warthog",
                       guid="030000004F0400000204000000000000"),
        PhysicalDevice(alias='thr2',
                       name="Saitek Pro Flight Throttle Quadrant"),
        PhysicalDevice(alias='pdl',
                       name="MFG Crosswind V2")
    ]

    controls = [
        # Virtual Axes
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='joy', ctrl=0)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='joy', ctrl=1)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='thr', ctrl=0)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='thr', ctrl=1)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='thr', ctrl=2)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='pdl', ctrl=0)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='pdl', ctrl=1)]),
        Axis(processor=EssentialToolbox.passthrough,
             inputs=[Axis(dev='pdl', ctrl=2)]),

        # Virtual Buttons
        Button(processor=EssentialToolbox.passthrough,
               inputs=[Button(dev='thr', ctrl=0)]),
        Button(processor=EssentialToolbox.passthrough,
               inputs=[Button(dev='thr', ctrl=22)]),
        Button(processor=EssentialToolbox.not_any,
               inputs=[Button(dev='thr', ctrl=21),
                       Button(dev='thr', ctrl=22)]),
        Button(processor=EssentialToolbox.passthrough,
               inputs=[Button(dev='thr', ctrl=21)]),

        # Virtual Hats
        Hat(processor=EssentialToolbox.passthrough,
            inputs=[Hat(dev='thr', ctrl=0)])
    ]

    return {'input_devices': input_devices,
            'controls': controls}
