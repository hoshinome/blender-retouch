import bpy
import gpu
import math
from bpy.types import Operator

from ..utils.trim import (
    get_compositor_node_tree,
    find_single_image_node,
    get_transform_node,
    reset_transform_node,
    clamp_rect_to_image,
    clamp_move_to_image,
    clamp_resize_to_image,
    get_handle_positions,
    get_rotate_handle_position,
    get_trim_rect_screen_corners,
    point_in_polygon,
    image_to_region,
    draw_callback_px,
    ImageNodeLookupError,
    TransformNodeLookupError,
    HANDLE_PICK_RADIUS_PX,
    ROTATE_DIAL_RADIUS_PX,
    ROTATE_SNAP_STEP_DEG,
)


def revert_update(self, context):
    if self.revert_to_original:
        revert_data = context.window_manager.get('ic_revert_data')
        if revert_data:
            original_size = revert_data['size']
            self.xmin = 0
            self.ymin = 0
            self.xmax = original_size[0]
            self.ymax = original_size[1]
        self.revert_to_original = False


class RETOUCH_OT_image_trim(Operator):
    bl_idname = "retouch.image_trim"
    bl_label = "Image Trim"
    bl_description = "Image Trim"
    # bl_options = {'REGISTER', 'UNDO'}

    xmin: bpy.props.IntProperty(name="X Min")
    xmax: bpy.props.IntProperty(name="X Max")
    ymin: bpy.props.IntProperty(name="Y Min")
    ymax: bpy.props.IntProperty(name="Y Max")

    revert_to_original: bpy.props.BoolProperty(
        name="Revert to Original",
        description="Cancel the trim and restore the original Transform/resolution",
        default=False,
        update=revert_update
    )

    aspect_ratio_enum: bpy.props.EnumProperty(
        name="Aspect Ratio",
        description="Aspect ratio to lock while dragging",
        items=[
            ('1_1', "1:1", "Square"),
            ('4_3', "4:3", "4:3"),
            ('3_2', "3:2", "3:2"),
            ('16_9', "16:9", "16:9"),
            ('9_16', "9:16", "9:16 (Portrait)"),
            ('CUSTOM', "Custom", "Specify a custom ratio"),
        ],
        default='3_2',
    )
    aspect_ratio_custom_w: bpy.props.FloatProperty(
        name="W", description="Custom ratio width", default=1.0, min=0.0001,
    )
    aspect_ratio_custom_h: bpy.props.FloatProperty(
        name="H", description="Custom ratio height", default=1.0, min=0.0001,
    )

    rotation: bpy.props.FloatProperty(
        name="Rotation",
        description="Rotation angle of the image (applied to the Transform node's Angle)",
        default=0.0,
        subtype='ANGLE',
    )

    _draw_handler = None
    shader = None
    _area = None
    _region = None
    _image_size = (1, 1)
    _image = None

    active_handle = None
    drag_start_mouse = (0, 0)
    drag_start_rect = (0, 0, 0, 0)
    drag_start_rotation = 0.0
    drag_start_angle = 0.0

    @classmethod
    def poll(cls, context):
        return context.area.type == 'IMAGE_EDITOR'

    def _get_aspect_ratio(self):
        preset_map = {
            '1_1': (1.0, 1.0), '4_3': (4.0, 3.0), '3_2': (3.0, 2.0),
            '16_9': (16.0, 9.0), '9_16': (9.0, 16.0),
        }
        if self.aspect_ratio_enum == 'CUSTOM':
            if self.aspect_ratio_custom_w <= 0 or self.aspect_ratio_custom_h <= 0:
                return None
            return (self.aspect_ratio_custom_w, self.aspect_ratio_custom_h)
        return preset_map.get(self.aspect_ratio_enum)

    def _get_display_rect(self):
        img_w, img_h = self._image_size
        return clamp_rect_to_image(
            self.xmin, self.xmax, self.ymin, self.ymax, img_w, img_h, self.rotation,
        )

    def _apply_aspect_to_current_rect(self):
        aspect = self._get_aspect_ratio()
        if aspect is None:
            return

        ratio_w, ratio_h = aspect
        center_x = (self.xmin + self.xmax) / 2.0
        center_y = (self.ymin + self.ymax) / 2.0

        width = self.xmax - self.xmin
        height = self.ymax - self.ymin
        area = max(width * height, 1.0)

        new_width = (area * ratio_w / ratio_h) ** 0.5
        new_height = new_width * (ratio_h / ratio_w)

        img_w, img_h = self._image_size
        if new_width > img_w or new_height > img_h:
            scale = min(img_w / new_width, img_h / new_height)
            new_width *= scale
            new_height *= scale

        new_xmin = center_x - new_width / 2.0
        new_xmax = center_x + new_width / 2.0
        new_ymin = center_y - new_height / 2.0
        new_ymax = center_y + new_height / 2.0

        new_xmin, new_xmax, new_ymin, new_ymax = clamp_rect_to_image(
            new_xmin, new_xmax, new_ymin, new_ymax, img_w, img_h, self.rotation,
        )

        self.xmin = int(round(new_xmin))
        self.xmax = int(round(new_xmax))
        self.ymin = int(round(new_ymin))
        self.ymax = int(round(new_ymax))

    def _set_aspect_ratio(self, region, mouse_pos, new_enum_value):
        self.aspect_ratio_enum = new_enum_value
        self._apply_aspect_to_current_rect()
        if self.active_handle is not None:
            self.drag_start_mouse = mouse_pos
            self.drag_start_rect = (self.xmin, self.xmax, self.ymin, self.ymax)

    def _handle_at_mouse(self, region, mouse_pos):
        mx, my = mouse_pos
        dxmin, dxmax, dymin, dymax = self._get_display_rect()
        rotation = self.rotation

        handle_positions = get_handle_positions(region, self._image_size, dxmin, dxmax, dymin, dymax, rotation)
        closest_key = None
        closest_dist = HANDLE_PICK_RADIUS_PX

        for key, (hx, hy) in handle_positions.items():
            dist = ((hx - mx) ** 2 + (hy - my) ** 2) ** 0.5
            if dist <= closest_dist:
                closest_dist = dist
                closest_key = key

        if closest_key is not None:
            return closest_key

        rotate_pos = get_rotate_handle_position(region, self._image_size, dxmin, dxmax, dymin, dymax, rotation)
        dist = ((rotate_pos[0] - mx) ** 2 + (rotate_pos[1] - my) ** 2) ** 0.5

        if abs(dist - ROTATE_DIAL_RADIUS_PX) <= 15 and my <= rotate_pos[1]:
            return 'ROTATE'

        corners_screen = get_trim_rect_screen_corners(region, self._image_size, dxmin, dxmax, dymin, dymax, rotation)
        if point_in_polygon(mouse_pos, corners_screen):
            return 'MOVE'

        return None

    def invoke(self, context, event):
        scene = context.scene
        node_tree = get_compositor_node_tree(scene)

        try:
            image_node = find_single_image_node(node_tree)
        except ImageNodeLookupError as err:
            self.report({'ERROR'}, str(err))
            return {'CANCELLED'}

        image = image_node.image
        if image is None:
            self.report({'ERROR'}, "No image is assigned to the Image node.")
            return {'CANCELLED'}

        image_size = image.size[:]
        context.window_manager['ic_revert_data'] = {
            'size': image_size,
            'render_res': (scene.render.resolution_x, scene.render.resolution_y),
            'render_percentage': scene.render.resolution_percentage,
        }

        self.xmin = 0
        self.ymin = 0
        self.xmax = image_size[0]
        self.ymax = image_size[1]
        self._image_size = image_size
        self._image = image
        self._area = context.area
        self._region = context.region
        self.active_handle = None

        try:
            transform_node = get_transform_node(node_tree, image_node)
            if 'Angle' in transform_node.inputs:
                self.rotation = transform_node.inputs['Angle'].default_value
            else:
                self.rotation = 0.0
        except TransformNodeLookupError:
            self.rotation = 0.0

        c_xmin, c_xmax, c_ymin, c_ymax = clamp_rect_to_image(
            self.xmin, self.xmax, self.ymin, self.ymax,
            image_size[0], image_size[1], self.rotation,
        )
        self.xmin = int(round(c_xmin))
        self.xmax = int(round(c_xmax))
        self.ymin = int(round(c_ymin))
        self.ymax = int(round(c_ymax))

        self._apply_aspect_to_current_rect()

        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.image_shader = gpu.shader.from_builtin('IMAGE_COLOR_SCENE_LINEAR_TO_REC709_SRGB')
        try:
            self._image_gpu_texture = gpu.texture.from_image(self._image)
        except Exception:
            self._image_gpu_texture = None

        args = (self, context)
        self._draw_handler = bpy.types.SpaceImageEditor.draw_handler_add(
            draw_callback_px, args, 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self._area:
            self._area.tag_redraw()

        pass_through_types = {
            'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
            'NDOF_PAN', 'NDOF_ORBIT', 'NDOF_BUTTON_FIT', 'TRACKPADPAN', 'TRACKPADZOOM'
        }
        if event.type in pass_through_types or (event.type in {'NUMPAD_PLUS', 'NUMPAD_MINUS'} and event.value == 'PRESS'):
            return {'PASS_THROUGH'}

        region = self._region
        mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        if self.active_handle is None:
            hovered = self._handle_at_mouse(region, mouse_pos)
            cursor_map = {
                'TL': 'MOVE_X', 'TR': 'MOVE_X', 'BL': 'MOVE_X', 'BR': 'MOVE_X',
                'T': 'MOVE_Y', 'B': 'MOVE_Y', 'L': 'MOVE_X', 'R': 'MOVE_X',
                'MOVE': 'SCROLL_XY', 'ROTATE': 'KNIFE', None: 'DEFAULT',
            }
            context.window.cursor_set(cursor_map.get(hovered, 'DEFAULT'))

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            hovered = self._handle_at_mouse(region, mouse_pos)
            if hovered is not None:
                self.active_handle = hovered
                self.drag_start_mouse = mouse_pos
                self.drag_start_rect = (self.xmin, self.xmax, self.ymin, self.ymax)
                if hovered == 'ROTATE':
                    self.drag_start_rotation = self.rotation
                    self.drag_start_angle = self._angle_from_center(region, mouse_pos)
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        elif event.type == 'MOUSEMOVE':
            if self.active_handle == 'ROTATE':
                self._apply_rotation_drag(region, mouse_pos, event.shift)
                return {'RUNNING_MODAL'}
            if self.active_handle is not None:
                self._apply_drag(region, mouse_pos)
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.active_handle is not None:
                self.active_handle = None
            return {'RUNNING_MODAL'}

        elif event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            self._finish(context, cancelled=False)
            return self.execute(context)
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return self._finish(context, cancelled=True)

        elif event.type in {'ONE', 'NUMPAD_1'} and event.value == 'PRESS':
            self._set_aspect_ratio(region, mouse_pos, '1_1')
            return {'RUNNING_MODAL'}
        elif event.type in {'TWO', 'NUMPAD_2'} and event.value == 'PRESS':
            self._set_aspect_ratio(region, mouse_pos, '4_3')
            return {'RUNNING_MODAL'}
        elif event.type in {'THREE', 'NUMPAD_3'} and event.value == 'PRESS':
            self._set_aspect_ratio(region, mouse_pos, '3_2')
            return {'RUNNING_MODAL'}
        elif event.type in {'FOUR', 'NUMPAD_4'} and event.value == 'PRESS':
            self._set_aspect_ratio(region, mouse_pos, '16_9')
            return {'RUNNING_MODAL'}
        elif event.type in {'FIVE', 'NUMPAD_5'} and event.value == 'PRESS':
            self._set_aspect_ratio(region, mouse_pos, '9_16')
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def _angle_from_center(self, region, mouse_pos):
        dxmin, dxmax, dymin, dymax = self._get_display_rect()
        center = image_to_region(region, self._image_size, (dxmin + dxmax) / 2.0, (dymin + dymax) / 2.0)
        return math.atan2(mouse_pos[1] - center[1], mouse_pos[0] - center[0])

    def _apply_rotation_drag(self, region, mouse_pos, snap):
        delta_angle = self._angle_from_center(region, mouse_pos) - self.drag_start_angle
        new_rotation = self.drag_start_rotation + delta_angle

        if snap:
            step = math.radians(ROTATE_SNAP_STEP_DEG)
            new_rotation = round(new_rotation / step) * step

        self.rotation = new_rotation
        img_w, img_h = self._image_size
        c_xmin, c_xmax, c_ymin, c_ymax = clamp_rect_to_image(
            self.xmin, self.xmax, self.ymin, self.ymax, img_w, img_h, self.rotation,
        )
        self.xmin = int(round(c_xmin))
        self.xmax = int(round(c_xmax))
        self.ymin = int(round(c_ymin))
        self.ymax = int(round(c_ymax))

    def _apply_drag(self, region, mouse_pos):
        start_uv = region.view2d.region_to_view(*self.drag_start_mouse)
        curr_uv = region.view2d.region_to_view(*mouse_pos)

        delta_x = (curr_uv[0] - start_uv[0]) * self._image_size[0]
        delta_y = (curr_uv[1] - start_uv[1]) * self._image_size[1]

        handle = self.active_handle
        start_xmin, start_xmax, start_ymin, start_ymax = self.drag_start_rect
        img_w, img_h = self._image_size

        # 最低サイズ (極端に潰れたり反転するのを防ぐ)
        MIN_SIZE = min(16.0, img_w, img_h)

        if handle == 'MOVE':
            new_xmin, new_xmax = start_xmin + delta_x, start_xmax + delta_x
            new_ymin, new_ymax = start_ymin + delta_y, start_ymax + delta_y
            new_xmin, new_xmax, new_ymin, new_ymax = clamp_move_to_image(
                new_xmin, new_xmax, new_ymin, new_ymax, img_w, img_h, self.rotation,
            )
        else:
            is_corner = handle in {'TL', 'TR', 'BL', 'BR'}

            # マウスの移動量に基づく生の目標座標
            raw_xmin = start_xmin + delta_x if 'L' in handle else start_xmin
            raw_xmax = start_xmax + delta_x if 'R' in handle else start_xmax
            raw_ymin = start_ymin + delta_y if 'B' in handle else start_ymin
            raw_ymax = start_ymax + delta_y if 'T' in handle else start_ymax

            ratio_w, ratio_h = self._get_aspect_ratio()
            if is_corner:
                width = max(abs(raw_xmax - raw_xmin), MIN_SIZE)
                height = width * (ratio_h / ratio_w)
                if height < MIN_SIZE:
                    height = MIN_SIZE
                    width = height * (ratio_w / ratio_h)
            elif handle in {'L', 'R'}:
                width = max(abs(raw_xmax - raw_xmin), MIN_SIZE)
                height = width * (ratio_h / ratio_w)
            elif handle in {'T', 'B'}:
                height = max(abs(raw_ymax - raw_ymin), MIN_SIZE)
                width = height * (ratio_w / ratio_h)

            if 'L' in handle:
                new_xmin, new_xmax = start_xmax - width, start_xmax
            elif 'R' in handle:
                new_xmin, new_xmax = start_xmin, start_xmin + width
            else:
                new_xmin, new_xmax = start_xmin, start_xmax

            if 'B' in handle:
                new_ymin, new_ymax = start_ymax - height, start_ymax
            elif 'T' in handle:
                new_ymin, new_ymax = start_ymin, start_ymin + height
            else:
                new_ymin, new_ymax = start_ymin, start_ymax

            if handle in {'L', 'R'}:
                center_y = (start_ymin + start_ymax) / 2.0
                new_ymin, new_ymax = center_y - height / 2.0, center_y + height / 2.0
            elif handle in {'T', 'B'}:
                center_x = (start_xmin + start_xmax) / 2.0
                new_xmin, new_xmax = center_x - width / 2.0, center_x + width / 2.0

            # アスペクト比固定のため、決定した形状(縦横比)を保ったまま画像内に相似縮小する。
            # これにより、斜めの壁に当たっても潰れたり平べったくなることはない。
            anchor_x = start_xmax if 'L' in handle else (start_xmin if 'R' in handle else (start_xmin + start_xmax) / 2.0)
            anchor_y = start_ymax if 'B' in handle else (start_ymin if 'T' in handle else (start_ymin + start_ymax) / 2.0)

            new_xmin, new_xmax, new_ymin, new_ymax = clamp_resize_to_image(
                new_xmin, new_xmax, new_ymin, new_ymax,
                anchor_x, anchor_y, img_w, img_h, self.rotation, MIN_SIZE
            )

        self.xmin = int(round(new_xmin))
        self.xmax = int(round(new_xmax))
        self.ymin = int(round(new_ymin))
        self.ymax = int(round(new_ymax))

    def execute(self, context):
        scene = context.scene
        revert_data = context.window_manager.get('ic_revert_data')
        if not revert_data:
            self.report({'ERROR'}, "Original image data not found. Please run the tool again.")
            return {'CANCELLED'}

        original_size = tuple(revert_data['size'])
        clamped_xmin, clamped_xmax, clamped_ymin, clamped_ymax = clamp_rect_to_image(
            self.xmin, self.xmax, self.ymin, self.ymax,
            original_size[0], original_size[1], self.rotation,
        )

        safe_xmin = max(0, int(round(clamped_xmin)))
        safe_ymin = max(0, int(round(clamped_ymin)))
        safe_xmax = min(original_size[0], int(round(clamped_xmax)))
        safe_ymax = min(original_size[1], int(round(clamped_ymax)))

        if safe_xmin > safe_xmax:
            safe_xmin, safe_xmax = safe_xmax, safe_xmin
        if safe_ymin > safe_ymax:
            safe_ymin, safe_ymax = safe_ymax, safe_ymin

        trim_width = safe_xmax - safe_xmin
        trim_height = safe_ymax - safe_ymin

        if trim_width <= 0 or trim_height <= 0:
            self.report({'WARNING'}, "The selected region is invalid.")
            return {'CANCELLED'}

        node_tree = get_compositor_node_tree(scene)
        try:
            image_node = find_single_image_node(node_tree)
            transform_node = get_transform_node(node_tree, image_node)
        except (ImageNodeLookupError, TransformNodeLookupError) as err:
            self.report({'ERROR'}, str(err))
            return {'CANCELLED'}

        revert_data['transform_node_name'] = transform_node.name
        context.window_manager['ic_revert_data'] = revert_data

        trim_center_x = (safe_xmin + safe_xmax) / 2.0
        trim_center_y = (safe_ymin + safe_ymax) / 2.0
        image_center_x = original_size[0] / 2.0
        image_center_y = original_size[1] / 2.0

        transform_angle = self.rotation

        raw_dx = trim_center_x - image_center_x
        raw_dy = trim_center_y - image_center_y
        cos_r = math.cos(transform_angle)
        sin_r = math.sin(transform_angle)
        rotated_dx = raw_dx * cos_r - raw_dy * sin_r
        rotated_dy = raw_dx * sin_r + raw_dy * cos_r

        transform_node.inputs['X'].default_value = -rotated_dx
        transform_node.inputs['Y'].default_value = -rotated_dy
        if 'Angle' in transform_node.inputs:
            transform_node.inputs['Angle'].default_value = transform_angle

        scene.render.resolution_x = trim_width
        scene.render.resolution_y = trim_height
        scene.render.resolution_percentage = 100

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "xmin")
        col.prop(self, "xmax")
        col.prop(self, "ymin")
        col.prop(self, "ymax")
        layout.separator()

        col = layout.column()
        col.prop(self, "aspect_ratio_enum")
        if self.aspect_ratio_enum == 'CUSTOM':
            row = col.row(align=True)
            row.prop(self, "aspect_ratio_custom_w")
            row.prop(self, "aspect_ratio_custom_h")

        layout.separator()
        layout.prop(self, "rotation")

        layout.separator()
        layout.prop(self, "revert_to_original")

    def _finish(self, context, cancelled):
        context.window.cursor_set('DEFAULT')
        if self._draw_handler:
            bpy.types.SpaceImageEditor.draw_handler_remove(self._draw_handler, 'WINDOW')
        if self._area:
            self._area.tag_redraw()

        self._image_gpu_texture = None

        if cancelled and 'ic_revert_data' in context.window_manager:
            del context.window_manager['ic_revert_data']

        return {'CANCELLED'} if cancelled else {'FINISHED'}


class RETOUCH_OT_image_trim_reset(Operator):
    bl_idname = "retouch.image_trim_reset"
    bl_label = "Reset Trim"
    bl_description = "Reset Trim"
    # bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'IMAGE_EDITOR'

    def execute(self, context):
        scene = context.scene
        node_tree = get_compositor_node_tree(scene)

        revert_data = context.window_manager.get('ic_revert_data')
        if not revert_data:
            self.report({'WARNING'}, "Revert data not found.")
            return {'CANCELLED'}

        transform_node_name = revert_data.get('transform_node_name')
        if transform_node_name:
            transform_node = node_tree.nodes.get(transform_node_name) if node_tree else None
            reset_transform_node(transform_node)

        res_x, res_y = revert_data['render_res']
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y
        scene.render.resolution_percentage = revert_data['render_percentage']
        del context.window_manager['ic_revert_data']

        return {'FINISHED'}


classes = (
    RETOUCH_OT_image_trim,
    RETOUCH_OT_image_trim_reset,
)
