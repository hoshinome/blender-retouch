import bpy
from . import (ui,
               operator,
               scene,
               template,
               preferences)


modules = (
    ui,
    operator,
    scene,
    template,
    preferences
)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()