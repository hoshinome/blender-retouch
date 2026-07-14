import bpy
from . import template


def register():
    template.install_app_template()


def unregister():
    pass
#     template.uninstall_app_template()
