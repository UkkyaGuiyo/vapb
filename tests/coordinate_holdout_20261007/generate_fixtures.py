"""Generate fresh Blender 5.2.1 holdout FBXs after contract freeze.

Usage: blender --background --factory-startup --python generate_fixtures.py -- PREREG_DIR NEW_OUTPUT_DIR
The output directory must not exist. This script does not import prior captures.
"""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Euler
from io_scene_fbx.parse_fbx import parse as parse_fbx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import (CASES, EXPORT_CONTROLS, EXPECTED_RAW_UNIT_SCALE_FACTOR, GEOMETRY,
                      METADATA_TOLERANCE, public_contract, validate_contract)

ROOT = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def properties70(element):
    block = next((child for child in element.elems if child.id == b"Properties70"), None)
    result = {}
    for item in (block.elems if block else []):
        if item.id == b"P" and item.props:
            key = item.props[0].decode("utf-8")
            vals = [x.decode("utf-8") if isinstance(x, bytes) else x for x in item.props[4:]]
            result[key] = vals[0] if len(vals) == 1 else vals
    return result


def raw_material_rows(filepath):
    root, _ = parse_fbx(str(filepath))
    objects = next(x for x in root.elems if x.id == b"Objects")
    found = {}
    for element in objects.elems:
        if element.id != b"Material" or len(element.props) < 2:
            continue
        name = element.props[1].decode("utf-8", "strict").split("\x00", 1)[0].split("::")[-1]
        found[name] = int(element.props[0])
    rows = []
    for index, identity in enumerate(GEOMETRY["materials"]):
        name = "VAPB_HO_MATERIAL_%s" % chr(65 + index)
        if name not in found:
            raise RuntimeError("RAW_MATERIAL_IDENTITY_MISSING:" + name)
        rows.append({"name": name, "fixture_material_id": identity, "fbx_object_uid": found[name]})
    if len(found) != len(rows):
        raise RuntimeError("RAW_MATERIAL_SET_MISMATCH")
    return rows


def verify_preregistration(path):
    prereg_path = path / "preregistration.json"
    contract_path = path / "contract.json"
    oracle_path = path / "authored-oracle.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("schema") != "vapb-coordinate-holdout-preregistration-v1" or prereg.get("status") != "FROZEN_BEFORE_EXPORT_AND_IMPORT":
        raise RuntimeError("PREREGISTRATION_SCHEMA_OR_STATUS_INVALID")
    if sha256(contract_path) != prereg.get("contract_sha256") or sha256(oracle_path) != prereg.get("authored_oracle_sha256"):
        raise RuntimeError("PREREGISTRATION_ARTIFACT_HASH_MISMATCH")
    current = {p.name: sha256(p) for p in sorted(ROOT.glob("*.py")) if p.is_file()}
    if current != prereg.get("source_sha256"):
        raise RuntimeError("PREREGISTRATION_SOURCE_HASH_MISMATCH")
    if json.loads(contract_path.read_text(encoding="utf-8")) != public_contract():
        raise RuntimeError("PREREGISTERED_CONTRACT_CONTENT_MISMATCH")
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    if oracle.get("schema") != "vapb-coordinate-holdout-authored-oracle-v1":
        raise RuntimeError("PREREGISTERED_ORACLE_SCHEMA_INVALID")
    return prereg, sha256(prereg_path)


def main():
    errors = validate_contract()
    if errors:
        raise RuntimeError("INVALID_HOLDOUT_CONTRACT:" + ",".join(errors))
    if bpy.app.version_string != "5.2.1":
        raise RuntimeError("BLENDER_VERSION_MISMATCH:" + bpy.app.version_string)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit("EXPECTED_PREREGISTRATION_AND_NEW_OUTPUT_DIRECTORY")
    prereg, prereg_hash = verify_preregistration(Path(args[0]).resolve())
    out = Path(args[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest_cases = []
    for case in CASES:
        bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
        for group in (bpy.data.meshes, bpy.data.materials):
            for block in list(group):
                if block.users == 0: group.remove(block)
        mesh = bpy.data.meshes.new("VAPB_HO_Geometry")
        mesh.from_pydata(GEOMETRY["vertices"], [], [f["vertices"] for f in GEOMETRY["faces"]]); mesh.update()
        for index, identity in enumerate(GEOMETRY["materials"]):
            mat = bpy.data.materials.new("VAPB_HO_MATERIAL_%s" % chr(65 + index))
            mat["vapb_holdout_material_id"] = identity; mesh.materials.append(mat)
        for i, poly in enumerate(mesh.polygons): poly.material_index = i // 2
        uv = mesh.uv_layers.new(name="VAPB_HO_CORNER_ID")
        for i, face in enumerate(GEOMETRY["faces"]):
            for li, coord in zip(mesh.polygons[i].loop_indices, face["uvs"]): uv.data[li].uv = coord
        obj = bpy.data.objects.new("VAPB_HO_MESH", mesh); bpy.context.scene.collection.objects.link(obj)
        obj.location = case["location"]; obj.rotation_mode = "XYZ"
        obj.rotation_euler = Euler([v * 3.141592653589793 / 180 for v in case["rotation_degrees"]], "XYZ")
        obj.scale = case["scale"]; obj["vapb_holdout_case_id"] = case["id"]
        bpy.context.view_layer.objects.active = obj; obj.select_set(True)
        bpy.context.scene.unit_settings.system = case["unit_system"]
        bpy.context.scene.unit_settings.scale_length = case["unit_scale_length"]
        path = out / (case["id"] + ".fbx")
        result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
            object_types=set(EXPORT_CONTROLS["object_types"]), use_mesh_modifiers=False,
            use_custom_props=True, apply_scale_options="FBX_SCALE_UNITS", global_scale=1.,
            apply_unit_scale=True, axis_up=case["axis_up"], axis_forward=case["axis_forward"],
            bake_space_transform=False, bake_anim=False, add_leaf_bones=False, path_mode="AUTO")
        if "FINISHED" not in result or not path.is_file() or not path.stat().st_size:
            raise RuntimeError("FBX_EXPORT_FAILED:" + case["id"])
        root, version = parse_fbx(str(path))
        material_rows = raw_material_rows(path)
        glob = next(x for x in root.elems if x.id == b"GlobalSettings")
        settings = properties70(glob)
        axis = tuple(settings.get(k) for k in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign"))
        expected_axis = (1, 1, 2, 1, 0, 1) if case["axis_up"] == "Y" else (0, 1, 1, 1, 2, 1)
        if axis != expected_axis:
            raise RuntimeError("RAW_AXIS_METADATA_MISMATCH:%s:%r" % (case["id"], axis))
        manifest_cases.append({**case, "filename": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size,
                               "raw_fbx_version": version, "raw_global_settings": settings,
                               "raw_axis_tuple": list(axis),
                               "raw_unit_scale_factor": settings.get("UnitScaleFactor"),
                               "materials_by_fixture_identity": material_rows})
    base = float(manifest_cases[0]["raw_unit_scale_factor"])
    for row in manifest_cases:
        expected = EXPECTED_RAW_UNIT_SCALE_FACTOR[row["id"]]
        actual = float(row["raw_unit_scale_factor"])
        if not math.isfinite(actual) or abs(actual - expected) > abs(expected) * METADATA_TOLERANCE:
            raise RuntimeError("RAW_UNIT_METADATA_MISMATCH:%s:%r:%r" % (row["id"], actual, expected))
    manifest = {"schema": "vapb-coordinate-holdout-manifest-v1", "blender_version": bpy.app.version_string,
                "preregistration_sha256": prereg_hash,
                "contract_sha256": prereg["contract_sha256"],
                "authored_oracle_sha256": prereg["authored_oracle_sha256"],
                "source_sha256": prereg["source_sha256"],
                "contract": public_contract(), "cases": manifest_cases}
    mpath = out / "manifest.json"
    with mpath.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
    print("HOLDOUT_FIXTURES_CREATED=4")
    print("MANIFEST_SHA256=" + sha256(mpath))


if __name__ == "__main__": main()
