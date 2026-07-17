import bpy
from bpy.props import BoolProperty, PointerProperty

from . import scene

classes = []
classes += scene.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.retouch = PointerProperty(type=scene.RETOUCH_PG_tabs)

    bpy.types.Scene.retouch_image_only = BoolProperty(
        name="Image Only",
        description="Image Only",
        default=False,
    )


def unregister():
    del bpy.types.Scene.retouch_image_only
    del bpy.types.Scene.retouch

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
