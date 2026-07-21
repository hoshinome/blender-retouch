import bpy

from . import add_nodes, preset_ops, template, trim_ops

classes = (
    *add_nodes.classes,
    *preset_ops.classes,
    *template.classes,
    *trim_ops.classes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
