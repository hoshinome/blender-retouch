import bpy
from . import (ui,
               operator,
               settings,
               template,
               preferences)


modules = (
    ui,
    operator,
    settings,
    template,
    preferences
)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()
