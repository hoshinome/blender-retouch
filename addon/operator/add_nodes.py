import os
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

NODETREE_NAME = "BlenderRetouch_Nodes"

def _unique_data_name(base, collection):
    if base not in collection:
        return base
    i = 1
    while f"{base}.{i:03d}" in collection:
        i += 1
    return f"{base}.{i:03d}"


def _group_sort_key(name, base_name):
    if name == base_name:
        return (0, 0)
    if not name.startswith(base_name + "."):
        return (2, 0)
    suffix = name[len(base_name) + 1 :]
    try:
        return (1, int(suffix))
    except ValueError:
        return (1, 9999)


def _pick_appended_group(nodetree_name, before_names):
    after_names = set(bpy.data.node_groups.keys())
    new_names = after_names - before_names
    matches = [
        n
        for n in new_names
        if n == nodetree_name or n.startswith(nodetree_name + ".")
    ]
    if matches:
        chosen = max(matches, key=lambda n: _group_sort_key(n, nodetree_name))
        return bpy.data.node_groups[chosen]

    if nodetree_name in bpy.data.node_groups and nodetree_name not in before_names:
        return bpy.data.node_groups[nodetree_name]

    return None


def _enable_compositor(scene):
    if hasattr(scene, "compositor"):
        scene.compositor.use_nodes = True
    if hasattr(scene, "use_nodes"):
        scene.use_nodes = True


def _assign_compositing_group(scene, group_tree):
    if hasattr(scene, "compositing_node_group"):
        scene.compositing_node_group = group_tree
        return True

    if hasattr(scene, "compositor") and hasattr(scene.compositor, "node_tree"):
        _enable_compositor(scene)
        comp_tree = scene.compositor.node_tree
        if comp_tree is None:
            comp_tree = bpy.data.node_groups.new(
                name=_unique_data_name(f"{scene.name}_Compositor", bpy.data.node_groups),
                type="CompositorNodeTree",
            )
            scene.compositor.node_tree = comp_tree

        group_node = None
        for node in comp_tree.nodes:
            if node.type == "GROUP" and node.node_tree == group_tree:
                group_node = node
                break

        if group_node is None:
            group_node = comp_tree.nodes.new("CompositorNodeGroup")
            group_node.node_tree = group_tree
            group_node.label = group_tree.name
            group_node.location = (0, 0)

        _select_node_in_tree(comp_tree, group_node.name)
        return True

    if hasattr(scene, "compositor_node_tree"):
        scene.compositor_node_tree = group_tree
        return True

    return False


def _select_node_in_tree(node_tree, node_name):
    if not node_tree or node_name not in node_tree.nodes:
        return None
    for node in node_tree.nodes:
        node.select = False
    target = node_tree.nodes[node_name]
    target.select = True
    node_tree.nodes.active = target
    return target

def _focus_compositor_group(context, group_tree):
    scene = context.scene
    _enable_compositor(scene)
    _assign_compositing_group(scene, group_tree)
    _select_node_in_tree(group_tree, "Image")

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "NODE_EDITOR":
                continue
            space = area.spaces.active
            if space.type == "NODE_EDITOR":
                space.tree_type = "CompositorNodeTree"


def _iter_image_nodes(node_tree):
    if not node_tree:
        return
    for node in node_tree.nodes:
        if node.type == "IMAGE":
            yield node
        elif node.type == "GROUP" and node.node_tree:
            yield from _iter_image_nodes(node.node_tree)


def _configure_image_node(image_node):
    if hasattr(image_node, "image_user") and image_node.image_user:
        image_node.image_user.frame_duration = 1
        image_node.image_user.use_auto_refresh = True


def _load_image(operator, image_path):
    abs_path = bpy.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        operator.report({"ERROR"}, f"画像ファイルが存在しません: {abs_path}")
        return None
    try:
        return bpy.data.images.load(abs_path, check_existing=True)
    except Exception as e:
        operator.report({"ERROR"}, f"画像の読み込みに失敗: {e}")
        return None


def _append_nodetree(operator, blend_file_path, nodetree_name):
    """
    blend から BlenderRetouch_Nodes をアペンドする。
    依存グループ (BR_Color 等) も一緒に入るが、返すのは目的のグループだけ。
    """
    before = set(bpy.data.node_groups.keys())
    directory = os.path.join(blend_file_path, "NodeTree")
    inner_path = os.path.join(directory, nodetree_name)

    try:
        bpy.ops.wm.append(
            filepath=inner_path,
            directory=directory + os.sep,
            filename=nodetree_name,
        )
    except Exception as e:
        operator.report(
            {"ERROR"},
            f"アペンド失敗: node.blend 内に '{nodetree_name}' が見つかりません。エラー: {e}",
        )
        return None

    group = _pick_appended_group(nodetree_name, before)
    if group:
        return group

    if nodetree_name in bpy.data.node_groups:
        src = bpy.data.node_groups[nodetree_name]
        copy = src.copy()
        copy.name = _unique_data_name(f"{nodetree_name}_copy", bpy.data.node_groups)
        return copy

    operator.report(
        {"ERROR"},
        f"アペンド後にノードグループ '{nodetree_name}' を取得できませんでした。",
    )
    return None


def apply_retouch_to_scene(
    operator, context, image_path, blend_file_path, nodetree_name=NODETREE_NAME
):
    """
    1. BlenderRetouch_Nodes をアペンド
    2. シーンの compositing_node_group に割り当て（Blender 5.1+）
    3. グループ内の Image ノードに画像を設定
    """
    scene = context.scene
    if scene is None:
        operator.report({"ERROR"}, "アクティブなシーンがありません。")
        return None

    group_tree = _append_nodetree(operator, blend_file_path, nodetree_name)
    if group_tree is None:
        return None

    if not _assign_compositing_group(scene, group_tree):
        operator.report({"ERROR"}, "この Blender バージョンではコンポジターを割り当てできません。")
        return None

    img = _load_image(operator, image_path)
    if img is None:
        return None

    if img.size[0] > 0 and img.size[1] > 0:
        scene.render.resolution_x = img.size[0]
        scene.render.resolution_y = img.size[1]
        scene.render.resolution_percentage = 100

    image_nodes = list(_iter_image_nodes(group_tree))
    if image_nodes:
        for image_node in image_nodes:
            image_node.image = img
            _configure_image_node(image_node)
    else:
        operator.report(
            {"WARNING"},
            f"警告: '{group_tree.name}' の中に Image ノードが見つかりませんでした。",
        )

    _focus_compositor_group(context, group_tree)
    return scene


class RETOUCH_OT_add_nodes(Operator, ImportHelper):
    bl_idname = "retouch.add_nodes"
    bl_label = ""
    bl_description = ("Add nodes")

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.exr",
        options={"HIDDEN"},
        maxlen=255,
    )

    filepath: StringProperty(
        name="File Path",
        description="選択された画像のパス",
        maxlen=1024,
        default="",
    )

    def execute(self, context):
        image_path = self.filepath
        if not image_path:
            self.report({"ERROR"}, "画像が選択されていません。")
            return {"CANCELLED"}

        current_dir = os.path.dirname(os.path.realpath(__file__))
        addon_dir = os.path.dirname(current_dir)
        blend_file_path = os.path.join(addon_dir, "assets", "node.blend")

        if not os.path.exists(blend_file_path):
            self.report({"ERROR"}, f"Template blend file not found: {blend_file_path}")
            return {"CANCELLED"}

        scene = apply_retouch_to_scene(
            self, context, image_path, blend_file_path, NODETREE_NAME
        )
        if scene is None:
            return {"CANCELLED"}

        try:
            scene.render.compositor_device = "GPU"
        except (AttributeError, TypeError):
            pass

        self.report(
            {"INFO"},
            f"シーン '{scene.name}' に '{NODETREE_NAME}' を適用しました",
        )
        return {"FINISHED"}


classes = (
    RETOUCH_OT_add_nodes,
)