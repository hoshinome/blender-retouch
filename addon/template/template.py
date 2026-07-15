import hashlib
import os
import shutil
import bpy

TEMPLATE_NAME = "Blender Retouch"
MARKER_NAME = ".installed_by_blender_retouch"


def get_template_dir():
    user_scripts = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(user_scripts, "startup", "bl_app_templates_user", TEMPLATE_NAME)


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def install_app_template():
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_blend = os.path.join(addon_dir, "assets", "startup.blend")

    if not os.path.isfile(src_blend):
        print(f"[{TEMPLATE_NAME}] Error: startup.blend not found at '{src_blend}'")
        return False

    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")
    marker_path = os.path.join(template_dir, MARKER_NAME)

    if os.path.isfile(dst_blend):
        if os.path.isfile(marker_path):
            try:
                with open(marker_path, "r") as f:
                    recorded_digest = f.read().strip()
                current_digest = _file_digest(dst_blend)
            except OSError:
                recorded_digest, current_digest = None, None

            if recorded_digest and recorded_digest == current_digest:
                print(f"[{TEMPLATE_NAME}] Template already installed at '{template_dir}', skipping copy.")
            else:
                print(f"[{TEMPLATE_NAME}] startup.blend at '{template_dir}' was modified by the user, leaving it untouched.")
        else:
            print(f"[{TEMPLATE_NAME}] Existing user startup.blend found at '{template_dir}', leaving it untouched.")
        return True
    try:
        os.makedirs(template_dir, exist_ok=True)
        shutil.copy(src_blend, dst_blend)

        with open(marker_path, "w") as f:
            f.write(_file_digest(dst_blend))
        print(f"[{TEMPLATE_NAME}] Success: Template installed to '{template_dir}'")
        return True
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error installing template: {e}")
        return False


def uninstall_app_template():
    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")
    marker_path = os.path.join(template_dir, MARKER_NAME)

    if not os.path.isfile(dst_blend):
        print(f"[{TEMPLATE_NAME}] Warning: Template not found, nothing to uninstall.")
        return "missing"

    if not os.path.isfile(marker_path):
        print(f"[{TEMPLATE_NAME}] Warning: startup.blend was not installed by this add-on, leaving it untouched.")
        return "not_owned"
    try:
        with open(marker_path, "r") as f:
            recorded_digest = f.read().strip()
        current_digest = _file_digest(dst_blend)
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error verifying template ownership: {e}")
        return "failed"

    if recorded_digest != current_digest:
        print(f"[{TEMPLATE_NAME}] Warning: startup.blend was modified since installation, leaving it untouched.")
        return "not_owned"
    try:
        os.remove(dst_blend)
        os.remove(marker_path)

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
