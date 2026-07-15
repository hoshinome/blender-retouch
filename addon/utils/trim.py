import bpy
import gpu
import blf
import math
from gpu_extras.batch import batch_for_shader


# ------------------------------------------------------------------
# 定数
# ------------------------------------------------------------------

HANDLE_PICK_RADIUS_PX = 10
HANDLE_DRAW_SIZE_PX = 8
ROTATE_DIAL_RADIUS_PX = 200
ROTATE_SNAP_STEP_DEG = 15.0
ROTATE_DIAL_LINE_WIDTH = 2
ROTATE_DIAL_LINE_WIDTH_INACTIVE = 1.5

ASPECT_KEY_LABELS = [
    ("1", "1:1"), ("2", "4:3"), ("3", "3:2"),
    ("4", "16:9"), ("5", "9:16"),
]


# ------------------------------------------------------------------
# ノード探索
# ------------------------------------------------------------------

def get_compositor_node_tree(scene):
    node_group = getattr(scene, "compositing_node_group", None)
    if node_group is not None:
        return node_group
    return getattr(scene, "node_tree", None)


class ImageNodeLookupError(Exception):
    pass


def find_single_image_node(node_tree):
    if node_tree is None:
        raise ImageNodeLookupError("Compositor node tree not found.")

    image_nodes = [node for node in node_tree.nodes if node.type == 'IMAGE']

    if len(image_nodes) == 0:
        raise ImageNodeLookupError("No Image node found in the compositor.")
    if len(image_nodes) > 1:
        names = ", ".join(n.name for n in image_nodes)
        raise ImageNodeLookupError(
            f"Multiple Image nodes found ({names}). "
            "Please narrow it down to a single target before running this."
        )

    return image_nodes[0]


def find_downstream_link(node_tree, image_node):
    if node_tree is None or image_node is None:
        return None
    out_socket = image_node.outputs.get("Image")
    if out_socket is None:
        return None
    for link in node_tree.links:
        if link.from_socket == out_socket:
            return (link.from_socket, link.to_socket, link)
    return None


class TransformNodeLookupError(Exception):
    pass


def get_transform_node(node_tree, image_node):
    link_info = find_downstream_link(node_tree, image_node)
    if link_info is not None:
        _, to_socket, _ = link_info
        downstream_node = to_socket.node
        if downstream_node.type == 'TRANSFORM' and downstream_node.bl_idname == "CompositorNodeTransform":
            return downstream_node

    raise TransformNodeLookupError(
        "No Transform node found directly downstream of the Image node. "
        "Please connect the Image node's output to a Transform node in the compositor first."
    )


def reset_transform_node(transform_node):
    if transform_node is None:
        return
    if 'X' in transform_node.inputs:
        transform_node.inputs['X'].default_value = 0.0
    if 'Y' in transform_node.inputs:
        transform_node.inputs['Y'].default_value = 0.0
    if 'Angle' in transform_node.inputs:
        transform_node.inputs['Angle'].default_value = 0.0


# ------------------------------------------------------------------
# 座標変換
# ------------------------------------------------------------------

def image_to_region(region, image_size, x, y):
    u = x / image_size[0]
    v = y / image_size[1]
    return region.view2d.view_to_region(u, v, clip=False)


def rotate_point_image_space(px, py, center_x, center_y, angle):
    dx = px - center_x
    dy = py - center_y
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    rx = dx * cos_a - dy * sin_a
    ry = dx * sin_a + dy * cos_a
    return (center_x + rx, center_y + ry)


def rotated_image_to_region(region, image_size, x, y, rotation):
    center_x = image_size[0] / 2.0
    center_y = image_size[1] / 2.0
    rx, ry = rotate_point_image_space(x, y, center_x, center_y, rotation)
    return image_to_region(region, image_size, rx, ry)


def get_handle_positions(region, image_size, xmin, xmax, ymin, ymax, rotation=0.0):
    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    coords = {
        'TL': (xmin, ymax), 'T': (center_x, ymax), 'TR': (xmax, ymax),
        'L': (xmin, center_y), 'R': (xmax, center_y),
        'BL': (xmin, ymin), 'B': (center_x, ymin), 'BR': (xmax, ymin),
    }
    result = {}
    for key, (x, y) in coords.items():
        result[key] = image_to_region(region, image_size, x, y)
    return result


def get_rotate_handle_position(region, image_size, xmin, xmax, ymin, ymax, rotation=0.0):
    center_x = (xmin + xmax) / 2.0
    bottom_center_screen = image_to_region(region, image_size, center_x, ymin)

    outward = -ROTATE_DIAL_RADIUS_PX * 0.75

    return (bottom_center_screen[0], bottom_center_screen[1] - outward)


def get_trim_rect_screen_corners(region, image_size, xmin, xmax, ymin, ymax, rotation=0.0):
    corners_local = [
        (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin),
    ]
    return [
        image_to_region(region, image_size, px, py)
        for px, py in corners_local
    ]


def point_in_polygon(point, polygon):
    x, y = point
    n = len(polygon)
    inside = False
    x1, y1 = polygon[0]
    for i in range(1, n + 1):
        x2, y2 = polygon[i % n]
        if y > min(y1, y2):
            if y <= max(y1, y2):
                if x <= max(x1, x2):
                    if y1 != y2:
                        x_intersect = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                    if x1 == x2 or x <= x_intersect:
                        inside = not inside
        x1, y1 = x2, y2
    return inside


def point_within_rotated_image(px, py, rotation, img_w, img_h):
    center_x = img_w / 2.0
    center_y = img_h / 2.0
    rx, ry = rotate_point_image_space(px, py, center_x, center_y, -rotation)
    return -1e-6 <= rx <= img_w + 1e-6 and -1e-6 <= ry <= img_h + 1e-6


def clamp_rect_to_image(xmin, xmax, ymin, ymax, img_w, img_h, rotation=0.0):
    if img_w <= 0 or img_h <= 0:
        return xmin, xmax, ymin, ymax

    min_size = min(16.0, img_w, img_h)
    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    half_w = (xmax - xmin) / 2.0
    half_h = (ymax - ymin) / 2.0

    if half_w <= 0 or half_h <= 0:
        return max(0.0, min(xmin, img_w)), max(0.0, min(xmax, img_w)), max(0.0, min(ymin, img_h)), max(0.0, min(ymax, img_h))

    def corners_fit_within_image(scale):
        nx_min = center_x - half_w * scale
        nx_max = center_x + half_w * scale
        ny_min = center_y - half_h * scale
        ny_max = center_y + half_h * scale
        corners = [(nx_min, ny_min), (nx_max, ny_min), (nx_max, ny_max), (nx_min, ny_max)]
        return all(point_within_rotated_image(cx, cy, rotation, img_w, img_h) for cx, cy in corners)

    if corners_fit_within_image(1.0):
        scale = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if corners_fit_within_image(mid):
                lo = mid
            else:
                hi = mid
        scale = lo

    # 最低サイズを下回らないように保護
    min_scale_w = min_size / (half_w * 2) if half_w > 0 else 1.0
    min_scale_h = min_size / (half_h * 2) if half_h > 0 else 1.0
    scale = max(scale, min_scale_w, min_scale_h)

    new_half_w = half_w * scale
    new_half_h = half_h * scale
    return (
        center_x - new_half_w, center_x + new_half_w,
        center_y - new_half_h, center_y + new_half_h,
    )


def clamp_move_to_image(xmin, xmax, ymin, ymax, img_w, img_h, rotation=0.0):
    if img_w <= 0 or img_h <= 0:
        return xmin, xmax, ymin, ymax

    width = xmax - xmin
    height = ymax - ymin

    if rotation == 0.0:
        new_xmin, new_xmax = xmin, xmax
        new_ymin, new_ymax = ymin, ymax
        if new_xmin < 0:
            new_xmin, new_xmax = 0.0, width
        if new_xmax > img_w:
            new_xmax, new_xmin = img_w, img_w - width
        if new_ymin < 0:
            new_ymin, new_ymax = 0.0, height
        if new_ymax > img_h:
            new_ymax, new_ymin = img_h, img_h - height
        return new_xmin, new_xmax, new_ymin, new_ymax

    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    half_w = width / 2.0
    half_h = height / 2.0
    img_center_x = img_w / 2.0
    img_center_y = img_h / 2.0

    def fits_at_center(cx, cy):
        corners = [
            (cx - half_w, cy - half_h), (cx + half_w, cy - half_h),
            (cx + half_w, cy + half_h), (cx - half_w, cy + half_h),
        ]
        return all(point_within_rotated_image(px, py, rotation, img_w, img_h) for px, py in corners)

    if fits_at_center(center_x, center_y):
        return center_x - half_w, center_x + half_w, center_y - half_h, center_y + half_h

    if not fits_at_center(img_center_x, img_center_y):
        return clamp_rect_to_image(
            img_center_x - half_w, img_center_x + half_w,
            img_center_y - half_h, img_center_y + half_h,
            img_w, img_h, rotation,
        )

    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        test_x = img_center_x + (center_x - img_center_x) * mid
        test_y = img_center_y + (center_y - img_center_y) * mid
        if fits_at_center(test_x, test_y):
            lo = mid
        else:
            hi = mid

    new_center_x = img_center_x + (center_x - img_center_x) * lo
    new_center_y = img_center_y + (center_y - img_center_y) * lo

    return (
        new_center_x - half_w, new_center_x + half_w,
        new_center_y - half_h, new_center_y + half_h,
    )


def clamp_resize_to_image(xmin, xmax, ymin, ymax, anchor_x, anchor_y, img_w, img_h, rotation=0.0, min_size=16.0):
    if img_w <= 0 or img_h <= 0:
        return xmin, xmax, ymin, ymax

    width = xmax - xmin
    height = ymax - ymin

    if width <= 0 or height <= 0:
        return max(0.0, min(xmin, img_w)), max(0.0, min(xmax, img_w)), max(0.0, min(ymin, img_h)), max(0.0, min(ymax, img_h))

    corners = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]

    def scaled_corners(scale):
        return [(anchor_x + (cx - anchor_x) * scale, anchor_y + (cy - anchor_y) * scale) for cx, cy in corners]

    def corners_fit_within_image(scale):
        pts = scaled_corners(scale)
        return all(point_within_rotated_image(nx, ny, rotation, img_w, img_h) for nx, ny in pts)

    if corners_fit_within_image(1.0):
        scale = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if corners_fit_within_image(mid):
                lo = mid
            else:
                hi = mid
        scale = lo

    # 相似縮小時も最低サイズを死守する
    min_scale_w = min_size / width if width > 0 else 1.0
    min_scale_h = min_size / height if height > 0 else 1.0
    scale = max(scale, min_scale_w, min_scale_h)

    pts = scaled_corners(scale)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


# ------------------------------------------------------------------
# 描画
# ------------------------------------------------------------------

def draw_custom_image(op, region):
    rotation = getattr(op, "rotation", 0.0)
    if op._image is None or op._image_gpu_texture is None:
        return
    image_size = op._image_size
    try:
        bg_color = bpy.context.preferences.themes[0].image_editor.space.back[:3]
    except Exception:
        bg_color = (0.11, 0.11, 0.11)
    gpu.state.blend_set('NONE')
    op.shader.bind()
    bg_rect = (
        (0.0, 0.0), (region.width, 0.0),
        (region.width, region.height), (0.0, region.height),
    )
    bg_batch = batch_for_shader(op.shader, 'TRI_FAN', {"pos": bg_rect})
    op.shader.uniform_float("color", (bg_color[0], bg_color[1], bg_color[2], 1.0))
    bg_batch.draw(op.shader)

    corners_local = [
        (0.0, image_size[1]), (image_size[0], image_size[1]),
        (image_size[0], 0.0), (0.0, 0.0),
    ]
    positions = [rotated_image_to_region(region, image_size, px, py, rotation) for px, py in corners_local]
    uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]

    op.image_shader.bind()
    op.image_shader.uniform_sampler("image", op._image_gpu_texture)
    op.image_shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
    image_batch = batch_for_shader(op.image_shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
    image_batch.draw(op.image_shader)


def draw_callback_px(op, context):
    try:
        region = op._region
        if region is None:
            return

        image_size = op._image_size
        rotation = getattr(op, "rotation", 0.0)
        dxmin, dxmax, dymin, dymax = op._get_display_rect()

        draw_custom_image(op, region)

        p_tl, p_tr, p_br, p_bl = get_trim_rect_screen_corners(
            region, image_size, dxmin, dxmax, dymin, dymax, rotation
        )

        gpu.state.blend_set('ALPHA')

        op.shader.bind()
        fill_batch = batch_for_shader(op.shader, 'TRI_FAN', {"pos": (p_bl, p_br, p_tr, p_tl)})
        op.shader.uniform_float("color", (0.0, 0.0, 0.0, 0.15))
        fill_batch.draw(op.shader)

        gpu.state.line_width_set(2.0)
        outline_batch = batch_for_shader(op.shader, 'LINE_LOOP', {"pos": (p_bl, p_br, p_tr, p_tl)})
        op.shader.uniform_float("color", (1.0, 1.0, 1.0, 0.9))
        outline_batch.draw(op.shader)

        if op.active_handle == 'ROTATE':
            draw_trim_grid(op.shader, p_tl, p_tr, p_br, p_bl, mode='FINE')
        elif op.active_handle is not None:
            draw_trim_grid(op.shader, p_tl, p_tr, p_br, p_bl, mode='COARSE')

        handle_positions = get_handle_positions(region, image_size, dxmin, dxmax, dymin, dymax, rotation)
        half = HANDLE_DRAW_SIZE_PX / 2.0
        for key, (hx, hy) in handle_positions.items():
            is_active = (key == op.active_handle)
            color = (1.0, 0.6, 0.0, 1.0) if is_active else (1.0, 1.0, 1.0, 1.0)
            square = (
                (hx - half, hy - half), (hx + half, hy - half),
                (hx + half, hy + half), (hx - half, hy + half),
            )
            handle_batch = batch_for_shader(op.shader, 'TRI_FAN', {"pos": square})
            op.shader.uniform_float("color", color)
            handle_batch.draw(op.shader)

        rotate_pos = get_rotate_handle_position(region, image_size, dxmin, dxmax, dymin, dymax, rotation)
        is_rotating = (op.active_handle == 'ROTATE')

        # クロップ枠の左下角のY座標(枠の下端ライン)を取得して渡す
        trim_bottom_y = p_bl[1]
        draw_rotate_dial(op.shader, rotate_pos, rotation, is_rotating, trim_bottom_y)

        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')

        if is_rotating:
            draw_rotation_angle_label(region, rotate_pos, rotation)

        draw_aspect_ratio_hud(op, region)

    except ReferenceError:
        try:
            gpu.state.blend_set('NONE')
        except Exception:
            pass
        return


def _grid_lines_at(p_tl, p_tr, p_br, p_bl, divisions):
    lines = []
    for i in range(1, divisions):
        t = i / divisions
        top_x = p_tl[0] + (p_tr[0] - p_tl[0]) * t
        top_y = p_tl[1] + (p_tr[1] - p_tl[1]) * t
        bottom_x = p_bl[0] + (p_br[0] - p_bl[0]) * t
        bottom_y = p_bl[1] + (p_br[1] - p_bl[1]) * t
        lines.append((top_x, top_y))
        lines.append((bottom_x, bottom_y))

        left_x = p_tl[0] + (p_bl[0] - p_tl[0]) * t
        left_y = p_tl[1] + (p_bl[1] - p_tl[1]) * t
        right_x = p_tr[0] + (p_br[0] - p_tr[0]) * t
        right_y = p_tr[1] + (p_br[1] - p_tr[1]) * t
        lines.append((left_x, left_y))
        lines.append((right_x, right_y))
    return lines


def draw_trim_grid(shader, p_tl, p_tr, p_br, p_bl, mode='COARSE'):
    if mode == 'FINE':
        # 回転中: 9分割の細かいグリッド
        lines = _grid_lines_at(p_tl, p_tr, p_br, p_bl, 9)
        if not lines:
            return
        gpu.state.line_width_set(1.0)
        grid_batch = batch_for_shader(shader, 'LINES', {"pos": lines})
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.3))
        grid_batch.draw(shader)
    else:
        # 移動/リサイズ中: 3分割の太線グリッド
        lines = _grid_lines_at(p_tl, p_tr, p_br, p_bl, 3)
        if not lines:
            return
        gpu.state.line_width_set(1.5)
        grid_batch = batch_for_shader(shader, 'LINES', {"pos": lines})
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.35))
        grid_batch.draw(shader)


def draw_rotate_dial(shader, center, rotation, is_active, trim_bottom_y):
    cx, cy = center
    r = ROTATE_DIAL_RADIUS_PX
    half_segments = 24

    rotation_deg = math.degrees(rotation)

    gpu.state.blend_set('ALPHA')

    # 中心からクロップ下端までのY軸の距離
    dy = trim_bottom_y - cy

    # 円の下半分がすべてクロップ枠内にある場合は何も描画しない
    if dy <= -r:
        gpu.state.blend_set('NONE')
        return

    if dy >= 0:
        # クロップ枠が円の中心より上にある場合は、通常通り下半分(180度)を描画
        theta_start = math.pi
        theta_end = 2.0 * math.pi
    else:
        # 円がクロップ枠の境界に交差する場合、計算して枠の外に出ている弧だけを描画する
        dx = math.sqrt(r**2 - dy**2)

        ts = math.atan2(dy, -dx)
        te = math.atan2(dy, dx)
        theta_start = ts if ts >= 0 else ts + 2 * math.pi
        theta_end = te if te >= 0 else te + 2 * math.pi

    def angle_at(t):
        return theta_start + (theta_end - theta_start) * t

    # アーチの描画
    ring_pts = [
        (cx + r * math.cos(angle_at(i / half_segments)), cy + r * math.sin(angle_at(i / half_segments)))
        for i in range(half_segments + 1)
    ]
    gpu.state.line_width_set(ROTATE_DIAL_LINE_WIDTH if is_active else ROTATE_DIAL_LINE_WIDTH_INACTIVE)
    ring_batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": ring_pts})
    ring_alpha = 0.7 if is_active else 0.4
    shader.uniform_float("color", (1.0, 1.0, 1.0, ring_alpha))
    ring_batch.draw(shader)

    def draw_dot(pos, radius, color):
        px, py = pos
        pts = []
        segs = 8
        for i in range(segs):
            a = (i / segs) * 2 * math.pi
            pts.append((px + radius * math.cos(a), py + radius * math.sin(a)))
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pts})
        shader.uniform_float("color", color)
        batch.draw(shader)

    # 目盛りの描画
    for deg in range(0, 360, 15):
        theta = -math.pi / 2.0 + math.radians(deg - rotation_deg)
        dot_pos = (cx + r * math.cos(theta), cy + r * math.sin(theta))

        # ドットのY座標がクロップ枠より上（内側）なら描画をスキップ
        if dot_pos[1] >= trim_bottom_y:
            continue

        is_major = (deg % 90 == 0)
        if is_major:
            draw_dot(dot_pos, 1.6, (1.0, 1.0, 1.0, 0.7 if is_active else 0.45))
        else:
            draw_dot(dot_pos, 1.1, (1.0, 1.0, 1.0, 0.45 if is_active else 0.25))

    # 一番下の基準インジケーター（枠より外にある場合のみ描画）
    indicator_color = (1.0, 0.6, 0.0, 1.0) if is_active else (1.0, 1.0, 1.0, 0.85)
    marker_pos = (cx, cy - r)
    if marker_pos[1] < trim_bottom_y:
        draw_dot(marker_pos, 2.5, indicator_color)

    gpu.state.blend_set('NONE')


def draw_rotation_angle_label(region, center, rotation):
    font_id = 0
    rotation_deg = math.degrees(rotation)
    text = f"{rotation_deg:.1f}°"
    blf.size(font_id, 15)
    text_w, text_h = blf.dimensions(font_id, text)
    x = center[0] - text_w / 2.0
    y = center[1] - ROTATE_DIAL_RADIUS_PX - 22.0
    blf.color(font_id, 1.0, 1.0, 1.0, 0.95)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, text)


def draw_aspect_ratio_hud(op, region):
    font_id = 0
    x = 12
    y = region.height - 24
    line_height = 18
    blf.size(font_id, 13)

    enum_to_key = {'1_1': '1', '4_3': '2', '3_2': '3', '16_9': '4', '9_16': '5'}
    current = getattr(op, "aspect_ratio_enum", '3_2')
    active_key = enum_to_key.get(current)

    label_map = dict(ASPECT_KEY_LABELS)
    current_label = "Custom" if current == 'CUSTOM' else label_map.get(active_key, "")

    blf.color(font_id, 1.0, 1.0, 1.0, 0.95)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, f"Aspect Ratio: {current_label}")
    y -= line_height

    for key, label in ASPECT_KEY_LABELS:
        is_active = (key == active_key)
        if is_active:
            blf.color(font_id, 1.0, 0.75, 0.2, 1.0)
        else:
            blf.color(font_id, 1.0, 1.0, 1.0, 0.65)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, f"{key}: {label}")
        y -= line_height

    # y -= 4
    # rotation_deg = math.degrees(getattr(op, "rotation", 0.0))
    # blf.color(font_id, 1.0, 1.0, 1.0, 0.95)
    # blf.position(font_id, x, y, 0)
    # blf.draw(font_id, f"Rotation: {rotation_deg:.1f}°  (drag compass, Shift=snap 15°)")
