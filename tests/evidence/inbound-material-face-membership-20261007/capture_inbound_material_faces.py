"""Read-only Blender capture for the inbound Unity/FBX material partition diagnostic.

Run only in an allocated disposable Blender process. It never saves a .blend or exports.
All result writes use exclusive creation; all inputs are SHA pinned.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import traceback

import bpy

PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
UNITY_DIAGNOSTIC_SHA256 = "af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2"
CONFIRMED_BLEND_SHA256 = "58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c"
SOURCE_FBX_SHA256 = "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5"
SOURCE_FBX_META_SHA256 = "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d"
SOURCE_MESH_GUID = "abcdefabcdefabcdefabcdefabcdefab"
SOURCE_MESH_FILE_ID = "3538053534738119282"
SOURCE_PREFAB_GUID = "7cbdcbe81fde386408bcfb379e62b6bb"
SOURCE_FBX_MODEL_UID = 208084244
SOURCE_FBX_GEOMETRY_UID = 329684292
CONFIRMED_ROOT_CONTEXT_ID = "6d785054-f71b-4861-9ab9-d7a6901fd1f9"
CONFIRMED_OCCURRENCE_ID = "9c913bea517b84409aa7b7e28a7fccccdbf11b9104b154b50ba29615e4214694"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exclusive_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def unitypackage_asset(package_path: Path, unity_path: str) -> tuple[bytes, bytes]:
    matches = []
    with tarfile.open(package_path, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith("/pathname"):
                continue
            stream = archive.extractfile(member)
            if stream is None or stream.read().decode("utf-8", errors="replace").strip() != unity_path:
                continue
            prefix = member.name[:-len("/pathname")]
            asset_stream = archive.extractfile(prefix + "/asset")
            meta_stream = archive.extractfile(prefix + "/asset.meta")
            if asset_stream is None or meta_stream is None:
                raise AssertionError("unitypackage source asset or .meta is missing: " + unity_path)
            matches.append((asset_stream.read(), meta_stream.read()))
    if len(matches) != 1:
        raise AssertionError("unitypackage source pathname is not unique: " + unity_path)
    return matches[0]


def matrix_rows(matrix):
    return [[float(matrix[r][c]) for c in range(4)] for r in range(4)]


def vec(value):
    return [float(value.x), float(value.y), float(value.z)]


def identity(material):
    if material is None:
        return {"present": False, "package_id": "", "guid": "", "file_id": ""}
    return {
        "present": True,
        "package_id": str(material.get("unity_source_package_id", "")),
        "guid": str(material.get("unity_material_guid", "")).lower(),
        "file_id": str(material.get("unity_material_file_id", "")),
    }


def capture_mesh(obj, relative_matrix=None):
    obj.data.calc_loop_triangles()
    matrix = relative_matrix if relative_matrix is not None else obj.matrix_world.copy()
    triangles = []
    for triangle in obj.data.loop_triangles:
        polygon = obj.data.polygons[triangle.polygon_index]
        triangles.append({
            "material_index": int(polygon.material_index),
            "vertices": [int(i) for i in triangle.vertices],
            "corners": [vec(matrix @ obj.data.vertices[i].co) for i in triangle.vertices],
        })
    return {
        "object_type": obj.type,
        "source_asset_guid": str(obj.get("_vapb_fbx_source_asset_guid", "")).lower(),
        "source_asset_sha256": str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower(),
        "source_package_id": str(obj.get("unity_source_package_id", "")),
        "root_context_id": str(obj.get("_vapb_root_context_id", "")),
        "mesh_data_name_diagnostic_only": obj.data.name,
        "object_name_diagnostic_only": obj.name,
        "point_transform": matrix_rows(matrix),
        "triangle_count": len(triangles),
        "vertices_local": [vec(v.co) for v in obj.data.vertices],
        "triangles": triangles,
        "data_materials": [identity(m) for m in obj.data.materials],
        "object_slots": [{
            "link": slot.link,
            "identity": identity(slot.material),
        } for slot in obj.material_slots],
        "polygon_material_indices": [int(poly.material_index) for poly in obj.data.polygons],
        "renderer_binding_raw": str(obj.get("_vapb_renderer_binding", "")),
    }


def exact_renderer_mesh(package_root: Path):
    roots = [obj for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")]
    if len(roots) != 1:
        raise AssertionError("expected exactly one Renderer projection root")
    root = roots[0]
    payload = json.loads(str(root["_vapb_renderer_occurrences"]))
    records = payload.get("records", [])
    if len(records) != 1:
        raise AssertionError("expected exactly one Renderer occurrence")
    record = records[0]
    mesh = record.get("mesh", {})
    if (str(mesh.get("mesh_guid", "")).lower() != SOURCE_MESH_GUID
            or str(mesh.get("mesh_file_id", "")) != SOURCE_MESH_FILE_ID):
        raise AssertionError("Renderer mesh package/GUID/fileID differs from pinned source witness")

    from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
    candidates = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and str(obj.get("_vapb_root_context_id", "")) == str(root.get("_vapb_root_context_id", ""))
        and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == SOURCE_MESH_GUID
        and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower()
        == str(mesh.get("source_sha256", "")).lower()
        and validate_persistent_receipt(obj)
    ]
    if len(candidates) != 1:
        raise AssertionError("receipt-valid source mesh is not unique")
    return root, record, candidates[0]


def capture_face_meshes():
    return [capture_mesh(obj) for obj in bpy.context.scene.objects
            if obj.type == "MESH" and len(obj.data.polygons) > 0]


def plain_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "tolist"):
        return plain_value(value.tolist())
    if isinstance(value, (tuple, list)):
        return [plain_value(item) for item in value]
    if hasattr(value, "__iter__") and type(value).__module__ == "array":
        return [plain_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def fbx_source_table(source_fbx):
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(str(source_fbx), use_namedtuple=True)
    objects_nodes = [node for node in root.elems if node.id == b"Objects"]
    connection_nodes = [node for node in root.elems if node.id == b"Connections"]
    settings_nodes = [node for node in root.elems if node.id == b"GlobalSettings"]
    if len(objects_nodes) != 1 or len(connection_nodes) != 1 or len(settings_nodes) != 1:
        raise AssertionError("FBX GlobalSettings/Objects/Connections structure is ambiguous")
    objects = objects_nodes[0].elems
    by_uid = {node.props[0]: node for node in objects
              if node.props and type(node.props[0]) is int}
    if len(by_uid) != len(objects):
        raise AssertionError("FBX object UIDs are missing or duplicated")
    model = by_uid.get(SOURCE_FBX_MODEL_UID)
    geometry = by_uid.get(SOURCE_FBX_GEOMETRY_UID)
    if (model is None or model.id != b"Model"
            or geometry is None or geometry.id != b"Geometry"
            or len(geometry.props) < 3 or geometry.props[2] != b"Mesh"):
        raise AssertionError("pinned FBX Model/Geometry UIDs do not resolve")
    rows = [row for row in connection_nodes[0].elems
            if row.id == b"C" and row.props and row.props[0] == b"OO"]
    model_geometry_edges = [
        {"source_uid": int(row.props[1]), "destination_uid": int(row.props[2])}
        for row in rows if len(row.props) >= 3
        and int(row.props[1]) == SOURCE_FBX_GEOMETRY_UID
        and int(row.props[2]) == SOURCE_FBX_MODEL_UID
    ]
    if len(model_geometry_edges) != 1:
        raise AssertionError("pinned FBX Geometry��Model edge is not unique")
    material_connections = [
        {"material_uid": int(row.props[1]),
         "destination_model_uid": int(row.props[2])}
        for row in rows if len(row.props) >= 3
        and int(row.props[2]) == SOURCE_FBX_MODEL_UID
        and by_uid.get(row.props[1]) is not None
        and by_uid[row.props[1]].id == b"Material"
    ]

    def properties(node):
        containers = [child for child in node.elems if child.id == b"Properties70"]
        if len(containers) > 1:
            raise AssertionError("duplicate FBX Properties70 in pinned object")
        result = {}
        for row in containers[0].elems if containers else ():
            if row.id == b"P" and row.props:
                key = plain_value(row.props[0])
                if key in result:
                    raise AssertionError("duplicate FBX property: " + str(key))
                result[key] = plain_value(row.props[1:])
        return result

    geo_layers = []
    for layer in (child for child in geometry.elems if child.id == b"LayerElementMaterial"):
        entry = {}
        for child in layer.elems:
            entry[plain_value(child.id)] = plain_value(child.props)
        geo_layers.append(entry)
    global_properties = properties(settings_nodes[0])
    geometry_arrays = {}
    for child in geometry.elems:
        if child.id in (b"Vertices", b"PolygonVertexIndex"):
            geometry_arrays[plain_value(child.id)] = plain_value(child.props)
    return {
        "fbx_version": int(version),
        "global_settings_properties70": global_properties,
        "model_uid": SOURCE_FBX_MODEL_UID,
        "model_object_properties70": properties(model),
        "geometry_uid": SOURCE_FBX_GEOMETRY_UID,
        "geometry_object_kind": plain_value(geometry.props[2]),
        "geometry_vertices_and_polygon_indices": geometry_arrays,
        "geometry_layer_element_material": geo_layers,
        "model_geometry_connections": model_geometry_edges,
        "model_material_connections_in_file_order": material_connections,
        "coordinate_frame_note": (
            "Raw FBX native-import points are captured with Blender matrix_world. "
            "Unity source points are separately transformed by source_mesh_to_prefab_root "
            "and the explicit repository Unity-to-Blender basis; equality is asserted only "
            "if those independently declared frames match without fitting."
        ),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 7:
        raise SystemExit("usage: -- <product-addon-root> <source.unitypackage> <unity-diagnostic.json> <Input.fbx> <Input.fbx.meta> <confirmed.blend> <result.json>")
    product_root, package_path, unity_path, source_fbx, source_fbx_meta, blend_path, output = map(
        lambda item: Path(item).resolve(), args)
    addon_root = product_root / "unitypackage_blender_importer" if not (product_root / "__init__.py").is_file() else product_root
    tests_root = product_root / "tests"
    if not (tests_root / "strict_source_import.py").is_file():
        tests_root = addon_root.parent / "tests"
    if not (tests_root / "strict_source_import.py").is_file():
        raise FileNotFoundError("selected product checkout has no tests/strict_source_import.py")
    pins = {
        "package": (package_path, PACKAGE_SHA256),
        "unity_diagnostic": (unity_path, UNITY_DIAGNOSTIC_SHA256),
        "source_fbx": (source_fbx, SOURCE_FBX_SHA256),
        "source_fbx_meta": (source_fbx_meta, SOURCE_FBX_META_SHA256),
        "confirmed_blend": (blend_path, CONFIRMED_BLEND_SHA256),
    }
    if output.exists():
        raise FileExistsError(output)
    for label, (path, expected) in pins.items():
        if sha256(path) != expected:
            raise AssertionError(label + " SHA-256 pin mismatch")
    diagnostic = json.loads(unity_path.read_text(encoding="utf-8"))
    if diagnostic.get("status") != "DIAGNOSTIC_ONLY":
        raise AssertionError("Unity diagnostic is not DIAGNOSTIC_ONLY")
    report = {
        "status": "CAPTURE_FAILED",
        "read_only": True,
        "no_blend_save_or_fbx_export": True,
        "blender_version": bpy.app.version_string,
        "input_sha256": {key: sha256(value[0]) for key, value in pins.items()},
        "unity_source_mesh_guid": diagnostic.get("source_renderer_mesh_guid", ""),
        "unity_source_mesh_file_id": str(diagnostic.get("source_renderer_mesh_local_file_id", "")),
    }
    try:
        safety_path = tests_root / "evidence" / "confirmed_route_winding_20261007" / "confirmed_route_output_safety.py"
        spec = importlib.util.spec_from_file_location("_vapb_capture_safety", safety_path)
        if spec is None or spec.loader is None:
            raise ImportError("cannot load reviewed exclusive-output helper")
        safety = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(safety)
        safety.validate_output_path(output, [package_path, unity_path, source_fbx, source_fbx_meta, blend_path])
        if sha256(package_path) != PACKAGE_SHA256:
            raise AssertionError("package changed before capture")
        sys.path.insert(0, str(tests_root))
        from blender_three_slot_fixture_oracle import raw_prefab_material_refs
        fixture_raw_refs = raw_prefab_material_refs(package_path)
        diagnostic_refs = [
            {"guid": str(row.get("guid", "")).lower(),
             "file_id": str(row.get("local_file_id", ""))}
            for row in diagnostic.get("source_renderer_materials", [])
        ]
        if fixture_raw_refs != diagnostic_refs:
            raise AssertionError("pinned Unity diagnostic source material refs differ from raw fixture Prefab")
        input_fbx_payload, input_fbx_meta_payload = unitypackage_asset(
            package_path, "Assets/PublicMaterialSource/Input.fbx")
        prefab_path = str(diagnostic.get("source_prefab_path", ""))
        prefab_payload, prefab_meta_payload = unitypackage_asset(package_path, prefab_path)
        input_fbx_meta_text = input_fbx_meta_payload.decode("utf-8", errors="strict")
        prefab_meta_text = prefab_meta_payload.decode("utf-8", errors="strict")
        prefab_text = prefab_payload.decode("utf-8", errors="strict")
        mesh_meta_guid = re.search(r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", input_fbx_meta_text)
        prefab_meta_guid = re.search(r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", prefab_meta_text)
        renderer_guids = {str(row.get("target_renderer_guid", "")).lower()
                          for row in diagnostic.get("variant_material_overrides", [])}
        renderer_ids = {str(row.get("target_renderer_local_id", ""))
                        for row in diagnostic.get("variant_material_overrides", [])}
        renderer_docs = re.findall(
            r"(?ms)^---\s*!u!137\s+&(-?\d+)\s*\r?\n(.*?)(?=^---\s*!u!|\Z)",
            prefab_text)
        if len(renderer_docs) != 1:
            raise AssertionError("raw source Prefab does not contain exactly one serialized SkinnedMeshRenderer")
        renderer_doc_id, renderer_doc = renderer_docs[0]
        source_mesh_ref = re.search(
            r"(?m)^\s*m_Mesh:\s*\{\s*fileID:\s*(-?\d+)\s*,\s*guid:\s*([0-9a-fA-F]{32})",
            renderer_doc)
        if (hashlib.sha256(input_fbx_payload).hexdigest() != SOURCE_FBX_SHA256
                or input_fbx_payload != source_fbx.read_bytes()
                or hashlib.sha256(input_fbx_meta_payload).hexdigest() != SOURCE_FBX_META_SHA256
                or input_fbx_meta_payload != source_fbx_meta.read_bytes()
                or mesh_meta_guid is None or mesh_meta_guid.group(1).lower() != SOURCE_MESH_GUID
                or prefab_meta_guid is None or prefab_meta_guid.group(1).lower() != SOURCE_PREFAB_GUID
                or renderer_guids != {SOURCE_PREFAB_GUID} or renderer_ids != {renderer_doc_id}
                or not source_mesh_ref
                or source_mesh_ref.group(1) != SOURCE_MESH_FILE_ID
                or source_mesh_ref.group(2).lower() != SOURCE_MESH_GUID):
            raise AssertionError("source package/FBX/.meta/Prefab/Mesh content identity join failed")
        report["fixture_raw_prefab_material_refs"] = fixture_raw_refs
        report["unity_diagnostic_source_material_refs"] = diagnostic_refs
        report["source_revision_join"] = {
            "status": "PASS",
            "fixture_package_context_sha256": PACKAGE_SHA256,
            "unity_diagnostic_output_package_sha256": str(diagnostic.get("package_sha256", "")).lower(),
            "contexts_are_distinct": str(diagnostic.get("package_sha256", "")).lower() != PACKAGE_SHA256,
            "source_fbx_sha256": sha256(source_fbx),
            "source_fbx_meta_sha256": sha256(source_fbx_meta),
            "source_fbx_meta_guid": mesh_meta_guid.group(1).lower(),
            "source_prefab_path": prefab_path,
            "source_prefab_meta_guid": prefab_meta_guid.group(1).lower(),
            "source_renderer_file_id_from_unity_override": next(iter(renderer_ids)),
            "source_renderer_file_id_from_raw_prefab": renderer_doc_id,
            "source_mesh_guid": source_mesh_ref.group(2).lower(),
            "source_mesh_file_id": source_mesh_ref.group(1),
            "raw_prefab_material_refs": fixture_raw_refs,
            "source_prefab_asset_sha256": hashlib.sha256(prefab_payload).hexdigest(),
            "source_prefab_meta_sha256": hashlib.sha256(prefab_meta_payload).hexdigest(),
        }
        strict_path = tests_root / "strict_source_import.py"
        strict_spec = importlib.util.spec_from_file_location("_vapb_strict_source_import", strict_path)
        if strict_spec is None or strict_spec.loader is None:
            raise ImportError("cannot load strict source package loader")
        strict = importlib.util.module_from_spec(strict_spec)
        strict_spec.loader.exec_module(strict)
        addon = strict.load_source_package(addon_root)
        addon.register()

        # First capture the previously confirmed saved scene; never save it back.
        bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False, use_scripts=False)
        from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
        saved_candidates = []
        for obj in bpy.context.scene.objects:
            payload = obj.get("_vapb_renderer_binding")
            if not payload:
                continue
            binding = json.loads(str(payload))
            if binding.get("occurrence_id") == CONFIRMED_OCCURRENCE_ID:
                saved_candidates.append((obj, binding))
        if len(saved_candidates) != 1:
            raise AssertionError("confirmed saved source mesh is not uniquely receipt/binding selected")
        saved_mesh, saved_binding = saved_candidates[0]
        if saved_mesh.type != "MESH" or saved_binding.get("evidence") != "USER_CONFIRMED":
            raise AssertionError("confirmed saved binding does not select a Mesh")
        if str(saved_binding.get("root_context_id", "")) != CONFIRMED_ROOT_CONTEXT_ID:
            raise AssertionError("confirmed saved binding root context differs from pinned evidence")
        source_record = saved_binding.get("occurrence", {})
        source_mesh_ref = source_record.get("mesh", {})
        receipt_ref = saved_binding.get("mesh_receipt", {})
        package_id = "sha256:" + PACKAGE_SHA256
        if (source_record.get("occurrence_id") != CONFIRMED_OCCURRENCE_ID
                or str(source_mesh_ref.get("mesh_guid", "")).lower() != SOURCE_MESH_GUID
                or str(source_mesh_ref.get("mesh_file_id", "")) != SOURCE_MESH_FILE_ID
                or saved_binding.get("source_package_id") != package_id
                or receipt_ref.get("source_package_id") != package_id
                or str(receipt_ref.get("mesh_guid", "")).lower() != SOURCE_MESH_GUID
                or str(receipt_ref.get("mesh_file_id", "")) != SOURCE_MESH_FILE_ID
                or str(receipt_ref.get("source_sha256", "")).lower() != SOURCE_FBX_SHA256):
            raise AssertionError("saved binding occurrence and exact receipt identity join failed")
        saved_roots = [obj for obj in bpy.context.scene.objects
                       if obj.get("_vapb_renderer_occurrences")
                       and str(obj.get("_vapb_root_context_id", "")) ==
                       str(saved_mesh.get("_vapb_root_context_id", ""))]
        if len(saved_roots) != 1:
            raise AssertionError("confirmed saved scene root is not unique")
        from unitypackage_blender_importer.blender.renderer_binding import validate_existing_binding
        if validate_existing_binding(saved_binding, saved_roots[0], saved_mesh,
                                     tuple(bpy.data.objects)) != saved_binding:
            raise AssertionError("saved exact Renderer binding no longer validates")
        if not validate_persistent_receipt(saved_mesh):
            raise AssertionError("saved exact source mesh receipt no longer validates")
        saved_relative = saved_roots[0].matrix_world.inverted() @ saved_mesh.matrix_world
        report["confirmed_saved_scene"] = {
            "mesh": capture_mesh(saved_mesh, saved_relative),
            "root_count": len(saved_roots),
            "root_context_id": str(saved_mesh.get("_vapb_root_context_id", "")),
            "binding_occurrence": source_record,
            "mesh_receipt": receipt_ref,
        }

        # Capture raw Input.fbx through Blender's native importer in this same process.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        raw_import = bpy.ops.import_scene.fbx(filepath=str(source_fbx))
        if raw_import != {"FINISHED"}:
            raise AssertionError("native import of pinned Input.fbx did not finish")
        raw_meshes = capture_face_meshes()
        if not raw_meshes:
            raise AssertionError("pinned Input.fbx produced no native mesh")
        report["raw_input_fbx_native_import"] = raw_meshes
        report["raw_input_fbx_semantic_table"] = fbx_source_table(source_fbx)

        # Fresh factory scene, then the production package import and exact existing confirmation.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        source_storage = output.parent / "source_archive"
        if source_storage.exists():
            raise FileExistsError(source_storage)
        imported = bpy.ops.import_scene.unitypackage(
            filepath=str(package_path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
            use_materials=True, use_textures=True, keep_extracted=False,
            source_storage_directory=str(source_storage),
        )
        if imported != {"FINISHED"}:
            raise AssertionError("production package import did not finish: " + repr(imported))
        root, record, mesh = exact_renderer_mesh(addon_root)
        from unitypackage_blender_importer.blender.renderer_binding import validate_binding
        validate_binding(record, root, mesh, bpy.data.objects)
        relative = root.matrix_world.inverted() @ mesh.matrix_world
        before = capture_mesh(mesh, relative)
        bpy.context.scene.vapb_renderer_root = root
        bpy.context.scene.vapb_renderer_mesh = mesh
        result = bpy.ops.vapb.confirm_renderer_binding(
            occurrence_id=str(record["occurrence_id"]))
        after_relative = root.matrix_world.inverted() @ mesh.matrix_world
        after = capture_mesh(mesh, after_relative)
        report["package_import"] = {
            "operator_result": sorted(result),
            "root_context_id": str(root.get("_vapb_root_context_id", "")),
            "renderer_occurrence_id": str(record.get("occurrence_id", "")),
            "renderer_material_projection": [
                {"slot_index": int(index), "guid": str(value.get("guid", "")).lower(),
                 "file_id": str(value.get("file_id", ""))}
                for index, value in sorted(record.get("materials", {}).items(),
                                           key=lambda pair: int(pair[0]))
            ],
            "mesh_guid": str(mesh.get("_vapb_fbx_source_asset_guid", "")).lower(),
            "mesh_sha256": str(mesh.get("_vapb_fbx_source_asset_sha256", "")).lower(),
            "mesh_file_id": str(record.get("mesh", {}).get("mesh_file_id", "")),
            "receipt_valid": bool(validate_persistent_receipt(mesh)),
            "before_confirm": before,
            "after_confirm": after,
        }
        if result != {"FINISHED"}:
            raise AssertionError("existing confirm operator did not finish: " + repr(result))
        report["product_source_sha256"] = {}
        for relative_path in (
            "blender/renderer_binding.py",
            "blender/model_witness_bridge.py",
            "blender/dependency_resolver.py",
            "blender/hierarchy_builder.py",
            "operators/renderer_binding.py",
            "operators/export_unitypackage.py",
            "export/triangle_staging.py",
        ):
            path = addon_root / relative_path
            if path.is_file():
                report["product_source_sha256"][relative_path] = sha256(path)
        report["status"] = "CAPTURED"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["traceback"] = traceback.format_exc()
    try:
        report["input_sha256_postflight"] = {key: sha256(value[0]) for key, value in pins.items()}
        report["input_bytes_unchanged"] = report["input_sha256_postflight"] == report["input_sha256"]
        if not report["input_bytes_unchanged"] and report["status"] == "CAPTURED":
            report["status"] = "CAPTURE_FAILED"
            report["error"] = "input hash changed during read-only capture"
    except Exception as error:
        report["input_postflight_error"] = type(error).__name__ + ": " + str(error)
        report["input_bytes_unchanged"] = False
    exclusive_json(output, report)
    print("INBOUND_MATERIAL_FACE_CAPTURE_" + report["status"] + " " + json.dumps(
        {"output": str(output), "error": report.get("error", "")}, sort_keys=True))
    if report["status"] != "CAPTURED":
        raise RuntimeError(report.get("error", "capture failed"))


if __name__ == "__main__":
    main()

