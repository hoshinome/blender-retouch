from bpy.props import EnumProperty, StringProperty
from bpy.types import PropertyGroup


class RETOUCH_PG_tabs(PropertyGroup):
    panel_tabs: EnumProperty(
        items=[
            ("Effects", "Effects", "Effects Settings", "NONE", 0),
            ("Vignette", "Vignette", "Vignette Settings", "NONE", 1),
            ("Grain", "Grain", "Grain Settings", "NONE", 2),
        ]
    )

    retouch_preset_name: StringProperty(
        name="Preset Name",
        description="Preset name to save or load",
        default="",
    )

    retouch_preset_folder: StringProperty(
        name="Preset Folder",
        description="Current preset folder path relative to the presets directory",
        default="presets",
    )

    retouch_preset_folder_name: StringProperty(
        name="New Folder Name",
        description="Name for a new preset folder",
        default="",
    )


classes = (
    RETOUCH_PG_tabs,
)
