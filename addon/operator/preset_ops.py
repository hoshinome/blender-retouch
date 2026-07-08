import json
import os
import pickle
import re
import shutil

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator

from ..utils.compositor import ensure_compositor_nodes

IGNORED_NODE_TYPES = {"IMAGE", "VIEWER", "GROUP_OUTPUT"}


def _get_preset_dir() -> str:
    """アドオン直下の presets フォルダの絶対パスを返す"""
    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    preset_dir = os.path.join(addon_dir, "presets")
    
    # 存在しない場合のみ新規作成
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
        
    return preset_dir


def _normalize_folder(folder: str) -> str:
    folder = (folder or "").replace("\\", "/").strip("/")
    return folder


def _get_preset_extension() -> str:
    return ".brp"


def _get_preset_path(preset_name: str) -> str:
    safe_name = _sanitize_preset_name(preset_name)
    preset_dir = _get_preset_dir()

    if "/" in safe_name:
        folder_parts = safe_name.split("/")[:-1]
        file_name = safe_name.split("/")[-1]
        target_dir = os.path.join(preset_dir, *folder_parts)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{file_name}{_get_preset_extension()}")

    default_path = os.path.join(preset_dir, f"{safe_name}{_get_preset_extension()}")
    return default_path


def _sanitize_preset_name(name: str) -> str:
    if not name:
        return "preset"

    parts = []
    for raw_part in str(name).replace("\\", "/").split("/"):
        if not raw_part or raw_part in {".", ".."}:
            continue
        safe_part = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_part).strip("._-")
        parts.append(safe_part or "preset")

    if not parts:
        return "preset"
    return "/".join(parts)


def _serialize_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if hasattr(value, "to_list"):
        try:
            return [_serialize_value(v) for v in value.to_list()]
        except Exception:
            pass
    if hasattr(value, "to_tuple"):
        try:
            return [_serialize_value(v) for v in value.to_tuple()]
        except Exception:
            pass
    if hasattr(value, "__len__") and not hasattr(value, "bl_rna"):
        try:
            return [_serialize_value(v) for v in value]
        except TypeError:
            return None
    return None


def _serialize_curve_mapping(mapping) -> dict:
    if not mapping:
        return {}

    curves_data = []
    for curve in getattr(mapping, "curves", []):
        points = []
        for point in getattr(curve, "points", []):
            try:
                location = point.location
                points.append([float(location[0]), float(location[1])])
            except Exception:
                continue
        curves_data.append({"points": points})

    payload = {"type": "CurveMapping", "curves": curves_data}
    for attr in ("black_level", "white_level"):
        try:
            value = getattr(mapping, attr)
        except Exception:
            continue
        if value is None:
            continue
        try:
            payload[attr] = list(value)
        except TypeError:
            payload[attr] = value

    for attr in ("clip", "use_clip"):
        try:
            payload[attr] = bool(getattr(mapping, attr))
        except Exception:
            continue

    return payload


def _restore_curve_mapping(mapping, data: dict) -> None:
    if not mapping or not isinstance(data, dict):
        return

    for attr in ("black_level", "white_level"):
        if attr not in data:
            continue
        try:
            setattr(mapping, attr, data[attr])
        except Exception:
            continue

    for attr in ("clip", "use_clip"):
        if attr in data:
            try:
                setattr(mapping, attr, bool(data[attr]))
            except Exception:
                continue

    curves_data = data.get("curves", [])
    curves = getattr(mapping, "curves", None)
    if not curves or not curves_data:
        return

    count = min(len(curves), len(curves_data))
    for index in range(count):
        curve = curves[index]
        curve_data = curves_data[index]
        points_data = curve_data.get("points", [])

        if not points_data:
            continue

        # --- 修正箇所: 既存のポイントを一度クリア（逆順に削除） ---
        for p_idx in range(len(curve.points) - 1, -1, -1):
            try:
                curve.points.remove(curve.points[p_idx])
            except Exception:
                # Blenderの仕様で消せない最小限のポイント（通常2点）はスルー
                pass

        # --- プリセットデータの適用 ---
        for point_index, point_data in enumerate(points_data):
            try:
                x, y = float(point_data[0]), float(point_data[1])
                
                # 残ってしまった既存ポイントがある場合は位置を上書き、なければ新規追加
                if point_index < len(curve.points):
                    curve.points[point_index].location = (x, y)
                else:
                    curve.points.new(x, y)
            except Exception:
                continue

    try:
        mapping.update()
    except Exception:
        pass


def _serialize_node(node: bpy.types.Node) -> dict:
    data = {
        "name": node.name,
        "type": node.bl_idname,
        "label": node.label,
        "location": [node.location.x, node.location.y],
        "inputs": [],
        "properties": {},
    }

    for socket in node.inputs:
        default_value = getattr(socket, "default_value", None)
        data["inputs"].append(
            {
                "name": socket.name,
                "identifier": socket.identifier,
                "default_value": _serialize_value(default_value),
            }
        )

    for prop in node.bl_rna.properties:
        if prop.identifier in {"name", "label", "location", "inputs", "outputs", "type", "parent", "id_data"}:
            continue
        try:
            value = getattr(node, prop.identifier)
        except Exception:
            continue
        if value is None:
            continue
        if prop.identifier == "mapping" and getattr(getattr(value, "bl_rna", None), "identifier", None) == "CurveMapping":
            data["properties"][prop.identifier] = _serialize_curve_mapping(value)
            continue
        if prop.identifier.startswith("_") or prop.is_readonly:
            continue
        if hasattr(value, "bl_rna") and not isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, (str, int, float, bool)):
            data["properties"][prop.identifier] = value
            continue
        serialized = _serialize_value(value)
        if serialized is not None:
            data["properties"][prop.identifier] = serialized

    return data


def _capture_preset(tree: bpy.types.NodeTree | None) -> dict:
    if tree is None:
        return {"version": 1, "nodes": []}

    return {
        "version": 1,
        "nodes": [
            _serialize_node(node)
            for node in tree.nodes
            if getattr(node, "bl_idname", None) and node.type not in IGNORED_NODE_TYPES
        ],
    }


def _write_preset_file(path: str, payload: dict) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".pkl", ".pickle"}:
        with open(path, "wb") as handle:
            pickle.dump(payload, handle, protocol=4)
        return

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _load_preset_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None

    ext = os.path.splitext(path)[1].lower()
    if ext in {".pkl", ".pickle"}:
        with open(path, "rb") as handle:
            return pickle.load(handle)

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _restore_node_state(node: bpy.types.Node, node_data: dict) -> None:
    if node_data.get("location"):
        try:
            node.location = tuple(node_data["location"])
        except Exception:
            pass

    input_lookup = {socket.identifier: socket for socket in node.inputs}
    input_lookup.update({socket.name: socket for socket in node.inputs})

    for socket_data in node_data.get("inputs", []):
        socket = input_lookup.get(socket_data.get("identifier")) or input_lookup.get(socket_data.get("name"))
        if socket is None:
            continue
        if "default_value" in socket_data and socket_data["default_value"] is not None:
            try:
                if hasattr(socket, "default_value"):
                    socket.default_value = socket_data["default_value"]
            except Exception:
                pass

    for prop_name, value in node_data.get("properties", {}).items():
        if prop_name == "mapping" and isinstance(value, dict):
            try:
                _restore_curve_mapping(getattr(node, prop_name, None), value)
            except Exception:
                continue
            continue
        try:
            setattr(node, prop_name, value)
        except Exception:
            continue


class RETOUCH_OT_save_preset(Operator):
    bl_idname = "retouch.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the current compositor node values as a preset"

    preset_name: StringProperty(name="Preset Name", default="")

    def invoke(self, context, event):
        # ポップアップを開くたびに入力欄を空にする（またはデフォルト名を入れる）
        self.preset_name = ""
        # 幅250ピクセルのプロパティダイアログ（ポップアップ）を表示
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        # ポップアップ内の入力フィールド
        layout.prop(self, "preset_name", text="Name")

    def execute(self, context):
        scene = context.scene
        retouch_props = getattr(scene, "retouch", None)
        
        # ポップアップで入力された名前を使用する
        preset_name = _sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        folder = _normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
        
        tree = ensure_compositor_nodes(scene)
        payload = _capture_preset(tree)
        payload["name"] = preset_name
        target_path = _get_preset_path(f"{folder}/{preset_name}" if folder else preset_name)
        _write_preset_file(target_path, payload)
        
        # 保存が終わったらUI側のテキストボックス（あれば）もクリアするか同期
        if retouch_props and hasattr(retouch_props, "retouch_preset_name"):
            retouch_props.retouch_preset_name = ""
            
        self.report({"INFO"}, f"Saved preset: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_load_preset(Operator):
    bl_idname = "retouch.load_preset"
    bl_label = "Load Preset"
    bl_description = "Load a saved compositor preset"

    preset_name: StringProperty(name="Preset Name", default="")

    def execute(self, context):
        scene = context.scene
        preset_name = _sanitize_preset_name(self.preset_name or getattr(getattr(scene, "retouch", None), "retouch_preset_name", ""))
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        tree = ensure_compositor_nodes(scene)
        path = _get_preset_path(preset_name)
        payload = _load_preset_file(path)
        if payload is None:
            self.report({"ERROR"}, f"Preset not found: {preset_name}")
            return {"CANCELLED"}

        node_lookup = {node.name: node for node in tree.nodes}
        for node_data in payload.get("nodes", []):
            node_name = node_data.get("name")
            node = node_lookup.get(node_name)
            if node is None:
                try:
                    node = tree.nodes.new(type=node_data.get("type", "NodeReroute"))
                    node.name = node_name
                    node.label = node_data.get("label", node_name)
                except Exception:
                    continue
            _restore_node_state(node, node_data)
            node_lookup[node_name] = node

        self.report({"INFO"}, f"Loaded preset: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_create_preset_folder(Operator):
    bl_idname = "retouch.create_preset_folder"
    bl_label = "Create Folder"
    bl_description = "Create a new preset folder"

    folder_name: StringProperty(name="Folder Name", default="")
    create_same_level: BoolProperty(default=False)

    def invoke(self, context, event):
        self.folder_name = ""
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_name", text="Name")

    def execute(self, context):
        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is None:
            return {"CANCELLED"}

        folder_name = _sanitize_preset_name(self.folder_name)
        if not folder_name:
            self.report({"ERROR"}, "Folder name is empty.")
            return {"CANCELLED"}

        current_folder = _normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
        base_folder = current_folder
        if self.create_same_level:
            base_folder = os.path.dirname(current_folder) if current_folder else ""

        new_folder = f"{base_folder}/{folder_name}" if base_folder else folder_name
        target_dir = os.path.join(_get_preset_dir(), *new_folder.split("/"))

        os.makedirs(target_dir, exist_ok=True)
        retouch_props.retouch_preset_folder = new_folder
        self.report({"INFO"}, f"Created folder: {folder_name}")
        return {"FINISHED"}


class RETOUCH_OT_open_preset_folder(Operator):
    bl_idname = "retouch.open_preset_folder"
    bl_label = "Open Folder"
    bl_description = "Open a preset folder"

    folder_path: StringProperty(default="")

    def execute(self, context):
        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is None:
            return {"CANCELLED"}
        retouch_props.retouch_preset_folder = _normalize_folder(self.folder_path)
        return {"FINISHED"}


class RETOUCH_OT_delete_preset_folder(Operator):
    bl_idname = "retouch.delete_preset_folder"
    bl_label = "Delete Folder"
    bl_description = "Delete a preset folder and everything inside it"

    folder_path: StringProperty(name="Folder Path", default="")
    confirmed: BoolProperty(default=False)

    def invoke(self, context, event):
        if self.confirmed:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Delete folder '{self.folder_path}'?", icon="ERROR")

    def execute(self, context):
        folder_path = _normalize_folder(self.folder_path)
        if not folder_path:
            self.report({"ERROR"}, "Cannot delete the presets root folder.")
            return {"CANCELLED"}

        safe_path = _sanitize_preset_name(folder_path)
        target_dir = os.path.join(_get_preset_dir(), safe_path)

        if not os.path.isdir(target_dir):
            self.report({"WARNING"}, f"Folder not found: {folder_path}")
            return {"CANCELLED"}

        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to delete folder: {e}")
            return {"CANCELLED"}

        # 削除したフォルダの中にいた場合は、親フォルダ（またはpresetsルート）へ移動する
        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is not None:
            current_folder = _normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
            if current_folder == folder_path or current_folder.startswith(f"{folder_path}/"):
                retouch_props.retouch_preset_folder = os.path.dirname(folder_path)

        self.report({"INFO"}, f"Deleted folder: {folder_path}")
        return {"FINISHED"}


class RETOUCH_OT_delete_preset(Operator):
    bl_idname = "retouch.delete_preset"
    bl_label = "Delete Preset"
    bl_description = "Delete a saved compositor preset"

    preset_name: StringProperty(name="Preset Name", default="")
    confirmed: BoolProperty(default=False)

    def invoke(self, context, event):
        if self.confirmed:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Delete preset '{self.preset_name}'?")
        row = layout.row(align=True)
        # op = row.operator("retouch.delete_preset", text="Delete", icon="TRASH")
        # op.preset_name = self.preset_name
        # op.confirmed = True
        # row.operator("ui.eyedropper_color", text="Cancel")

    def execute(self, context):
        preset_name = _sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        path = _get_preset_path(preset_name)
        if os.path.exists(path):
            os.remove(path)
            self.report({"INFO"}, f"Deleted preset: {preset_name}")
        else:
            self.report({"WARNING"}, f"Preset not found: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_export_preset(Operator, ExportHelper):
    bl_idname = "retouch.export_preset"
    bl_label = "Export Preset"
    bl_description = "Export a preset .brp file"

    filename_ext = _get_preset_extension()
    filter_glob: StringProperty(default="*.brp", options={"HIDDEN"})
    preset_name: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        preset_name = _sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        base_name = os.path.basename(os.path.normpath(preset_name)) or "preset"
        self.filepath = f"{base_name}{_get_preset_extension()}"
        return super().invoke(context, event)

    def execute(self, context):
        preset_name = _sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        source_path = _get_preset_path(preset_name)
        if not os.path.exists(source_path):
            self.report({"ERROR"}, f"Preset not found: {preset_name}")
            return {"CANCELLED"}

        filepath = self.filepath
        if not filepath.lower().endswith(_get_preset_extension()):
            filepath = f"{filepath}{_get_preset_extension()}"

        try:
            with open(source_path, "r", encoding="utf-8") as src:
                payload = src.read()
            with open(filepath, "w", encoding="utf-8") as dst:
                dst.write(payload)
            self.report({"INFO"}, f"Exported preset: {preset_name}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}


class RETOUCH_OT_import_preset(Operator, ImportHelper):
    bl_idname = "retouch.import_preset"
    bl_label = "Import Preset"
    bl_description = "Import a preset .brp file"

    filename_ext = _get_preset_extension()
    filter_glob: StringProperty(default="*.brp", options={"HIDDEN"})
    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        if not self.filepath.lower().endswith(_get_preset_extension()):
            self.report({"ERROR"}, f"Only {_get_preset_extension()} files are supported.")
            return {"CANCELLED"}

        try:
            payload = _load_preset_file(self.filepath)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to import preset: {e}")
            return {"CANCELLED"}

        preset_name = _sanitize_preset_name(payload.get("name", os.path.splitext(os.path.basename(self.filepath))[0]))
        dest_path = _get_preset_path(preset_name)
        _write_preset_file(dest_path, payload)

        self.report({"INFO"}, f"Imported preset: {preset_name}")
        return {"FINISHED"}


classes = (
    RETOUCH_OT_save_preset,
    RETOUCH_OT_load_preset,
    RETOUCH_OT_create_preset_folder,
    RETOUCH_OT_open_preset_folder,
    RETOUCH_OT_delete_preset_folder,
    RETOUCH_OT_delete_preset,
    RETOUCH_OT_export_preset,
    RETOUCH_OT_import_preset,
)