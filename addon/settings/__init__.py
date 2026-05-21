import bpy
from bpy.props import PointerProperty
from . import scene

classes = []
classes += scene.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.retouch = PointerProperty(type=scene.RETOUCH_PG_tabs)


def unregister():
    del bpy.types.Scene.retouch

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
