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


def _read_marker(marker_path):
    try:
        with open(marker_path, "r") as f:
            lines = f.read().splitlines()
    except OSError:
        return None

    if not lines:
        return None
    installed_digest = lines[0].strip()
    source_digest = lines[1].strip() if len(lines) > 1 else ""
    return installed_digest, source_digest


def _write_marker(marker_path, installed_digest, source_digest):
    with open(marker_path, "w") as f:
        f.write(f"{installed_digest}\n{source_digest}\n")


def install_app_template():
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_blend = os.path.join(addon_dir, "assets", "startup.blend")

    if not os.path.isfile(src_blend):
        print(f"[{TEMPLATE_NAME}] Error: startup.blend not found at '{src_blend}'")
        return False

    try:
        src_digest = _file_digest(src_blend)
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error reading bundled startup.blend: {e}")
        return False

    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")
    marker_path = os.path.join(template_dir, MARKER_NAME)

    if os.path.isfile(dst_blend):
        marker = _read_marker(marker_path) if os.path.isfile(marker_path) else None

        if marker is None:
            print(f"[{TEMPLATE_NAME}] Existing user startup.blend found at '{template_dir}', leaving it untouched.")
            return True

        installed_digest, source_digest_at_install = marker
        try:
            current_digest = _file_digest(dst_blend)
        except OSError as e:
            print(f"[{TEMPLATE_NAME}] Error reading installed startup.blend: {e}")
            return False

        if installed_digest != current_digest:
            print(f"[{TEMPLATE_NAME}] startup.blend at '{template_dir}' was modified by the user, leaving it untouched.")
            return True

        if source_digest_at_install == src_digest:
            print(f"[{TEMPLATE_NAME}] Template already installed at '{template_dir}', skipping copy.")
            return True

        try:
            shutil.copy(src_blend, dst_blend)
            _write_marker(marker_path, _file_digest(dst_blend), src_digest)
            print(f"[{TEMPLATE_NAME}] Success: Template refreshed at '{template_dir}'")
            return True
        except OSError as e:
            print(f"[{TEMPLATE_NAME}] Error refreshing template: {e}")
            return False

    try:
        os.makedirs(template_dir, exist_ok=True)
        shutil.copy(src_blend, dst_blend)
        _write_marker(marker_path, _file_digest(dst_blend), src_digest)
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

    marker = _read_marker(marker_path)
    if marker is None:
        print(f"[{TEMPLATE_NAME}] Error reading ownership marker.")
        return "failed"

    installed_digest, _source_digest_at_install = marker
    try:
        current_digest = _file_digest(dst_blend)
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error verifying template ownership: {e}")
        return "failed"

    if installed_digest != current_digest:
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
