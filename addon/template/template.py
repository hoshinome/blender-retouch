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
    dst_blend = os.path.join(template_dir, "startup.blend")

    if os.path.isfile(dst_blend):
        print(f"[{TEMPLATE_NAME}] Template already installed at '{template_dir}', skipping copy.")
        return True

    try:
        os.makedirs(template_dir, exist_ok=True)
        shutil.copy(src_blend, dst_blend)
        print(f"[{TEMPLATE_NAME}] Success: Template installed to '{template_dir}'")
        return True
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error installing template: {e}")
        return False


def uninstall_app_template():
    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")

    if not os.path.isfile(dst_blend):
        print(f"[{TEMPLATE_NAME}] Warning: Template not found, nothing to uninstall.")
        return "missing"

    try:
        os.remove(dst_blend)

        try:
            if not os.listdir(template_dir):
                os.rmdir(template_dir)
        except OSError:
            pass

        print(f"[{TEMPLATE_NAME}] Success: Template uninstalled.")
        return "removed"
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error uninstalling template: {e}")
        return "failed"
