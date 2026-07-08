import bpy
from . import panel, preset

classes = []
classes += panel.classes
classes += preset.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
