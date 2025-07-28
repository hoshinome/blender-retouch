import bpy
from bpy.types import Panel
from ... import panel_label

def panel_draw(self, context):
    layout = self.layout
    layout.operator("retouch.add_nodes", text="Add Nodes")
    layout.prop(context.scene, "use_nodes")

class RETOUCH_PT_main(Panel):
    bl_idname      = "RETOUCH_PT_main"
    bl_label       = "blener retouch"
    bl_category    = panel_label
    bl_space_type  = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context     = ""
    bl_order       = 0

    def draw(self, context):
        panel_draw(self, context)

classes = (
    RETOUCH_PT_main,
)