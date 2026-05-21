import bpy
from bpy.types import Panel
from ... import panel_label
from ..operator.add_nodes import NODETREE_NAME

class RetouchPanelMixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = panel_label

class RetouchAppliedPanelMixin:
    """リタッチグループ適用時のみ表示するパネル用。"""

    @classmethod
    def poll(cls, context):
        return is_retouch_group_applied(context)

def is_retouch_group_applied(context):
    """BlenderRetouch_Nodes がシーンのコンポジターに適用されているか。"""
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


def _find_node_by_name(tree, name):
    if not tree:
        return None
    if node := tree.nodes.get(name):
        return node
    return next(
        (found for n in tree.nodes
         if n.type == "GROUP" and (found := _find_node_by_name(n.node_tree, name))),
        None
    )


def node_get(context, name, input_index=None):
    """
    ノード、または入力ソケットを取得する。

    - input_index 省略: ノード本体 → layout.prop(node_get(ctx, "X"), "input_whitepoint")
    - input_index 指定: 入力ソケット → layout.prop(node_get(ctx, "X", 15), "default_value")
    """
    node = _find_node_by_name(get_compositor_tree(context), name)
    if not node or input_index is None:
        return node
    return node.inputs[input_index] if isinstance(input_index, int) and input_index < len(node.inputs) else None


def _node_prop_data_path(context, node, prop):
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

        if not is_retouch_group_applied(context):
            layout.label(text="リタッチノードを適用してください", icon="INFO")


class RETOUCH_PT_light(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_light"
    bl_label = "Light"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 1

    def draw(self, context):
        layout = self.layout

        layout.prop(node_get(context, "Exposure", 1), "default_value", text="Exposure")
        layout.prop(node_get(context, "Brightness/Contrast", 2), "default_value", text="Contrast")
        layout.prop(node_get(context, "Color Correction", 10), "default_value", text="Highlight")
        layout.prop(node_get(context, "Color Correction", 20), "default_value", text="Shadow")
        layout.prop(node_get(context, "Color Correction", 9), "default_value", text="White Level")
        layout.prop(node_get(context, "Color Correction", 19), "default_value", text="Black Level")
        # curves_node = _find_node_by_name(get_compositor_tree(context), "RGB Curves")
        # layout.template_curve_mapping(curves_node, "mapping", type="COLOR")

class RETOUCH_PT_curves(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_curves"
    bl_label = "RGB Curves"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        curves_node = _find_node_by_name(get_compositor_tree(context), "RGB Curves")
        layout.template_curve_mapping(curves_node, "mapping", type="COLOR")

class RETOUCH_PT_lift_gamma_gain(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_lift_gamma_gain"
    bl_label = "Lift/Gamma/Gain"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(node_get(context, "Color Balance", 3), "default_value", text="Lift")
        layout.prop(node_get(context, "Color Balance", 5), "default_value", text="Gamma")
        layout.prop(node_get(context, "Color Balance", 7), "default_value", text="Gain")


class RETOUCH_PT_color(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color"
    bl_label = "Color"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        layout.prop(node_get(context, "Color Balance.002", 15), "default_value", text="Temperature")
        layout.prop(node_get(context, "Color Balance.002", 16), "default_value", text="Tint")
        # layout_node_eyedropper_icon(
        #     layout, context, "Color Balance.002", "input_whitepoint", text="White Point"
        # )
        row = layout.row(align=True)
        row.label(text="White Balance")
        row.operator("ui.eyedropper_color", text="", icon="EYEDROPPER").prop_data_path = (
            _node_prop_data_path(context, node_get(context, "Color Balance.002"), "input_whitepoint")
        )


class RETOUCH_PT_color_balance(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_balance"
    bl_label = "Color Balance"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        # layout.prop(node_get(context, "Color Balance.001", 3), "default_value", text="Shadow (Color Lift)")


classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
    RETOUCH_PT_curves,
    RETOUCH_PT_lift_gamma_gain,
    RETOUCH_PT_color,
    RETOUCH_PT_color_balance,
)