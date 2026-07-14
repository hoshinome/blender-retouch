import os
import shutil
import bpy

TEMPLATE_NAME = "Blender Retouch"


def get_template_dir():
    user_scripts = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(user_scripts, "startup", "bl_app_templates_user", TEMPLATE_NAME)


def install_app_template():
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_blend = os.path.join(addon_dir, "assets", "startup.blend")

    if not os.path.isfile(src_blend):
        print(f"[{TEMPLATE_NAME}] Error: startup.blend not found at '{src_blend}'")
        return False

    template_dir = get_template_dir()

    try:
        os.makedirs(template_dir, exist_ok=True)
        dst_blend = os.path.join(template_dir, "startup.blend")
        shutil.copy(src_blend, dst_blend)
        print(f"[{TEMPLATE_NAME}] Success: Template installed to '{template_dir}'")
        return True
    except Exception as e:
        print(f"[{TEMPLATE_NAME}] Error installing template: {e}")
        return False


def uninstall_app_template():
    template_dir = get_template_dir()

    if os.path.isdir(template_dir):
        try:
            shutil.rmtree(template_dir, ignore_errors=True)
            print(f"[{TEMPLATE_NAME}] Success: Template uninstalled.")
            return True
        except Exception as e:
            print(f"[{TEMPLATE_NAME}] Error uninstalling template: {e}")
            return False
    else:
        print(f"[{TEMPLATE_NAME}] Warning: Template directory not found, nothing to uninstall.")
        return False
