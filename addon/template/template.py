import bpy
import os
import shutil

TEMPLATE_NAME = "Blender Retouch"


def get_template_dir():
    user_scripts = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(user_scripts, "startup", "bl_app_templates_user", TEMPLATE_NAME)


def install_app_template():
    # blender-retouch/add_template.py と同じ階層(blender-retouch/)を基準に
    # addon/assets/template.blend を参照
    # startup.py があるフォルダ (blender-retouch/addon/startup/) から
    # 1階層上がって blender-retouch/addon/ を得る
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # そこから assets/startup.blend へ下る
    src_blend = os.path.join(addon_dir, "assets", "startup.blend")

    if not os.path.isfile(src_blend):
        print(f"[Blender Retouch] template.blend not found at: {src_blend}")
        return

    template_dir = get_template_dir()
    os.makedirs(template_dir, exist_ok=True)

    dst_blend = os.path.join(template_dir, "startup.blend")
    shutil.copy(src_blend, dst_blend)

    # init_path = os.path.join(template_dir, "__init__.py")
    # if not os.path.isfile(init_path):
    #     with open(init_path, "w", encoding="utf-8") as f:
    #         f.write("bl_info = {\n")
    #         f.write('    "name": "Blender Retouch",\n')
    #         f.write('    "author": "Blender Retouch",\n')
    #         f.write('    "version": (1, 0, 0),\n')
    #         f.write('    "blender": (5, 1, 0),\n')
    #         f.write('    "description": "Blender Retouch workspace template",\n')
    #         f.write('    "category": "Learnbgame",\n')
    #         f.write("}\n")


def uninstall_app_template():
    template_dir = get_template_dir()
    if os.path.isdir(template_dir):
        shutil.rmtree(template_dir, ignore_errors=True)


def register():
    install_app_template()


def unregister():
    uninstall_app_template()
