import bpy
from bpy.types import Operator
from ..template.template import uninstall_app_template


class RETOUCH_OT_uninstall_template(Operator):
    bl_idname = "retouch.uninstall_template"
    bl_label = "Remove template"
    bl_description = "Remove template"
    # bl_options = {'REGISTER'}

    def execute(self, context):
        result = uninstall_app_template()
        if result == "removed":
            self.report({'INFO'}, "Blender Retouch template removed. Restart Blender to update the splash list.")
        elif result == "missing":
            self.report({'WARNING'}, "Template was not installed, nothing to remove.")
        else:
            self.report({'ERROR'}, "Failed to remove template. Check the console for details.")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


classes = (
    RETOUCH_OT_uninstall_template,
)
