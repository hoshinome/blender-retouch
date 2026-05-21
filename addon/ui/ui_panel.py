import bpy
from bpy.types import Panel
from ... import panel_label
from ..operator.add_nodes import NODETREE_NAME


class RetouchPanelMixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = panel_label


def _is_retouch_group_name(name):
    return name == NODETREE_NAME or name.startswith(NODETREE_NAME + ".")


def is_retouch_group_applied(context):
    """BlenderRetouch_Nodes がシーンのコンポジターに適用されているか。"""
    scene = context.scene
    if not scene:
        return False

    group = getattr(scene, "compositing_node_group", None)
    if group is not None:
        return _is_retouch_group_name(group.name)

    tree = get_compositor_tree(context)
    if tree is None:
        return False

    if _is_retouch_group_name(tree.name):
        return True

    for node in tree.nodes:
        if node.type == "GROUP" and node.node_tree and _is_retouch_group_name(node.node_tree.name):
            return True

    return False


class RetouchAppliedPanelMixin:
    """リタッチグループ適用時のみ表示するパネル用。"""

    @classmethod
    def poll(cls, context):
        return is_retouch_group_applied(context)


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


def _find_node_by_name(node_tree, name):
    if not node_tree:
        return None
    node = node_tree.nodes.get(name)
    if node:
        return node
    for group_node in node_tree.nodes:
        if group_node.type == "GROUP" and group_node.node_tree:
            found = _find_node_by_name(group_node.node_tree, name)
            if found:
                return found
    return None


def node_get(context, name, input_index):
    """アクティブなノードツリーから指定した入力を安全に取得する"""
    tree = get_compositor_tree(context)
    node = _find_node_by_name(tree, name)
    if node and input_index < len(node.inputs):
        return node.inputs[input_index]
    return None


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
        curves_node = _find_node_by_name(get_compositor_tree(context), "RGB Curves")
        layout.template_curve_mapping(curves_node, "mapping", type="COLOR")

class RETOUCH_PT_lift_gamma_gain(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_lift_gamma_gain"
    bl_label = "Lift/Gamma/Gain"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.prop(node_get(context, "Color Balance", 3), "default_value", text="Lift")


class RETOUCH_PT_color(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color"
    bl_label = "Color"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        # layout.prop(node_get(context, "Hue/Saturation/Value", 2), "default_value", text="Saturation")


class RETOUCH_PT_color_balance(RetouchAppliedPanelMixin, RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_balance"
    bl_label = "Color Balance"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        # layout.prop(node_get(context, "Color Balance.001", 3), "default_value", text="Shadow (Color Lift)")


classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
    RETOUCH_PT_lift_gamma_gain,
    RETOUCH_PT_color,
    RETOUCH_PT_color_balance,
)