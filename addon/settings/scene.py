import bpy
# from ..resources import icons
from bpy.props import EnumProperty
from bpy.types import PropertyGroup

class RETOUCH_PG_tabs(PropertyGroup):
    panel_tabs: EnumProperty(
        items=[
            ("Reds", "Reds", "Red Settings", "NONE", 0),
            ("Yellows", "Yellows", "Yellow Settings", "NONE", 1),
            ("Greens", "Greens", "Green Settings", "NONE", 2),
            ("Cyans", "Cyans", "Cyan Settings", "NONE", 3),
            ("Blues", "Blues", "Blue Settings", "NONE", 4),
            ("Purples", "Purples", "Purple Settings", "NONE", 5),
            ("Magentas", "Magentas", "Magenta Settings", "NONE", 6),
        ]
    )

classes = (
    RETOUCH_PG_tabs,
)