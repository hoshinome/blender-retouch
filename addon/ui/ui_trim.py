from bpy.types import Panel

from .ui_panel import RetouchPanelMixin


class RETOUCH_PT_image_trim(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_image_trim"
    bl_label = "Trimming"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("retouch.image_trim", text="Start Trim", icon="FULLSCREEN_ENTER")
        col.operator("retouch.image_trim_reset", text="Reset", icon="LOOP_BACK")


classes = (RETOUCH_PT_image_trim,)
