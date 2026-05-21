import os
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from ..utils.compositor import apply_retouch_to_scene, NODETREE_NAME


class RETOUCH_OT_add_nodes(Operator, ImportHelper):
    bl_idname = "retouch.add_nodes"
    bl_label = "Load Image"
    bl_description = "Add nodes"

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.exr",
        options={"HIDDEN"},
        maxlen=255,
    )
    filepath: StringProperty(
        name="File Path",
        description="Path to the selected image",
        maxlen=1024,
        default="",
    )

    def execute(self, context):
        if not self.filepath:
            self.report({"ERROR"}, "No image selected.")
            return {"CANCELLED"}

        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        blend_file_path = os.path.join(addon_dir, "assets", "node.blend")

        if not os.path.exists(blend_file_path):
            self.report({"ERROR"}, f"Template blend file not found: {blend_file_path}")
            return {"CANCELLED"}

        scene = apply_retouch_to_scene(self, context, self.filepath, blend_file_path, NODETREE_NAME)
        if scene is None:
            return {"CANCELLED"}

        try:
            scene.render.compositor_device = "GPU"
        except (AttributeError, TypeError):
            pass

        self.report({"INFO"}, f"Applied '{NODETREE_NAME}' to scene '{scene.name}'.")
        return {"FINISHED"}


classes = (RETOUCH_OT_add_nodes,)