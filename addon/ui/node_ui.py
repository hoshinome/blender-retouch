"""コンポジターノードをパネルに描画するための再利用可能な UI ヘルパー。"""

EYEDROPPER_OPERATOR = "ui.eyedropper_color"
EYEDROPPER_ICON = "EYEDROPPER"


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


def find_node_by_name(node_tree, name):
    if not node_tree:
        return None
    node = node_tree.nodes.get(name)
    if node:
        return node
    for group_node in node_tree.nodes:
        if group_node.type == "GROUP" and group_node.node_tree:
            found = find_node_by_name(group_node.node_tree, name)
            if found:
                return found
    return None


def node_get(context, name, input_index=None):
    """
    ノード、または入力ソケットを取得する。

    - input_index 省略: ノード本体
    - input_index 指定: inputs[input_index]
    """
    tree = get_compositor_tree(context)
    node = find_node_by_name(tree, name)
    if not node:
        return None
    if input_index is None:
        return node
    if isinstance(input_index, int) and input_index < len(node.inputs):
        return node.inputs[input_index]
    return None


def node_prop_path(context, node, prop_name):
    """ui.eyedropper_color 用の RNA パス（scene から解決できる形式）。"""
    try:
        rel = node.path_from_id(prop_name)
    except (TypeError, AttributeError, ValueError):
        rel = f'nodes["{node.name}"].{prop_name}'

    scene = context.scene
    tree = node.id_data

    if hasattr(scene, "compositing_node_group") and scene.compositing_node_group == tree:
        return f"scene.compositing_node_group.{rel}"

    if hasattr(scene, "compositor") and getattr(scene.compositor, "node_tree", None) == tree:
        return f"scene.compositor.node_tree.{rel}"

    return f'bpy.data.node_groups["{tree.name}"].{rel}'


class CompositorNodeUI:
    """リタッチ用コンポジターノードのパネル UI を描画する。"""

    def __init__(self, layout, context):
        self.layout = layout
        self.context = context

    def _node(self, node_name):
        return node_get(self.context, node_name)

    def socket(self, node_name, socket_index, *, text=""):
        """入力ソケットの default_value を描画する。"""
        sock = node_get(self.context, node_name, socket_index)
        if not sock:
            return False
        self.layout.prop(sock, "default_value", text=text)
        return True

    def prop(self, node_name, prop_name, *, text=""):
        """ノード RNA プロパティを描画する。"""
        node = self._node(node_name)
        if not node or not hasattr(node, prop_name):
            return False
        self.layout.prop(node, prop_name, text=text)
        return True

    def eyedropper(
        self,
        node_name,
        prop_name,
        *,
        text="",
        operator=EYEDROPPER_OPERATOR,
        icon=EYEDROPPER_ICON,
    ):
        """ラベル + スポイトアイコンのみ。"""
        node = self._node(node_name)
        if not node or not hasattr(node, prop_name):
            return False

        row = self.layout.row(align=True)
        row.label(text=text)

        sub = row.row(align=True)
        sub.alignment = "RIGHT"
        op = sub.operator(operator, text="", icon=icon)
        op.prop_data_path = node_prop_path(self.context, node, prop_name)
        return True

    def prop_with_eyedropper(self, node_name, prop_name, *, text=""):
        """プロパティ + スポイトアイコンを1行で描画する。"""
        node = self._node(node_name)
        if not node or not hasattr(node, prop_name):
            return False

        row = self.layout.row(align=True)
        row.prop(node, prop_name, text=text)

        sub = row.row(align=True)
        sub.alignment = "RIGHT"
        op = sub.operator(EYEDROPPER_OPERATOR, text="", icon=EYEDROPPER_ICON)
        op.prop_data_path = node_prop_path(self.context, node, prop_name)
        return True

    def curve_mapping(self, node_name, prop_name="mapping", *, curve_type="COLOR"):
        """RGB Curves 等の template_curve_mapping。"""
        node = self._node(node_name)
        if not node:
            return False
        self.layout.template_curve_mapping(node, prop_name, type=curve_type)
        return True
