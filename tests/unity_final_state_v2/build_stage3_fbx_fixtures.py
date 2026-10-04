import argparse
import bpy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT.parent))

from tests.unity_final_state_v2.stage3_test_root import assert_owned_path, resolve_stage3_test_root


def blender_script_arguments():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


parser = argparse.ArgumentParser(description="Build synthetic Stage 3 FBX fixtures in an owned test root.")
parser.add_argument(
    "--test-root",
    default=os.environ.get("VAPB_STAGE3_TEST_ROOT"),
    help="existing marked disposable run root containing SourceProject and TargetProject",
)
args = parser.parse_args(blender_script_arguments())
if not args.test_root:
    parser.error("--test-root or VAPB_STAGE3_TEST_ROOT is required")

TEST_PATHS = resolve_stage3_test_root(args.test_root)
RUN_ROOT = TEST_PATHS.root
SOURCE_PROJECT = TEST_PATHS.source_project
FBX_ROOT = SOURCE_PROJECT / "Assets" / "SyntheticMaterialFixture" / "R2Stage3"
INPUT_ROOT = SOURCE_PROJECT / "FixtureInputs"
EVIDENCE_PATH = SOURCE_PROJECT / "stage3-fbx-fixture-evidence.json"
BLEND_PATH = INPUT_ROOT / "stage3_material_sources.blend"
SCRIPT_LOG = RUN_ROOT / "blender-fixture-build.log"
for owned_output in (FBX_ROOT, INPUT_ROOT, EVIDENCE_PATH, SCRIPT_LOG):
    assert_owned_path(owned_output, RUN_ROOT)


def repo_branch_sha():
    branch = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "branch", "--show-current"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout.strip()
    revision = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout.strip()
    return branch + "@" + revision
# Fail closed if this run''s planned output location already contains data.
if any(path.exists() for path in (FBX_ROOT, INPUT_ROOT, EVIDENCE_PATH, BLEND_PATH, SCRIPT_LOG)):
    raise RuntimeError("Stage3 fixture destination already exists; refusing to overwrite it")

# Import only the public package namespace needed for the existing Stage2 helper,
# avoiding addon registration side effects in the background fixture process.
if str(REPO_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT.parent))
pkg = types.ModuleType("vapb")
pkg.__path__ = [str(REPO_ROOT)]
pkg.__package__ = "vapb"
sys.modules["vapb"] = pkg
stage_module = importlib.import_module("vapb.export.final_state_package")
stage_fbx = stage_module._stage_fbx

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
context = bpy.context
source_objects = []
case_data = []

def property_value(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, "to_list"):
        return property_value(value.to_list())
    if isinstance(value, (list, tuple)):
        return [property_value(item) for item in value]
    try:
        return {str(key): property_value(value[key]) for key in value.keys()}
    except Exception:
        return repr(value)

def custom_props(block):
    return {str(key): property_value(block[key]) for key in sorted(block.keys())}

def digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def vector3(value):
    return [round(float(component), 9) for component in value]

def make_case(case_name, slot_identities, suffix):
    unique_identities = list(dict.fromkeys(slot_identities))
    materials_by_identity = {}
    for identity in unique_identities:
        material = bpy.data.materials.new("Source_%s_%s" % (case_name, identity))
        material.diffuse_color = {
            "A": (0.9, 0.1, 0.1, 1.0),
            "B": (0.1, 0.9, 0.1, 1.0),
            "C": (0.1, 0.1, 0.9, 1.0),
        }[identity]
        material["fixture_identity"] = identity
        material["fixture_origin"] = "VAPB_R2_STAGE3_PUBLIC_SYNTHETIC"
        materials_by_identity[identity] = material

    mesh = bpy.data.meshes.new("SourceMesh_%s" % case_name)
    vertices = [
        (0, 0, 0), (1, 0, 0), (0, 1, 0),
        (2, 0, 0), (3, 0, 0), (2, 1, 0),
        (4, 0, 0), (5, 0, 0), (4, 1, 0),
    ]
    mesh.from_pydata(vertices, [], [(0, 1, 2), (3, 4, 5), (6, 7, 8)])
    for identity in slot_identities:
        mesh.materials.append(materials_by_identity[identity])
    for polygon, slot_index in zip(mesh.polygons, range(len(slot_identities))):
        polygon.material_index = slot_index
    uv_layer = mesh.uv_layers.new(name="SyntheticUV")
    for polygon in mesh.polygons:
        for loop_index, uv in zip(polygon.loop_indices, ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))):
            uv_layer.data[loop_index].uv = uv

    obj = bpy.data.objects.new("SourceObject_%s" % case_name, mesh)
    scene.collection.objects.link(obj)
    obj["fixture_case"] = case_name
    obj["fixture_origin"] = "VAPB_R2_STAGE3_PUBLIC_SYNTHETIC"
    source_objects.append(obj)

    label_by_identity = {
        "A": "VAPB-MAT-" + "a" * 32,
        "B": "VAPB-MAT-" + "b" * 32,
        "C": "VAPB-MAT-" + "c" * 32,
    }
    material_ids_by_pointer = {
        materials_by_identity[identity].as_pointer(): label_by_identity[identity]
        for identity in unique_identities
    }
    expected_faces = [
        materials_by_identity[slot_identities[polygon.material_index]]["fixture_identity"]
        for polygon in mesh.polygons
    ]
    case_data.append({
        "case": case_name,
        "source_object": obj,
        "source_mesh": mesh,
        "materials_by_identity": materials_by_identity,
        "material_ids_by_pointer": material_ids_by_pointer,
        "label_by_identity": label_by_identity,
        "slot_identities": list(slot_identities),
        "expected_face_material_identities": expected_faces,
        "export_id": "VAPB-OBJ-" + suffix * 32,
    })

def snapshot_material(material):
    return {
        "name": material.name,
        "pointer": material.as_pointer(),
        "users": material.users,
        "diffuse_color": [round(float(v), 9) for v in material.diffuse_color],
        "use_nodes": bool(material.use_nodes),
        "custom_properties": custom_props(material),
    }

def snapshot_mesh(mesh):
    return {
        "name": mesh.name,
        "pointer": mesh.as_pointer(),
        "users": mesh.users,
        "vertices": [vector3(vertex.co) for vertex in mesh.vertices],
        "polygons": [
            {"vertices": list(poly.vertices), "material_index": int(poly.material_index)}
            for poly in mesh.polygons
        ],
        "material_slots": [
            {
                "material_name": material.name,
                "material_pointer": material.as_pointer(),
            }
            for material in mesh.materials
        ],
        "uv_layers": [
            {
                "name": layer.name,
                "active_render": bool(layer.active_render),
                "uvs": [[round(float(c), 9) for c in item.uv] for item in layer.data],
            }
            for layer in mesh.uv_layers
        ],
        "custom_properties": custom_props(mesh),
    }

def snapshot_object(obj):
    return {
        "name": obj.name,
        "pointer": obj.as_pointer(),
        "type": obj.type,
        "material_slots": [
            {
                "link": slot.link,
                "material_name": slot.material.name if slot.material else None,
                "material_pointer": slot.material.as_pointer() if slot.material else None,
            }
            for slot in obj.material_slots
        ],
        "data_name": obj.data.name if obj.data else None,
        "data_pointer": obj.data.as_pointer() if obj.data else None,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_world": [[round(float(c), 9) for c in row] for row in obj.matrix_world],
        "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
        "vertex_groups": [group.name for group in obj.vertex_groups],
        "selected": bool(obj.select_get()),
        "active_object": context.view_layer.objects.active.name if context.view_layer.objects.active else None,
        "custom_properties": custom_props(obj),
    }

def snapshot_case(item):
    obj = item["source_object"]
    mesh = item["source_mesh"]
    materials = item["materials_by_identity"]
    return {
        "object": snapshot_object(obj),
        "mesh": snapshot_mesh(mesh),
        "materials": {
            identity: snapshot_material(material)
            for identity, material in sorted(materials.items())
        },
        "object_sha256": digest(snapshot_object(obj)),
        "mesh_sha256": digest(snapshot_mesh(mesh)),
        "material_sha256": {
            identity: digest(snapshot_material(material))
            for identity, material in sorted(materials.items())
        },
        "slot_identities": list(item["slot_identities"]),
        "face_material_identities": [
            mesh.materials[polygon.material_index]["fixture_identity"]
            for polygon in mesh.polygons
        ],
    }

def datablock_counts():
    return {
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
    }

make_case("ABC", ("A", "B", "C"), "1")
make_case("ABA", ("A", "B", "A"), "2")
# Stable saved inputs contain the two untouched source cases, not stage carriers.
for obj in context.selected_objects:
    obj.select_set(False)
context.view_layer.objects.active = None
bpy.context.preferences.filepaths.save_version = 0
INPUT_ROOT.mkdir(parents=True, exist_ok=False)
BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
blend_save = bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
if blend_save != {"FINISHED"} or not BLEND_PATH.is_file():
    raise RuntimeError("Could not save synthetic Blender source fixtures")

cases_out = []
for item in case_data:
    obj = item["source_object"]
    for selected in tuple(context.selected_objects):
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj

    before = snapshot_case(item)
    counts_before = datablock_counts()
    output_path = FBX_ROOT / ("Stage3_%s.fbx" % item["case"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise RuntimeError("Fixture output exists; refusing to overwrite: " + str(output_path))

    stage_fbx(
        context,
        obj,
        item["export_id"],
        output_path,
        item["material_ids_by_pointer"],
    )

    after = snapshot_case(item)
    counts_after = datablock_counts()
    if before != after:
        raise AssertionError("%s source object/mesh/material state changed during _stage_fbx" % item["case"])
    if counts_before != counts_after:
        raise AssertionError("%s Blender datablock inventory changed during _stage_fbx: %r -> %r" %
                             (item["case"], counts_before, counts_after))
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise AssertionError("%s FBX is missing or empty" % item["case"])
    fbx_bytes = output_path.read_bytes()
    if item["export_id"].encode("ascii") not in fbx_bytes:
        raise AssertionError("%s FBX is missing its serialized Export ID" % item["case"])
    unique_labels = sorted(set(item["label_by_identity"][i] for i in item["slot_identities"]))
    missing_labels = [label for label in unique_labels if label.encode("ascii") not in fbx_bytes]
    if missing_labels:
        raise AssertionError("%s FBX is missing carrier labels: %r" % (item["case"], missing_labels))

    cases_out.append({
        "case": item["case"],
        "source": {
            "object_name": obj.name,
            "mesh_name": item["source_mesh"].name,
            "slot_identities": item["slot_identities"],
            "face_material_identities": item["expected_face_material_identities"],
            "object_sha256_before_after": [before["object_sha256"], after["object_sha256"]],
            "mesh_sha256_before_after": [before["mesh_sha256"], after["mesh_sha256"]],
            "material_sha256_before_after": {
                identity: [
                    before["material_sha256"][identity],
                    after["material_sha256"][identity],
                ]
                for identity in before["material_sha256"]
            },
            "full_source_snapshot_equal": before == after,
            "datablock_counts_before_after": [counts_before, counts_after],
        },
        "fbx": {
            "path": str(output_path),
            "size_bytes": output_path.stat().st_size,
            "sha256": hashlib.sha256(fbx_bytes).hexdigest(),
            "export_id": item["export_id"],
            "material_identity_labels": unique_labels,
            "serialized_export_id_present": True,
            "all_carrier_labels_present": True,
        },
    })

evidence = {
    "purpose": "Public synthetic Stage 3 native-FBX material-order fixture preparation",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "blender_version": bpy.app.version_string,
    "repo_branch_sha": repo_branch_sha(),
    "stage2_helper": "export/final_state_package.py::_stage_fbx",
    "source_blend": {
        "path": str(BLEND_PATH),
        "size_bytes": BLEND_PATH.stat().st_size,
        "sha256": hashlib.sha256(BLEND_PATH.read_bytes()).hexdigest(),
    },
    "cases": cases_out,
    "unity_apply_performed": False,
    "unity_test_framework_used": False,
}
EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
SCRIPT_LOG.write_text(
    "STAGE3_FIXTURE_BUILD_SUCCESS\n"
    "BLENDER_VERSION=" + bpy.app.version_string + "\n"
    "SOURCE_BLEND=" + str(BLEND_PATH) + "\n"
    "EVIDENCE=" + str(EVIDENCE_PATH) + "\n"
    + "\n".join(
        "%s path=%s bytes=%s sha256=%s source_hashes_unchanged=%s"
        % (row["case"], row["fbx"]["path"], row["fbx"]["size_bytes"],
           row["fbx"]["sha256"], row["source"]["full_source_snapshot_equal"])
        for row in cases_out
    )
    + "\n",
    encoding="utf-8",
)
print("STAGE3_FIXTURE_BUILD_SUCCESS")
print("STAGE3_FIXTURE_EVIDENCE=" + str(EVIDENCE_PATH))
