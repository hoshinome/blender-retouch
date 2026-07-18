from __future__ import annotations

import math

import bpy
import gpu
from bpy.types import Operator

from ..utils.trim import (
    HANDLE_PICK_RADIUS_PX,
    ROTATE_DIAL_RADIUS_PX,
    ROTATE_SNAP_STEP_DEG,
    ImageNodeLookupError,
    ImageSize,
    Rect,
    TransformNodeLookupError,
    clamp_move_to_image,
    clamp_rect_to_image,
    clamp_resize_to_image,
    compute_transform_offset,
    draw_callback_px,
    find_single_image_node,
    get_compositor_node_tree,
    get_handle_positions,
    get_rotate_handle_position,
    get_transform_node,
    get_trim_rect_screen_corners,
    image_to_region,
    point_in_polygon,
    reset_transform_node,
)

# ------------------------------------------------------------------
# 「前回のトリム位置を記憶する」ためのモジュールレベルキャッシュ。
#
# .blend ファイルやシーンには保存せず、同一 Blender セッション内で
# 「同じ画像に対してもう一度このオペレーターを起動したら、前回終了時点の
# トリム範囲・回転角度を復元する」ことだけを目的としたプロセス内メモリ。
#
# キーは画像名 (Image.name)。同名だがサイズが異なる別画像を誤って復元
# しないよう、画像サイズも一緒に保存し、サイズが一致する場合のみ復元する。
# ------------------------------------------------------------------
_last_trim_cache: dict[str, dict] = {}


def _store_last_trim(image_name: str, rect: Rect, rotation: float, image_size: ImageSize) -> None:
    _last_trim_cache[image_name] = {
        "rect": rect.as_tuple(),
        "rotation": rotation,
        "image_size": tuple(image_size),
    }


def _get_last_trim(image_name: str, image_size: ImageSize):
    cached = _last_trim_cache.get(image_name)
    if cached is None:
        return None
    if tuple(cached["image_size"]) != tuple(image_size):
        # 画像がリサイズ・差し替えされていた場合は古いキャッシュを信用しない
        return None
    xmin, xmax, ymin, ymax = cached["rect"]
    return Rect(xmin, xmax, ymin, ymax), cached["rotation"]


class RETOUCH_OT_image_trim(Operator):
    bl_idname = "retouch.image_trim"
    bl_label = "Image Trim"
    bl_description = "Trims the image by adjusting the Transform node and render resolution"

    _is_running = False

    xmin: bpy.props.IntProperty(name="X Min")
    xmax: bpy.props.IntProperty(name="X Max")
    ymin: bpy.props.IntProperty(name="Y Min")
    ymax: bpy.props.IntProperty(name="Y Max")

    # revert_to_original: bpy.props.BoolProperty(
    #     name="Revert to Original",
    #     description="Cancel the trim and restore the original Transform/resolution",
    #     default=False,
    #     update=revert_update,
    # )

    aspect_ratio_enum: bpy.props.EnumProperty(
        name="Aspect Ratio",
        description="Aspect ratio to lock while dragging",
        items=[
            ("1_1", "1:1", "Square"),
            ("4_3", "4:3", "4:3"),
            ("3_2", "3:2", "3:2"),
            ("16_9", "16:9", "16:9"),
            ("9_16", "9:16", "9:16 (Portrait)"),
            ("CUSTOM", "Custom", "Specify a custom ratio"),
        ],
        default="3_2",
    )
    aspect_ratio_custom_w: bpy.props.FloatProperty(
        name="W",
        description="Custom ratio width",
        default=1.0,
        min=0.0001,
    )
    aspect_ratio_custom_h: bpy.props.FloatProperty(
        name="H",
        description="Custom ratio height",
        default=1.0,
        min=0.0001,
    )

    rotation: bpy.props.FloatProperty(
        name="Rotation",
        description="Rotation angle of the image (applied to the Transform node's Angle)",
        default=0.0,
        subtype="ANGLE",
    )

    _draw_handler = None
    shader = None
    _area = None
    _region = None
    _image_size: ImageSize = ImageSize(1, 1)
    _image = None
    _original_size: ImageSize | None = None
    _original_render_res: tuple[int, int] | None = None
    _original_render_percentage: int | None = None
    _transform_node_name: str | None = None

    active_handle: str | None = None
    drag_start_mouse: tuple[float, float] = (0, 0)
    drag_start_rect: Rect | None = None
    drag_start_rotation = 0.0
    drag_start_angle = 0.0

    @classmethod
    def poll(cls, context):
        # 実行中でない場合のみ起動可能にする
        return context.area.type == "IMAGE_EDITOR" and not cls._is_running

    def _get_aspect_ratio(self) -> tuple[float, float] | None:
        preset_map = {
            "1_1": (1.0, 1.0),
            "4_3": (4.0, 3.0),
            "3_2": (3.0, 2.0),
            "16_9": (16.0, 9.0),
            "9_16": (9.0, 16.0),
        }
        if self.aspect_ratio_enum == "CUSTOM":
            if self.aspect_ratio_custom_w <= 0 or self.aspect_ratio_custom_h <= 0:
                return None
            return (self.aspect_ratio_custom_w, self.aspect_ratio_custom_h)
        return preset_map.get(self.aspect_ratio_enum)

    def _current_rect(self) -> Rect:
        return Rect(self.xmin, self.xmax, self.ymin, self.ymax)

    def _set_rect(self, rect: Rect) -> None:
        self.xmin = int(round(rect.xmin))
        self.xmax = int(round(rect.xmax))
        self.ymin = int(round(rect.ymin))
        self.ymax = int(round(rect.ymax))

    def _get_display_rect(self) -> Rect:
        return clamp_rect_to_image(self._current_rect(), self._image_size, self.rotation)

    def _apply_aspect_to_current_rect(self) -> None:
        aspect = self._get_aspect_ratio()
        if aspect is None:
            return

        ratio_w, ratio_h = aspect
        rect = self._current_rect()
        center_x, center_y = rect.center

        area = max(rect.width * rect.height, 1.0)

        new_width = (area * ratio_w / ratio_h) ** 0.5
        new_height = new_width * (ratio_h / ratio_w)

        img_w, img_h = self._image_size
        if new_width > img_w or new_height > img_h:
            scale = min(img_w / new_width, img_h / new_height)
            new_width *= scale
            new_height *= scale

        new_rect = Rect(
            center_x - new_width / 2.0,
            center_x + new_width / 2.0,
            center_y - new_height / 2.0,
            center_y + new_height / 2.0,
        )
        new_rect = clamp_rect_to_image(new_rect, self._image_size, self.rotation)
        self._set_rect(new_rect)

    def _set_aspect_ratio(self, region, mouse_pos, new_enum_value: str) -> None:
        self.aspect_ratio_enum = new_enum_value
        self._apply_aspect_to_current_rect()
        if self.active_handle is not None:
            self.drag_start_mouse = mouse_pos
            self.drag_start_rect = self._current_rect()

    def _handle_at_mouse(self, region, mouse_pos):
        mx, my = mouse_pos
        rect = self._get_display_rect()

        handle_positions = get_handle_positions(region, self._image_size, rect)
        closest_key = None
        closest_dist = HANDLE_PICK_RADIUS_PX

        for key, (hx, hy) in handle_positions.items():
            dist = ((hx - mx) ** 2 + (hy - my) ** 2) ** 0.5
            if dist <= closest_dist:
                closest_dist = dist
                closest_key = key

        if closest_key is not None:
            return closest_key

        rotate_pos = get_rotate_handle_position(region, self._image_size, rect)
        dist = ((rotate_pos[0] - mx) ** 2 + (rotate_pos[1] - my) ** 2) ** 0.5

        if abs(dist - ROTATE_DIAL_RADIUS_PX) <= 15 and my <= rotate_pos[1]:
            return "ROTATE"

        corners_screen = get_trim_rect_screen_corners(region, self._image_size, rect)
        if point_in_polygon(mouse_pos, corners_screen):
            return "MOVE"

        return None

    def invoke(self, context, event):
        self.__class__._is_running = True  # 起動フラグON

        scene = context.scene
        node_tree = get_compositor_node_tree(scene)

        try:
            image_node = find_single_image_node(node_tree)
        except ImageNodeLookupError as err:
            self.report({"ERROR"}, str(err))
            self.__class__._is_running = False
            return {"CANCELLED"}

        image = image_node.image
        if image is None:
            self.report({"ERROR"}, "No image is assigned to the Image node.")
            self.__class__._is_running = False
            return {"CANCELLED"}

        image_size = ImageSize(*image.size[:])
        self._original_size = image_size
        self._original_render_res = (scene.render.resolution_x, scene.render.resolution_y)
        self._original_render_percentage = scene.render.resolution_percentage
        self._transform_node_name = None

        self._image_size = image_size
        self._image = image
        self._area = context.area
        self._region = context.region
        self.active_handle = None

        try:
            transform_node = get_transform_node(node_tree, image_node)
            if "Angle" in transform_node.inputs:
                self.rotation = transform_node.inputs["Angle"].default_value
            else:
                self.rotation = 0.0
        except TransformNodeLookupError:
            self.rotation = 0.0

        last_trim = _get_last_trim(image.name, image_size)
        if last_trim is not None:
            restored_rect, restored_rotation = last_trim
            self._set_rect(restored_rect)
            self.rotation = restored_rotation
        else:
            self.xmin = 0
            self.ymin = 0
            self.xmax = image_size.width
            self.ymax = image_size.height

        clamped = clamp_rect_to_image(self._current_rect(), image_size, self.rotation)
        self._set_rect(clamped)

        if last_trim is None:
            self._apply_aspect_to_current_rect()

        self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self.image_shader = gpu.shader.from_builtin("IMAGE_COLOR_SCENE_LINEAR_TO_REC709_SRGB")
        try:
            self._image_gpu_texture = gpu.texture.from_image(self._image)
        except Exception:
            self._image_gpu_texture = None

        args = (self, context)
        self._draw_handler = bpy.types.SpaceImageEditor.draw_handler_add(draw_callback_px, args, "WINDOW", "POST_PIXEL")

        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._area:
            self._area.tag_redraw()

        pass_through_types = {
            "MIDDLEMOUSE",
            "WHEELUPMOUSE",
            "WHEELDOWNMOUSE",
            "NDOF_PAN",
            "NDOF_ORBIT",
            "NDOF_BUTTON_FIT",
            "TRACKPADPAN",
            "TRACKPADZOOM",
        }
        if event.type in pass_through_types or (event.type in {"NUMPAD_PLUS", "NUMPAD_MINUS"} and event.value == "PRESS"):
            return {"PASS_THROUGH"}

        region = self._region
        mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        if self.active_handle is None:
            hovered = self._handle_at_mouse(region, mouse_pos)
            cursor_map = {
                "TL": "MOVE_X",
                "TR": "MOVE_X",
                "BL": "MOVE_X",
                "BR": "MOVE_X",
                "T": "MOVE_Y",
                "B": "MOVE_Y",
                "L": "MOVE_X",
                "R": "MOVE_X",
                "MOVE": "SCROLL_XY",
                "ROTATE": "KNIFE",
                None: "DEFAULT",
            }
            context.window.cursor_set(cursor_map.get(hovered, "DEFAULT"))

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hovered = self._handle_at_mouse(region, mouse_pos)
            if hovered is not None:
                self.active_handle = hovered
                self.drag_start_mouse = mouse_pos
                self.drag_start_rect = self._current_rect()
                if hovered == "ROTATE":
                    self.drag_start_rotation = self.rotation
                    self.drag_start_angle = self._angle_from_center(region, mouse_pos)
                return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"}

        elif event.type == "MOUSEMOVE":
            if self.active_handle == "ROTATE":
                self._apply_rotation_drag(region, mouse_pos, event.shift)
                return {"RUNNING_MODAL"}
            if self.active_handle is not None:
                self._apply_drag(region, mouse_pos)
                return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"}

        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if self.active_handle is not None:
                self.active_handle = None
            return {"RUNNING_MODAL"}

        elif event.type in {"RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            self._finish(context, cancelled=False)
            return self.execute(context)
        elif event.type in {"RIGHTMOUSE", "ESC"}:
            return self._finish(context, cancelled=True)

        elif event.type in {"ONE", "NUMPAD_1"} and event.value == "PRESS":
            self._set_aspect_ratio(region, mouse_pos, "1_1")
            return {"RUNNING_MODAL"}
        elif event.type in {"TWO", "NUMPAD_2"} and event.value == "PRESS":
            self._set_aspect_ratio(region, mouse_pos, "4_3")
            return {"RUNNING_MODAL"}
        elif event.type in {"THREE", "NUMPAD_3"} and event.value == "PRESS":
            self._set_aspect_ratio(region, mouse_pos, "3_2")
            return {"RUNNING_MODAL"}
        elif event.type in {"FOUR", "NUMPAD_4"} and event.value == "PRESS":
            self._set_aspect_ratio(region, mouse_pos, "16_9")
            return {"RUNNING_MODAL"}
        elif event.type in {"FIVE", "NUMPAD_5"} and event.value == "PRESS":
            self._set_aspect_ratio(region, mouse_pos, "9_16")
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def _angle_from_center(self, region, mouse_pos):
        rect = self._get_display_rect()
        center = image_to_region(region, self._image_size, *rect.center)
        return math.atan2(mouse_pos[1] - center[1], mouse_pos[0] - center[0])

    def _apply_rotation_drag(self, region, mouse_pos, snap: bool) -> None:
        delta_angle = self._angle_from_center(region, mouse_pos) - self.drag_start_angle
        new_rotation = self.drag_start_rotation + delta_angle

        if snap:
            step = math.radians(ROTATE_SNAP_STEP_DEG)
            new_rotation = round(new_rotation / step) * step

        self.rotation = new_rotation
        clamped = clamp_rect_to_image(self._current_rect(), self._image_size, self.rotation)
        self._set_rect(clamped)

    def _apply_drag(self, region, mouse_pos) -> None:
        start_uv = region.view2d.region_to_view(*self.drag_start_mouse)
        curr_uv = region.view2d.region_to_view(*mouse_pos)

        delta_x = (curr_uv[0] - start_uv[0]) * self._image_size[0]
        delta_y = (curr_uv[1] - start_uv[1]) * self._image_size[1]

        handle = self.active_handle
        start = self.drag_start_rect
        start_xmin, start_xmax, start_ymin, start_ymax = start.as_tuple()
        img_w, img_h = self._image_size

        MIN_SIZE = min(16.0, img_w, img_h)

        if handle == "MOVE":
            moved = Rect(
                start_xmin + delta_x,
                start_xmax + delta_x,
                start_ymin + delta_y,
                start_ymax + delta_y,
            )
            new_rect = clamp_move_to_image(moved, self._image_size, self.rotation)
        else:
            is_corner = handle in {"TL", "TR", "BL", "BR"}

            raw_xmin = start_xmin + delta_x if "L" in handle else start_xmin
            raw_xmax = start_xmax + delta_x if "R" in handle else start_xmax
            raw_ymin = start_ymin + delta_y if "B" in handle else start_ymin
            raw_ymax = start_ymax + delta_y if "T" in handle else start_ymax

            ratio_w, ratio_h = self._get_aspect_ratio()
            if is_corner:
                width = max(abs(raw_xmax - raw_xmin), MIN_SIZE)
                height = width * (ratio_h / ratio_w)
                if height < MIN_SIZE:
                    height = MIN_SIZE
                    width = height * (ratio_w / ratio_h)
            elif handle in {"L", "R"}:
                width = max(abs(raw_xmax - raw_xmin), MIN_SIZE)
                height = width * (ratio_h / ratio_w)
            elif handle in {"T", "B"}:
                height = max(abs(raw_ymax - raw_ymin), MIN_SIZE)
                width = height * (ratio_w / ratio_h)

            if "L" in handle:
                new_xmin, new_xmax = start_xmax - width, start_xmax
            elif "R" in handle:
                new_xmin, new_xmax = start_xmin, start_xmin + width
            else:
                new_xmin, new_xmax = start_xmin, start_xmax

            if "B" in handle:
                new_ymin, new_ymax = start_ymax - height, start_ymax
            elif "T" in handle:
                new_ymin, new_ymax = start_ymin, start_ymin + height
            else:
                new_ymin, new_ymax = start_ymin, start_ymax

            if handle in {"L", "R"}:
                center_y = (start_ymin + start_ymax) / 2.0
                new_ymin, new_ymax = center_y - height / 2.0, center_y + height / 2.0
            elif handle in {"T", "B"}:
                center_x = (start_xmin + start_xmax) / 2.0
                new_xmin, new_xmax = center_x - width / 2.0, center_x + width / 2.0

            anchor_x = start_xmax if "L" in handle else (start_xmin if "R" in handle else (start_xmin + start_xmax) / 2.0)
            anchor_y = start_ymax if "B" in handle else (start_ymin if "T" in handle else (start_ymin + start_ymax) / 2.0)

            new_rect = clamp_resize_to_image(
                Rect(new_xmin, new_xmax, new_ymin, new_ymax),
                (anchor_x, anchor_y),
                self._image_size,
                self.rotation,
                MIN_SIZE,
            )

        self._set_rect(new_rect)

    def execute(self, context):
        scene = context.scene
        if self._original_size is None:
            self.report({"ERROR"}, "Original image data not found. Please run the tool again.")
            return {"CANCELLED"}

        original_size = self._original_size

        safe_xmin = self.xmin
        safe_ymin = self.ymin
        safe_xmax = self.xmax
        safe_ymax = self.ymax

        trim_width = safe_xmax - safe_xmin
        trim_height = safe_ymax - safe_ymin

        if trim_width <= 0 or trim_height <= 0:
            self.report({"WARNING"}, "The selected region is invalid.")
            return {"CANCELLED"}

        node_tree = get_compositor_node_tree(scene)
        try:
            image_node = find_single_image_node(node_tree)
            transform_node = get_transform_node(node_tree, image_node)
        except (ImageNodeLookupError, TransformNodeLookupError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        self._transform_node_name = transform_node.name

        safe_rect = Rect(safe_xmin, safe_xmax, safe_ymin, safe_ymax)
        offset_x, offset_y = compute_transform_offset(safe_rect, original_size)

        transform_node.inputs["X"].default_value = offset_x
        transform_node.inputs["Y"].default_value = offset_y
        if "Angle" in transform_node.inputs:
            transform_node.inputs["Angle"].default_value = self.rotation

        scene.render.resolution_x = trim_width
        scene.render.resolution_y = trim_height
        scene.render.resolution_percentage = 100

        _store_last_trim(self._image.name, safe_rect, self.rotation, original_size)

        return {"FINISHED"}

    def _finish(self, context, cancelled: bool):
        self.__class__._is_running = False  # 終了時にフラグOFF

        context.window.cursor_set("DEFAULT")
        if self._draw_handler:
            bpy.types.SpaceImageEditor.draw_handler_remove(self._draw_handler, "WINDOW")
        if self._area:
            self._area.tag_redraw()

        self._image_gpu_texture = None

        if cancelled:
            self._original_size = None
            self._original_render_res = None
            self._original_render_percentage = None
            self._transform_node_name = None

        return {"CANCELLED"} if cancelled else {"FINISHED"}


class RETOUCH_OT_image_trim_reset(Operator):
    bl_idname = "retouch.image_trim_reset"
    bl_label = "Reset Trim"
    bl_description = "Reset the trim and restore the original Transform node and render resolution"

    @classmethod
    def poll(cls, context):
        return context.area.type == "IMAGE_EDITOR"

    def execute(self, context):
        scene = context.scene
        node_tree = get_compositor_node_tree(scene)

        try:
            # ノードツリーから画像と Transform ノードを直接探す
            image_node = find_single_image_node(node_tree)
            image = image_node.image
            if not image:
                self.report({"ERROR"}, "No image found for reset.")
                return {"CANCELLED"}
            transform_node = get_transform_node(node_tree, image_node)
        except (ImageNodeLookupError, TransformNodeLookupError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        # Transformノードの移動・回転をリセット
        reset_transform_node(transform_node)

        # 解像度を画像のオリジナルサイズに完全リセット
        scene.render.resolution_x = image.size[0]
        scene.render.resolution_y = image.size[1]
        scene.render.resolution_percentage = 100

        # 再トリム時に古いキャッシュを読み込まないよう履歴を削除
        _last_trim_cache.pop(image.name, None)

        return {"FINISHED"}


classes = (
    RETOUCH_OT_image_trim,
    RETOUCH_OT_image_trim_reset,
)
