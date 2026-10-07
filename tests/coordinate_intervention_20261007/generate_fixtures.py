"""Generate seven one-factor FBX inputs with Blender 5.2.

Usage: blender --background --factory-startup --python generate_fixtures.py -- OUTPUT_DIR
The output directory must not already exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Euler
from io_scene_fbx.parse_fbx import parse as parse_fbx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experiment_spec import (CASES, EXPORT_CONTROLS, GEOMETRY, public_spec,
                             validate_emitted_factor_metadata, validate_spec)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def output_argument() -> Path:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("EXPECTED_ONE_OUTPUT_DIRECTORY_ARGUMENT")
    return Path(args[0]).resolve()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)


def parse_raw_fbx(filepath: Path, material_ids: list[str]) -> dict:
    root, version = parse_fbx(str(filepath))
    objects = next(element for element in root.elems if element.id == b"Objects")
    globals_element = next(element for element in root.elems if element.id == b"GlobalSettings")

    def properties70(element):
        block = next((child for child in element.elems if child.id == b"Properties70"), None)
        if block is None:
            return {}
        values = {}
        for item in block.elems:
            if item.id == b"P" and item.props:
                key = item.props[0].decode("utf-8", "strict")
                raw_values = item.props[4:]
                decoded = [value.decode("utf-8", "strict") if isinstance(value, bytes) else value
                           for value in raw_values]
                values[key] = decoded[0] if len(decoded) == 1 else decoded
        return values

    raw_global = properties70(globals_element)
    raw_materials = {}
    for element in objects.elems:
        if element.id != b"Material" or len(element.props) < 2:
            continue
        name = element.props[1].decode("utf-8", "strict").split("\x00", 1)[0]
        name = name.split("::")[-1]
        raw_materials[name] = int(element.props[0])
    expected_names = ["VAPB_CI_MATERIAL_%s" % chr(ord("A") + index)
                      for index in range(len(material_ids))]
    if set(raw_materials) != set(expected_names):
        raise RuntimeError("RAW_FBX_MATERIAL_OBJECTS_MISMATCH:%s" % filepath.name)

    models = []
    for element in objects.elems:
        if element.id != b"Model" or len(element.props) < 2:
            continue
        name = element.props[1].decode("utf-8", "strict").split("\x00", 1)[0].split("::")[-1]
        models.append({"uid": int(element.props[0]), "name": name,
                       "properties": properties70(element)})
    if len(models) != 1:
        raise RuntimeError("RAW_FBX_MODEL_COUNT_MISMATCH:%s:%d" % (filepath.name, len(models)))
    material_rows = [{"name": name, "fixture_material_id": material_id,
                      "fbx_object_uid": raw_materials[name]}
                     for name, material_id in zip(expected_names, material_ids)]
    return {
        "fbx_version": version,
        "global_settings": raw_global,
        "model": models[0],
        "materials_by_fixture_identity": material_rows,
    }


def make_case(case: dict, destination: Path) -> dict:
    reset_scene()
    mesh = bpy.data.meshes.new("VAPB_CI_Geometry")
    mesh.from_pydata(GEOMETRY["vertices"], [], [face["vertices"] for face in GEOMETRY["faces"]])
    mesh.update()

    material_by_id = {}
    for material_index, material_id in enumerate(GEOMETRY["materials"]):
        name = "VAPB_CI_MATERIAL_%s" % chr(ord("A") + material_index)
        material = bpy.data.materials.new(name)
        material["vapb_fixture_material_id"] = material_id
        material_by_id[material_id] = material
        mesh.materials.append(material)

    for face_index, polygon in enumerate(mesh.polygons):
        polygon.material_index = face_index // 2
    uv_layer = mesh.uv_layers.new(name="VAPB_CI_CORNER_ID")
    for face_index, face in enumerate(GEOMETRY["faces"]):
        polygon = mesh.polygons[face_index]
        for loop_index, uv in zip(polygon.loop_indices, face["uvs"]):
            uv_layer.data[loop_index].uv = uv

    obj = bpy.data.objects.new("VAPB_CI_MESH", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = case["location"]
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = Euler([value * 3.141592653589793 / 180.0
                                for value in case["rotation_degrees"]], "XYZ")
    obj.scale = case["scale"]
    obj["vapb_coordinate_case_id"] = case["id"]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.context.scene.unit_settings.system = case["unit_system"]
    bpy.context.scene.unit_settings.scale_length = case["unit_scale_length"]

    filepath = destination / (case["id"] + ".fbx")
    result = bpy.ops.export_scene.fbx(
        filepath=str(filepath),
        use_selection=True,
        object_types=set(EXPORT_CONTROLS["object_types"]),
        use_mesh_modifiers=EXPORT_CONTROLS["use_mesh_modifiers"],
        use_custom_props=EXPORT_CONTROLS["use_custom_props"],
        apply_scale_options=EXPORT_CONTROLS["apply_scale_options"],
        global_scale=EXPORT_CONTROLS["global_scale"],
        apply_unit_scale=EXPORT_CONTROLS["apply_unit_scale"],
        axis_up=case["axis_up"],
        axis_forward=case["axis_forward"],
        bake_space_transform=EXPORT_CONTROLS["bake_space_transform"],
        bake_anim=EXPORT_CONTROLS["bake_anim"],
        add_leaf_bones=EXPORT_CONTROLS["add_leaf_bones"],
        path_mode="AUTO",
    )
    if "FINISHED" not in result or not filepath.is_file() or filepath.stat().st_size == 0:
        raise RuntimeError("FBX_EXPORT_FAILED:%s" % case["id"])

    raw_fbx = parse_raw_fbx(filepath, list(GEOMETRY["materials"]))
    return {
        **case,
        "filename": filepath.name,
        "sha256": sha256(filepath),
        "size_bytes": filepath.stat().st_size,
        "source_vertex_count": len(GEOMETRY["vertices"]),
        "source_triangle_count": len(GEOMETRY["faces"]),
        "source_material_names": [material.name for material in material_by_id.values()],
        "source_material_ids": list(GEOMETRY["materials"]),
        "source_material_id_by_name": {material.name: material["vapb_fixture_material_id"]
                                        for material in material_by_id.values()},
        "raw_fbx": raw_fbx,
        "source_material_fbx_uids": [row["fbx_object_uid"]
                                      for row in raw_fbx["materials_by_fixture_identity"]],
    }


def main() -> None:
    errors = validate_spec()
    if errors:
        raise RuntimeError("INVALID_INTERVENTION_SPEC:" + ",".join(errors))
    destination = output_argument()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    records = [make_case(case, destination) for case in CASES]
    emitted_errors = validate_emitted_factor_metadata(records)
    if emitted_errors:
        raise RuntimeError("RAW_FBX_FACTOR_VALIDATION_FAILED:" + ",".join(emitted_errors))
    manifest = {
        "schema": "vapb-coordinate-intervention-manifest-v1",
        "blender_version": bpy.app.version_string,
        "exporter": "Blender io_scene_fbx",
        "spec": public_spec(),
        "cases": records,
    }
    manifest_path = destination / "manifest.json"
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(manifest_text)
    print("VAPB_COORDINATE_FIXTURE_GENERATION_PASS cases=%d" % len(records))
    print("MANIFEST_SHA256=" + sha256(manifest_path))


if __name__ == "__main__":
    main()
