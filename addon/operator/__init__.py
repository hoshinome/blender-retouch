import bpy
from . import add_nodes, preset_ops, template, trim


classes = []
classes += add_nodes.classes
classes += preset_ops.classes
classes += template.classes
classes += trim.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if 'ic_revert_data' in getattr(bpy.context, 'window_manager', {}):
        del bpy.context.window_manager['ic_revert_data']
