import os
import bpy

NODETREE_NAME = "BlenderRetouch_Nodes"


def _unique_data_name(base: str, collection) -> str:
    if base not in collection:
        return base
    i = 1
    while f"{base}.{i:03d}" in collection:
        i += 1
    return f"{base}.{i:03d}"


def _group_sort_key(name: str, base: str) -> tuple:
    if name == base:
        return (0, 0)
    if not name.startswith(base + "."):
        return (2, 0)
    try:
        return (1, int(name[len(base) + 1:]))
    except ValueError:
        return (1, 9999)


def _pick_appended_group(nodetree_name: str, before_names: set):
    new_names = set(bpy.data.node_groups.keys()) - before_names
    matches = [n for n in new_names
               if n == nodetree_name or n.startswith(nodetree_name + ".")]
    if matches:
        return bpy.data.node_groups[max(matches, key=lambda n: _group_sort_key(n, nodetree_name))]
    if nodetree_name in bpy.data.node_groups and nodetree_name not in before_names:
        return bpy.data.node_groups[nodetree_name]
    return None


def _enable_compositor(scene) -> None:
    if hasattr(scene, "compositor"):
        scene.compositor.use_nodes = True
    if hasattr(scene, "use_nodes"):
        scene.use_nodes = True


def _assign_compositing_group(scene, group_tree) -> bool:
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

        group_node = next(
            (n for n in comp_tree.nodes if n.type == "GROUP" and n.node_tree == group_tree),
            None,
        )
        if group_node is None:
            group_node = comp_tree.nodes.new("CompositorNodeGroup")
            group_node.node_tree = group_tree
            group_node.label = group_tree.name
            group_node.location = (0, 0)

        _select_node(comp_tree, group_node.name)
        return True

    if hasattr(scene, "compositor_node_tree"):
        scene.compositor_node_tree = group_tree
        return True

    return False


def _select_node(node_tree, node_name: str):
    if not node_tree or node_name not in node_tree.nodes:
        return None
    for node in node_tree.nodes:
        node.select = False
    target = node_tree.nodes[node_name]
    target.select = True
    node_tree.nodes.active = target
    return target


def _focus_compositor_group(context, group_tree) -> None:
    scene = context.scene
    _enable_compositor(scene)
    _assign_compositing_group(scene, group_tree)
    _select_node(group_tree, "Image")

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "NODE_EDITOR" and area.spaces.active.type == "NODE_EDITOR":
                area.spaces.active.tree_type = "CompositorNodeTree"


def _iter_image_nodes(node_tree):
    if not node_tree:
        return
    for node in node_tree.nodes:
        if node.type == "IMAGE":
            yield node
        elif node.type == "GROUP" and node.node_tree:
            yield from _iter_image_nodes(node.node_tree)


def _configure_image_node(image_node) -> None:
    if hasattr(image_node, "image_user") and image_node.image_user:
        image_node.image_user.frame_duration = 1
        image_node.image_user.use_auto_refresh = True


def _load_image(operator, image_path: str):
    abs_path = bpy.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        operator.report({"ERROR"}, f"Image file not found: {abs_path}")
        return None
    try:
        return bpy.data.images.load(abs_path, check_existing=True)
    except Exception as e:
        operator.report({"ERROR"}, f"Failed to load image: {e}")
        return None


def _append_nodetree(operator, blend_file_path: str, nodetree_name: str):
    before = set(bpy.data.node_groups.keys())
    directory = os.path.join(blend_file_path, "NodeTree")

    try:
        bpy.ops.wm.append(
            filepath=os.path.join(directory, nodetree_name),
            directory=directory + os.sep,
            filename=nodetree_name,
        )
    except Exception as e:
        operator.report({"ERROR"}, f"Append failed: '{nodetree_name}' not found in node.blend. ({e})")
        return None

    group = _pick_appended_group(nodetree_name, before)
    if group:
        return group

    if nodetree_name in bpy.data.node_groups:
        copy = bpy.data.node_groups[nodetree_name].copy()
        copy.name = _unique_data_name(f"{nodetree_name}_copy", bpy.data.node_groups)
        return copy

    operator.report({"ERROR"}, f"Could not retrieve node group '{nodetree_name}' after append.")
    return None


def apply_retouch_to_scene(operator, context, image_path: str,
                            blend_file_path: str, nodetree_name: str = NODETREE_NAME):
    scene = context.scene
    if scene is None:
        operator.report({"ERROR"}, "No active scene found.")
        return None

    group_tree = _append_nodetree(operator, blend_file_path, nodetree_name)
    if group_tree is None:
        return None

    if not _assign_compositing_group(scene, group_tree):
        operator.report({"ERROR"}, "Cannot assign compositor group in this Blender version.")
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
        for node in image_nodes:
            node.image = img
            _configure_image_node(node)
    else:
        operator.report({"WARNING"}, f"No Image nodes found inside '{group_tree.name}'.")

    _focus_compositor_group(context, group_tree)
    return scene