import bpy
import os

NODETREE_NAME = "BlenderRetouch_Nodes"


def create_compositor_nodes(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    tree = bpy.data.node_groups.new("Compositor Nodes", "CompositorNodeTree")
    scene.compositing_node_group = tree
    scene.render.use_compositing = True
    return tree


def ensure_compositor_nodes(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    if scene.compositing_node_group is None:
        return create_compositor_nodes(scene)
    scene.render.use_compositing = True
    return scene.compositing_node_group


def get_or_create_node(
    node_tree: bpy.types.NodeTree,
    node_type: str,
    name: str,
    location: tuple[float, float] = (0.0, 0.0),
) -> bpy.types.Node:
    node = node_tree.nodes.get(name)
    if node is None:
        node = node_tree.nodes.new(type=node_type)
        node.name = name
        node.label = name
        node.location = location
    return node


def find_or_create_image_node(node_tree: bpy.types.NodeTree, image_name: str) -> bpy.types.Node:
    for node in node_tree.nodes:
        if node.type == "IMAGE" and node.name == image_name:
            return node
    return get_or_create_node(node_tree, "CompositorNodeImage", image_name, (-400, 200))


def link_if_missing(
    node_tree: bpy.types.NodeTree,
    from_socket: bpy.types.NodeSocket,
    to_socket: bpy.types.NodeSocket,
) -> None:
    exists = any(lk.from_socket == from_socket and lk.to_socket == to_socket for lk in node_tree.links)
    if not exists:
        node_tree.links.new(from_socket, to_socket)


def connect_to_outputs(node_tree: bpy.types.NodeTree, out_socket: bpy.types.NodeSocket) -> None:
    group_out = next((n for n in node_tree.nodes if n.type == "GROUP_OUTPUT"), None)
    if group_out is None:
        group_out = node_tree.nodes.new(type="NodeGroupOutput")
        group_out.location = (500, 200)

    socket_names = [s.name for s in node_tree.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "OUTPUT"]
    if "Image" not in socket_names:
        node_tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")

    if "Image" in group_out.inputs:
        link_if_missing(node_tree, out_socket, group_out.inputs["Image"])

    viewer = next((n for n in node_tree.nodes if n.type == "VIEWER"), None)
    if viewer is None:
        viewer = node_tree.nodes.new(type="CompositorNodeViewer")
        viewer.location = (500, 0)

    if "Image" in viewer.inputs:
        link_if_missing(node_tree, out_socket, viewer.inputs["Image"])


def set_scene_resolution(scene: bpy.types.Scene, image: bpy.types.Image) -> None:
    width, height = image.size
    if width <= 0 or height <= 0:
        return
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0


def get_image_from_active_or_linked(node_tree: bpy.types.NodeTree | None) -> bpy.types.Image | None:
    if not node_tree:
        return None

    active = node_tree.nodes.active
    if active and active.type == "IMAGE" and active.image:
        return active.image

    for node in node_tree.nodes:
        if node.select and node.type == "IMAGE" and node.image:
            return node.image

    output_types = {"COMPOSITE", "VIEWER", "GROUP_OUTPUT"}
    for link in node_tree.links:
        if link.to_node.type in output_types and link.from_node.type == "IMAGE":
            if link.from_node.image:
                return link.from_node.image

    for node in node_tree.nodes:
        if node.type == "IMAGE" and node.image:
            return node.image

    return None


def _pick_appended_group(nodetree_name: str, before_names: set[str]) -> bpy.types.NodeTree | None:
    current_names = set(bpy.data.node_groups.keys())
    new_names = current_names - before_names

    matches = [n for n in new_names if n == nodetree_name or n.startswith(f"{nodetree_name}.")]
    if matches:

        def sort_key(name: str) -> tuple[int, int]:
            if name == nodetree_name:
                return (0, 0)
            try:
                suffix = name[len(nodetree_name) + 1 :]
                return (1, int(suffix))
            except ValueError:
                return (1, 9999)

        target_name = max(matches, key=sort_key)
        return bpy.data.node_groups.get(target_name)

    if nodetree_name in bpy.data.node_groups and nodetree_name not in before_names:
        return bpy.data.node_groups[nodetree_name]
    return None


def _assign_compositing_group(scene: bpy.types.Scene, group_tree: bpy.types.NodeTree) -> bool:
    if hasattr(scene, "compositing_node_group"):
        scene.compositing_node_group = group_tree
        return True
    return False


def _select_node(node_tree: bpy.types.NodeTree, node_name: str) -> bpy.types.Node | None:
    if not node_tree or node_name not in node_tree.nodes:
        return None
    for node in node_tree.nodes:
        node.select = False
    target = node_tree.nodes[node_name]
    target.select = True
    node_tree.nodes.active = target
    return target


def _focus_compositor_group(context: bpy.types.Context, group_tree: bpy.types.NodeTree) -> None:
    scene = context.scene
    _assign_compositing_group(scene, group_tree)
    _select_node(group_tree, "Image")

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "NODE_EDITOR" and area.spaces.active.type == "NODE_EDITOR":
                area.spaces.active.tree_type = "CompositorNodeTree"


def _iter_image_nodes(node_tree: bpy.types.NodeTree):
    if not node_tree:
        return
    for node in node_tree.nodes:
        if node.type == "IMAGE":
            yield node
        elif node.type == "GROUP" and node.node_tree:
            yield from _iter_image_nodes(node.node_tree)


def _configure_image_node(image_node: bpy.types.Node) -> None:
    if hasattr(image_node, "image_user") and image_node.image_user:
        image_node.image_user.frame_duration = 1
        image_node.image_user.use_auto_refresh = True


def _load_image(operator: bpy.types.Operator, image_path: str) -> bpy.types.Image | None:
    abs_path = bpy.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        operator.report({"ERROR"}, f"Image file not found: {abs_path}")
        return None
    try:
        return bpy.data.images.load(abs_path, check_existing=True)
    except Exception as e:
        operator.report({"ERROR"}, f"Failed to load image: {e}")
        return None


def _append_nodetree(operator: bpy.types.Operator, blend_file_path: str, nodetree_name: str) -> bpy.types.NodeTree | None:
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
        base = f"{nodetree_name}_copy"
        name = base
        i = 1
        while name in bpy.data.node_groups:
            name = f"{base}.{i:03d}"
            i += 1
        copy.name = name
        return copy

    operator.report({"ERROR"}, f"Could not retrieve node group '{nodetree_name}' after append.")
    return None


def apply_retouch_to_scene(
    operator: bpy.types.Operator,
    context: bpy.types.Context,
    image_path: str,
    blend_file_path: str,
    nodetree_name: str = NODETREE_NAME,
) -> bpy.types.Scene | None:
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

    set_scene_resolution(scene, img)

    image_nodes = list(_iter_image_nodes(group_tree))
    if image_nodes:
        for node in image_nodes:
            node.image = img
            _configure_image_node(node)
    else:
        operator.report({"WARNING"}, f"No Image nodes found inside '{group_tree.name}'.")

    _focus_compositor_group(context, group_tree)
    return scene
