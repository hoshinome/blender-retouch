import bpy
from bpy.types import Panel
from ... import panel_label

class RetouchPanelMixin:
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = panel_label

def nodes_get(name, inputs):
    scene = bpy.context.scene
    node_tree = scene.node_tree
    node = node_tree.nodes.get(name)
    if node:
        return node.inputs[inputs]
    return None

class RETOUCH_PT_main(RetouchPanelMixin,Panel):
    bl_idname      = "RETOUCH_PT_main"
    bl_label       = "blener retouch"
    bl_category    = panel_label
    bl_space_type  = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context     = ""
    bl_order       = 0

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.scale_x = 1.0
        row.scale_y = 2.0
        row.operator("retouch.add_nodes", text="Add Nodes")
        layout.prop(context.scene, "use_nodes")

class RETOUCH_PT_light(RetouchPanelMixin, Panel):
    bl_idname      = "RETOUCH_PT_light"
    bl_label       = "Light"
    bl_parent_id   = RETOUCH_PT_main.bl_idname
    bl_order       = 1

    def draw(self,context):
        layout = self.layout
        scene = bpy.data.scenes["Scene"]
        layout.prop(nodes_get("Exposure", 1), "default_value", text="Exposure")
        layout.prop(nodes_get("Brightness/Contrast", 2), "default_value", text="Contrast")
        layout.prop(nodes_get("Color Balance", 2), "default_value", text="Lift")
        layout.prop(nodes_get("Color Balance", 4), "default_value", text="Gamma")
        layout.prop(nodes_get("Color Balance", 6), "default_value", text="Gain")
        layout.template_curve_mapping(scene.node_tree.nodes.get("RGB Curves"), "mapping", type="COLOR",)

classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
)