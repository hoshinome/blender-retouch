import os, shutil, bpy
from bpy.types import Panel

class RetouchPanelMixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BLENDER RETOUCH"


def _get_preset_files(preset_dir: str) -> list[str]:
    """指定フォルダ直下にある .brp プリセットファイル名を一覧取得する（サブフォルダの中は含まない）"""
    if not os.path.isdir(preset_dir):
        return []

    preset_files = [
        filename for filename in os.listdir(preset_dir)
        if filename.endswith(".brp") and os.path.isfile(os.path.join(preset_dir, filename))
    ]
    return sorted(preset_files)


def _get_subfolders(preset_dir: str) -> list[str]:
    """指定フォルダ直下にあるサブフォルダ名を一覧取得する"""
    if not os.path.isdir(preset_dir):
        return []

    return sorted(
        entry for entry in os.listdir(preset_dir)
        if os.path.isdir(os.path.join(preset_dir, entry))
    )


# def _migrate_legacy_main_folder(preset_root: str) -> None:
#     """旧バージョンで既定フォルダだった presets/main の中身を presets 直下へ移動する。
#     main フォルダが空になったら削除し、以後は完全にルート運用にする。"""
#     legacy_dir = os.path.join(preset_root, "presets")
#     # if not os.path.isdir(legacy_dir):
#         # return

#     for entry in os.listdir(legacy_dir):
#         src = os.path.join(legacy_dir, entry)
#         dst = os.path.join(preset_root, entry)
#         if os.path.exists(dst):
#             # 同名のファイル/フォルダが既にルートにある場合は上書きせずそのまま残す
#             continue
#         try:
#             shutil.move(src, dst)
#         except Exception:
#             continue

#     try:
#         if not os.listdir(legacy_dir):
#             os.rmdir(legacy_dir)
#     except Exception:
#         pass


def _get_preset_root() -> str:
    """アドオン直下の presets フォルダの絶対パスを返す"""
    addon_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    preset_root = os.path.join(addon_root, "presets")
    
    # 存在しない場合のみ新規作成
    if not os.path.exists(preset_root):
        os.makedirs(preset_root)
        
    return preset_root

def _normalize_folder(folder: str) -> str:
    """フォルダパスを正規化する。空文字列は presets 直下（ルート）を表す。
    旧バージョンの既定フォルダだった "main" もルート扱いにして後方互換を保つ。"""
    folder = (folder or "").replace("\\", "/").strip("/")
    if folder == "presets":
        return ""
    return folder


class RETOUCH_PT_preset(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_preset"
    bl_label = "Preset"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        retouch = context.scene.retouch

        outer = layout.column(align=False)
        # outer.label(text="Preset", icon="PRESET")
        # outer.separator(factor=0.6)

        self._draw_save_row(outer, retouch)

        preset_root = _get_preset_root()

        current_folder = _normalize_folder(getattr(retouch, "retouch_preset_folder", ""))
        current_dir = self._resolve_current_dir(preset_root, current_folder)
        os.makedirs(current_dir, exist_ok=True)

        outer.separator(factor=1)
        self._draw_breadcrumbs(outer, current_folder)
        # outer.separator(factor=0.8)

        subfolders = _get_subfolders(current_dir)
        preset_files = _get_preset_files(current_dir)
        self._draw_browser(outer, current_folder, subfolders, preset_files)

    # --- 保存 / インポート行 -------------------------------------------------

    @staticmethod
    def _draw_save_row(layout, retouch):
        row = layout.row(align=True)
        row.scale_y = 1.2
        
        # テキスト入力を削除し、ボタンを押しやすく配置
        row.operator("retouch.save_preset", text="Save Preset", icon="NEWFOLDER")
        row.operator("retouch.import_preset", text="Import", icon="IMPORT")

    # --- フォルダパス解決 ------------------------------------------------------

    @staticmethod
    def _resolve_current_dir(preset_root, current_folder):
        if current_folder:
            return os.path.join(preset_root, current_folder)
        return preset_root

    # --- パンくずリスト（現在位置） -----------------------------------------------

    def _draw_breadcrumbs(self, layout, current_folder):
        row = layout.row()

        crumb = row.row(align=True)
        crumb.alignment = "LEFT"
        crumb.scale_y = 0.5

        home_op = crumb.operator("retouch.open_preset_folder", text="Presets", emboss=False)
        home_op.folder_path = ""

        if current_folder:
            parts = current_folder.split("/")
            accum = ""
            for part in parts:
                accum = f"{accum}/{part}" if accum else part
                crumb.label(text="", icon="RIGHTARROW_THIN")
                seg_op = crumb.operator("retouch.open_preset_folder", text=part, emboss=False)
                seg_op.folder_path = accum

        # 新規フォルダ作成ボタンは右端に配置
        action = row.row(align=True)
        action.alignment = "RIGHT"
        new_folder_op = action.operator("retouch.create_preset_folder", text="", icon="NEWFOLDER")
        new_folder_op.create_same_level = False

    # --- ファイルブラウザ風の一覧 --------------------------------------------------

    def _draw_browser(self, layout, current_folder, subfolders, preset_files):
        if not subfolders and not preset_files and not current_folder:
            layout.label(text="No presets yet", icon="INFO")
            return

        col = layout.column(align=False)

        # 一つ上の階層へ（ルート以外）
        if current_folder:
            parent = os.path.dirname(current_folder)
            up_row = col.row()
            up_row.scale_y = 1.1
            up_op = up_row.operator("retouch.open_preset_folder", text="...", icon="FILE_PARENT", emboss=False)
            up_op.folder_path = parent
            col.separator(factor=0.4)

        # フォルダ（先に表示、名前をクリックすると開く。削除ボタンは右端）
        for entry in subfolders:
            sub_path = f"{current_folder}/{entry}" if current_folder else entry

            row = col.row()
            row.scale_y = 1.15

            left = row.row(align=True)
            left.alignment = "LEFT"
            open_op = left.operator("retouch.open_preset_folder", text=entry, icon="FILE_FOLDER", emboss=False)
            open_op.folder_path = sub_path

            right = row.row(align=True)
            right.alignment = "RIGHT"
            delete_op = right.operator("retouch.delete_preset_folder", text="", icon="TRASH")
            delete_op.folder_path = sub_path

        if subfolders and preset_files:
            col.separator(factor=0.6)

        # プリセット（ファイル）：名前は表示のみ、右端のボタンを押して適用する
        for filename in preset_files:
            base_name = os.path.splitext(filename)[0]
            preset_name = self._to_full_preset_name(current_folder, base_name)

            row = col.row()
            row.scale_y = 1.15

            left = row.row(align=True)
            left.alignment = "LEFT"
            left.label(text=base_name, icon="PRESET")

            right = row.row(align=True)
            right.alignment = "RIGHT"

            # load_op = right.operator("retouch.load_preset", text="", icon="FILE_REFRESH")
            load_op = right.operator("retouch.load_preset", text="", icon="APPEND_BLEND")
            load_op.preset_name = preset_name

            export_op = right.operator("retouch.export_preset", text="", icon="EXPORT")
            export_op.preset_name = preset_name

            delete_op = right.operator("retouch.delete_preset", text="", icon="TRASH")
            delete_op.preset_name = preset_name

    @staticmethod
    def _to_full_preset_name(current_folder: str, base_name: str) -> str:
        """オペレーターに渡す preset_name（presetsフォルダからの相対パス）を組み立てる"""
        if current_folder:
            return f"{current_folder}/{base_name}"
        return base_name


classes = (RETOUCH_PT_preset,)