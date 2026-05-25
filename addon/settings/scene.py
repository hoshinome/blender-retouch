import bpy
from bpy.props import EnumProperty
from bpy.types import PropertyGroup


class RETOUCH_PG_tabs(PropertyGroup):
    panel_tabs: EnumProperty(
        items=[
            ("Effects", "Effects", "Effects Settings", "NONE", 0),
            ("Vignette", "Vignette", "Vignette Settings", "NONE", 1),
            ("Grain", "Grain", "Grain Settings", "NONE", 2),
        ]
    )


classes = (
    RETOUCH_PG_tabs,
)
