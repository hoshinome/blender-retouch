import os

import bpy
from bpy.types import Panel


class RETOUCH_PT_preset(Panel):
    bl_idname = "RETOUCH_PT_preset"
    bl_label = "Preset"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BLENDER RETOUCH"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Preset")

        row = box.row(align=True)
        row.prop(context.scene.retouch, "retouch_preset_name", text="")
        row.operator("retouch.save_preset", text="", icon="FILE_TICK")
        row.operator("retouch.import_preset", text="", icon="IMPORT")

        preset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "presets")
        if not os.path.isdir(preset_dir):
            return

        preset_files = sorted([f for f in os.listdir(preset_dir) if f.endswith(".brp")])
        if not preset_files:
            return

        box.label(text="Saved presets:")
        for filename in preset_files:
            preset_name = os.path.splitext(filename)[0]
            sub = box.row(align=True)
            sub.label(text=preset_name)

            load_op = sub.operator("retouch.load_preset", text="", icon="FILE_REFRESH")
            load_op.preset_name = preset_name

            export_op = sub.operator("retouch.export_preset", text="", icon="EXPORT")
            export_op.preset_name = preset_name

            delete_op = sub.operator("retouch.delete_preset", text="", icon="TRASH")
            delete_op.preset_name = preset_name


classes = (RETOUCH_PT_preset,)
