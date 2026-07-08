import json
import os
import pickle
import re

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator

from ..utils.compositor import ensure_compositor_nodes

IGNORED_NODE_TYPES = {"IMAGE", "VIEWER", "GROUP_OUTPUT"}


def _get_preset_dir() -> str:
    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    preset_dir = os.path.join(addon_dir, "presets")
    os.makedirs(preset_dir, exist_ok=True)
    return preset_dir


def _get_preset_extension() -> str:
    return ".brp"


def _get_preset_path(preset_name: str) -> str:
    return os.path.join(_get_preset_dir(), f"{_sanitize_preset_name(preset_name)}{_get_preset_extension()}")


def _sanitize_preset_name(name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "preset").strip("._-")
    return safe_name or "preset"


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

        for point_index, point_data in enumerate(points_data):
            try:
                x, y = point_data
                if point_index < len(curve.points):
                    curve.points[point_index].location = (float(x), float(y))
                else:
                    curve.points.new(float(x), float(y))
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
    bl_description = "Save the current compositor node values as a JSON preset"

    preset_name: StringProperty(name="Preset Name", default="")

    def execute(self, context):
        scene = context.scene
        preset_name = _sanitize_preset_name(self.preset_name or getattr(getattr(scene, "retouch", None), "retouch_preset_name", ""))
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        tree = ensure_compositor_nodes(scene)
        payload = _capture_preset(tree)
        payload["name"] = preset_name
        path = _get_preset_path(preset_name)
        _write_preset_file(path, payload)
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
    preset_name: StringProperty(default="")

    def invoke(self, context, event):
        preset_name = _sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        self.filepath = f"{preset_name}{_get_preset_extension()}"
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
    RETOUCH_OT_delete_preset,
    RETOUCH_OT_export_preset,
    RETOUCH_OT_import_preset,
)
