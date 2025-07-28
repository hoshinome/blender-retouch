import bpy
from . import ui,operator

modules=(ui,operator
         )

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in reversed(modules):
        mod.unregister()