import bpy
from . import (ui,
               operator,
               settings,)

modules = (
    ui,
    operator,
    settings,
)

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in reversed(modules):
        mod.unregister()