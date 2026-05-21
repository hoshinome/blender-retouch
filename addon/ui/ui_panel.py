import bpy
from bpy.types import Panel
from ... import panel_label
from ..operator.add_nodes import NODETREE_NAME

class RetouchPanelMixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = panel_label

    @classmethod
    def poll(cls, context):
        # リタッチグループが適用されている時だけパネルを表示する
        return is_retouch_group_applied(context)

def is_retouch_group_applied(context):
    if not (scene := context.scene):
        return False

    def is_retouch(name):
        return name == NODETREE_NAME or name.startswith(NODETREE_NAME + ".")

    if (group := getattr(scene, "compositing_node_group", None)) is not None:
        return is_retouch(group.name)

    if (tree := get_compositor_tree(context)) is None:
        return False

    return is_retouch(tree.name) or any(
        is_retouch(n.node_tree.name)
        for n in tree.nodes
        if n.type == "GROUP" and n.node_tree
    )

def get_compositor_tree(context):
    space = context.space_data
    if space and space.type == "NODE_EDITOR" and getattr(space, "tree_type", None) == "CompositorNodeTree":
        if hasattr(space, "edit_tree") and space.edit_tree:
            return space.edit_tree

    scene = context.scene
    if not scene:
        return None

    if hasattr(scene, "compositing_node_group") and scene.compositing_node_group:
        return scene.compositing_node_group

    if hasattr(scene, "compositor") and scene.compositor and getattr(scene.compositor, "node_tree", None):
        return scene.compositor.node_tree

    if hasattr(scene, "compositor_node_tree") and scene.compositor_node_tree:
        return scene.compositor_node_tree

    if hasattr(scene, "node_tree") and scene.node_tree:
        return scene.node_tree

    return None


def find_node_by_name(tree, name):
    if not tree:
        return None
    if node := tree.nodes.get(name):
        return node
    return next(
        (found for n in tree.nodes
         if n.type == "GROUP" and (found := find_node_by_name(n.node_tree, name))),
        None
    )


def node_get(context, name, input_index=None):
    node = find_node_by_name(get_compositor_tree(context), name)
    if not node or input_index is None:
        return node
    return node.inputs[input_index] if isinstance(input_index, int) and input_index < len(node.inputs) else None


def draw_prop(layout, data, prop, text=""):
    if data is not None:
        layout.prop(data, prop, text=text)


def node_prop_data_path(context, node, prop):
    scene, tree = context.scene, node.id_data
    try:
        rel = node.path_from_id(prop)
    except (TypeError, AttributeError, ValueError):
        rel = f'nodes["{node.name}"].{prop}'

    if hasattr(scene, "compositing_node_group") and scene.compositing_node_group == tree:
        return f"scene.compositing_node_group.{rel}"
    if getattr(getattr(scene, "compositor", None), "node_tree", None) == tree:
        return f"scene.compositor.node_tree.{rel}"
    return f'bpy.data.node_groups["{tree.name}"].{rel}'


class RETOUCH_PT_main(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_main"
    bl_label = "Blender Retouch"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.scale_y = 2.0
        row.operator("retouch.add_nodes", text="Apply Retouch Nodes")

class RETOUCH_PT_light(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_light"
    bl_label = "Light"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        draw_prop(layout, node_get(context, "Exposure", 1), "default_value", text="Exposure")
        draw_prop(layout, node_get(context, "Brightness/Contrast", 2), "default_value", text="Contrast")
        draw_prop(layout, node_get(context, "Color Correction", 10), "default_value", text="Highlight")
        draw_prop(layout, node_get(context, "Color Correction", 20), "default_value", text="Shadow")
        draw_prop(layout, node_get(context, "Color Correction", 9), "default_value", text="White Level")
        draw_prop(layout, node_get(context, "Color Correction", 19), "default_value", text="Black Level")

class RETOUCH_PT_lift_gamma_gain(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_lift_gamma_gain"
    bl_label = "Lift/Gamma/Gain"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 2
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        draw_prop(layout, node_get(context, "Color Balance", 3), "default_value", text="Lift")
        draw_prop(layout, node_get(context, "Color Balance", 5), "default_value", text="Gamma")
        draw_prop(layout, node_get(context, "Color Balance", 7), "default_value", text="Gain")

class RETOUCH_PT_curves(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_curves"
    bl_label = "RGB Curves"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        curves_node = find_node_by_name(get_compositor_tree(context), "RGB Curves")
        if curves_node is not None:
            layout.template_curve_mapping(curves_node, "mapping", type="COLOR", show_tone=True)

class RETOUCH_PT_color(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color"
    bl_label = "Color"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        draw_prop(layout, node_get(context, "Switch", 0), "default_value", text="Monochrome")
        wb_node = node_get(context, "Color Balance.001")
        if wb_node is not None:
            row = layout.row(align=True)
            row.label(text="White Balance")
            row.operator("ui.eyedropper_color", text="", icon="EYEDROPPER").prop_data_path = (
                node_prop_data_path(context, wb_node, "input_whitepoint")
            )

        draw_prop(layout, node_get(context, "Color Balance.001", 15), "default_value", text="Temperature")
        draw_prop(layout, node_get(context, "Color Balance.001", 16), "default_value", text="Tint")
        draw_prop(layout, node_get(context, "BR_Color", 1), "default_value", text="Saturation")
        draw_prop(layout, node_get(context, "BR_Color", 2), "default_value", text="Natural Saturation")

class RETOUCH_PT_color_mixier(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_mixier"
    bl_label = "Color Mixier"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self,context):
        layout = self.layout
        curves_node = find_node_by_name(get_compositor_tree(context), "Hue Correct")
        if curves_node is not None:
            layout.template_curve_mapping(curves_node, "mapping", type="HUE")

class RETOUCH_PT_color_balance(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_balance"
    bl_label = "Color Balance"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 6
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        draw_prop(layout, node_get(context, "Color Balance.002", 4), "default_value", text="Lift")
        draw_prop(layout, node_get(context, "Color Balance.002", 6), "default_value", text="Gamma")
        draw_prop(layout, node_get(context, "Color Balance.002", 8), "default_value", text="Gain")
        draw_prop(layout, node_get(context, "Mix", 7), "default_value", text="Offset")
        draw_prop(layout, node_get(context, "Color Balance.002", 1), "default_value", text="Strength")

class RETOUCH_PT_effect(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_effect"
    bl_label = "Effect"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 7

    def draw(self, context):
        layout = self.layout

        scn_sets: 'RETOUCH_PG_tabs' = context.scene.retouch
        self.scn_sets = scn_sets
        scene = context.scene
        row = layout.row(align=True)
        row.scale_y = 1
        row.prop(context.scene.retouch, "panel_tabs", expand=True)
        col = layout.column(align=True)
        if scn_sets.panel_tabs == "Effects":
            draw_prop(layout, node_get(context, "BR_Effect", 1), "default_value", text="Texture")
            draw_prop(layout, node_get(context, "BR_Effect", 2), "default_value", text="Clarity")
        if scn_sets.panel_tabs == "Vignette":
            draw_prop(col, node_get(context, "Vignette", 1), "default_value", text="Strength")
            draw_prop(col, node_get(context, "Vignette", 2), "default_value", text="Feather")
            draw_prop(col, node_get(context, "Vignette", 3), "default_value", text="Corner Roundness")
            draw_prop(col, node_get(context, "Vignette", 4), "default_value", text="Scale")
        if scn_sets.panel_tabs == "Grain":
            draw_prop(layout, node_get(context, "BR_Grain", 1), "default_value", text="Strength")
            draw_prop(layout, node_get(context, "BR_Grain", 2), "default_value", text="Scale")
            draw_prop(layout, node_get(context, "BR_Grain", 3), "default_value", text="Roughness")
            draw_prop(layout, node_get(context, "BR_Grain", 4), "default_value", text="Seed")

classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
    RETOUCH_PT_curves,
    RETOUCH_PT_lift_gamma_gain,
    RETOUCH_PT_color,
    RETOUCH_PT_color_mixier,
    RETOUCH_PT_color_balance,
    RETOUCH_PT_effect,
)