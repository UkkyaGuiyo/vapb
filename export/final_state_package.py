"""One static Blender final-state Mesh plus its selected Unity Material closure."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from dataclasses import replace

from .fbx_export import FBX_EXPORT_PRESET
from .triangle_staging import frozen_export_meshes
from .manifest import ExportManifest, GeneratorInfo, SCHEMA_VERSION
from .package_writer import UnityPackageWriter
from .raw_assets import RawAssetRepository
from .staging import StagedUnityAsset, StagingTree
from ..blender.identity_registry import load_scene_registry
from ..unity.asset_database import AssetDatabase
from ..unity.material_parser import parse_material
from ..unity.identity import select_package_provider
from .material_naming import allocate_material_paths
from ..blender.material_owner_usage import proven_owners


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _id(block, prefix: str, key: str, collection) -> str:
    current = str(block.get(key, ""))
    if current:
        if not re.fullmatch(prefix + r"[0-9a-f]{32}", current):
            raise ValueError("invalid VAPB Export ID")
        if any(other is not block and other.get(key) == current for other in collection):
            raise ValueError("duplicate VAPB Export ID")
        return current
    return prefix + uuid4().hex


def _material_data(payload: bytes):
    with tempfile.TemporaryDirectory(prefix="vapb_material_refs_") as temporary:
        root = Path(temporary)
        path = root / "Material.mat"
        path.write_bytes(payload)
        material = parse_material(path, AssetDatabase(root), strict_references=True)
    return material


def _material_texture_guids(payload: bytes) -> set[str]:
    return {reference.guid for reference in _material_data(payload).textures.values() if reference.file_id != 0}


def _source_assets(scene, package_id: str):
    package = load_scene_registry(scene).packages.get(package_id)
    if not package:
        raise ValueError("source Material package is unavailable")
    archive = Path(package["source_archive_path"])
    payload = archive.read_bytes()
    if package_id != "sha256:" + _sha(payload) or package["package_sha256"] != _sha(payload):
        raise ValueError("source Material package revision changed")
    return {asset.guid: asset for asset in RawAssetRepository(archive).read_all(payload)}


def _resolve_source_asset(scene, consumer_package_id: str, guid: str, cache=None):
    cache = {} if cache is None else cache
    def assets(package_id):
        if package_id not in cache:
            cache[package_id] = _source_assets(scene, package_id)
        return cache[package_id]
    local = assets(consumer_package_id).get(guid)
    if local is not None:
        return local
    candidates = []
    for package_id in load_scene_registry(scene).packages:
        if package_id != consumer_package_id:
            source = assets(package_id).get(guid)
            if source is not None:
                candidates.append((package_id, source))
    status, provider = select_package_provider(candidates, consumer_package_id)
    if provider is None:
        raise ValueError("dependency provider " + status)
    return provider


def _shader_dependency(scene, package_id, data, cache):
    if (not isinstance(data.shader_file_id, int) or isinstance(data.shader_file_id, bool)
            or not -(2 ** 63) <= data.shader_file_id < 2 ** 63
            or not data.shader_file_id or not re.fullmatch(r"[0-9a-f]{32}", data.shader_guid)
            or data.shader_guid == '0' * 32):
        raise ValueError("INVALID_REFERENCE")
    if data.shader_guid == "0000000000000000f000000000000000" and data.shader_file_id == 46:
        return {"classification": "UNITY_BUILTIN", "guid": data.shader_guid,
                "file_id": str(data.shader_file_id)}, None
    deferred = {"classification": "UNRESOLVED_BUT_PRESERVED", "kind": "SHADER",
        "reference_id": "VAPB-REF-" + _sha(f"SHADER:{data.shader_guid}:{data.shader_file_id}".encode())[:32],
        "guid": data.shader_guid, "file_id": str(data.shader_file_id),
        "status": "UNRESOLVED_BUT_PRESERVED"}
    try:
        source = _resolve_source_asset(scene, package_id, data.shader_guid, cache)
    except ValueError as error:
        if str(error) != "dependency provider UNRESOLVED":
            raise
        return deferred, None
    if (data.shader_file_id != 4800000 or not source.pathname.lower().endswith('.shader')
            or not re.search(rb"(?m)^ShaderImporter:\s*$", source.meta_bytes)):
        raise ValueError("Shader provider identity is unsupported")
    text = source.asset_bytes.decode('utf-8-sig')
    fallbacks = re.findall(r'\bFallback\s+(\S+)', text, re.IGNORECASE)
    if (re.search(r"#\s*include\b|\bUsePass\b", text)
            or any(value.lower() != 'off' for value in fallbacks)
            or any(int(value) != 0 for value in re.findall(rb"fileID:\s*(-?\d+)\b", source.meta_bytes))):
        return deferred, None
    return {"classification": "PACKAGE_PROVIDER", "guid": data.shader_guid,
            "file_id": str(data.shader_file_id)}, source


def _stage_fbx(context, mesh, export_id: str, output: Path) -> None:
    import bpy  # type: ignore

    selected_before = tuple(context.selected_objects)
    active_before = context.view_layer.objects.active
    copied = mesh.copy()
    copied.data = mesh.data.copy()
    try:
        copied.parent = None
        copied.matrix_world = mesh.matrix_world.copy()
        copied.animation_data_clear()
        for block in (copied, copied.data):
            for key in list(block.keys()):
                del block[key]
        copied["_vapb_export_object_id"] = export_id
        context.scene.collection.objects.link(copied)
        for obj in selected_before:
            obj.select_set(False)
        context.view_layer.objects.active = copied
        options = dict(FBX_EXPORT_PRESET)
        options.update(filepath=str(output), path_mode="STRIP", object_types={"MESH"},
                       use_selection=True, use_custom_props=True)
        copied.select_set(True)
        with frozen_export_meshes([copied]):
            if bpy.ops.export_scene.fbx(**options) != {"FINISHED"} or not output.is_file():
                raise ValueError("final-state FBX export failed")
        if b"_vapb_export_object_id" not in output.read_bytes() or export_id.encode() not in output.read_bytes():
            raise ValueError("final-state FBX lost the Export ID")
    finally:
        data = copied.data
        bpy.data.objects.remove(copied, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)
        for obj in selected_before:
            obj.select_set(True)
        context.view_layer.objects.active = active_before


def export_final_state_package(context, mesh, output: Path):
    """Create a new FBX and selected Unity Material/Texture assets; no source Mesh receipt."""
    import bpy  # type: ignore

    output = Path(output)
    if output.exists() or mesh is None or mesh.type != "MESH" or context.mode != "OBJECT":
        raise ValueError("select one static Mesh and an unused output path")
    if mesh.data.shape_keys is not None or mesh.modifiers or not mesh.data.uv_layers:
        raise ValueError("this first final-state route requires a static UV Mesh")
    if not mesh.material_slots or any(slot.material is None for slot in mesh.material_slots):
        raise ValueError("each current Mesh material slot needs a Unity-derived Material")
    object_id = _id(mesh, "VAPB-OBJ-", "_vapb_export_object_id", bpy.data.objects)
    material_records = []
    selected = StagingTree()
    material_ids = {}
    source_cache = {}
    material_entries = {}
    naming_rows = {}
    for slot in mesh.material_slots:
        material = slot.material
        key = material.as_pointer()
        if key not in material_ids:
            material_id = _id(material, "VAPB-MAT-", "_vapb_export_material_id", bpy.data.materials)
            package_id = str(material.get("unity_source_package_id", ""))
            guid = str(material.get("unity_material_guid", "")).lower()
            file_id = str(material.get("unity_material_file_id", ""))
            if package_id not in source_cache:
                source_cache[package_id] = _source_assets(context.scene, package_id)
            assets = source_cache[package_id]
            source = assets.get(guid)
            if source is None or not source.pathname.lower().endswith(".mat") or not re.search(
                    rb"(?m)^---\s+!u!21\s+&" + re.escape(file_id.encode()) + rb"\b", source.asset_bytes):
                raise ValueError("Unity Material asset identity is not proven")
            data = _material_data(source.asset_bytes)
            entry = StagedUnityAsset(source.guid, source.pathname, source.asset_bytes,
                source.meta_bytes, source.preview_bytes, asset_type="MATERIAL_ASSET",
                source_identity={'source_guid': guid, 'source_path': source.pathname,
                                 'source_package_id': package_id})
            owners = proven_owners(material, package_id, guid, file_id, source.asset_bytes)
            if guid in material_entries:
                previous = material_entries[guid]
                if previous.asset_bytes != entry.asset_bytes or previous.meta_bytes != entry.meta_bytes:
                    raise ValueError('conflicting canonical Material revisions')
                for owner, label in owners.items():
                    old = naming_rows[guid]['owners'].get(owner)
                    if old is not None and old != label:
                        raise ValueError('conflicting Material owner labels')
                naming_rows[guid]['owners'].update(owners)
            else:
                material_entries[guid] = entry
                naming_rows[guid] = {'guid': guid, 'name': data.name, 'owners': owners}
            shader, shader_source = _shader_dependency(context.scene, package_id, data, source_cache)
            if shader_source is not None:
                selected.add(StagedUnityAsset(shader_source.guid, shader_source.pathname,
                    shader_source.asset_bytes, shader_source.meta_bytes, shader_source.preview_bytes,
                    asset_type="SHADER_ASSET"))
            textures = []
            for reference in data.textures.values():
                if reference.file_id == 0:
                    continue
                texture = _resolve_source_asset(context.scene, package_id, reference.guid, source_cache)
                if reference.file_id != 2800000 or not re.search(rb"(?m)^TextureImporter:\s*$", texture.meta_bytes):
                    raise ValueError("Texture provider subasset identity is unsupported")
                selected.add(StagedUnityAsset(texture.guid, texture.pathname, texture.asset_bytes,
                    texture.meta_bytes, texture.preview_bytes, asset_type="TEXTURE_ASSET"))
                textures.append({"property_name": reference.property_name, "guid": reference.guid,
                                 "file_id": str(reference.file_id)})
            material_ids[key] = material_id
            material_records.append({"export_material_id": material_id,
                                     "guid": guid, "file_id": file_id,
                                     "asset_sha256": _sha(source.asset_bytes),
                                     "shader": shader, "textures": textures})
    slots = [{"slot_index": index, "export_material_id": material_ids[slot.material.as_pointer()]}
             for index, slot in enumerate(mesh.material_slots)]
    destinations = allocate_material_paths(naming_rows.values())
    for guid, entry in material_entries.items():
        selected.add(replace(entry, pathname=destinations[guid], operation='MOVE'))

    model_guid = uuid4().hex
    model_path = f"Assets/VAPBExport/Generated_{object_id.removeprefix('VAPB-OBJ-')}.fbx"
    prefab_path = model_path[:-4] + ".prefab"
    with tempfile.TemporaryDirectory(prefix="vapb_final_state_") as temporary:
        fbx = Path(temporary) / "Generated.fbx"
        _stage_fbx(context, mesh, object_id, fbx)
        payload = fbx.read_bytes()
    selected.add(StagedUnityAsset(model_guid, model_path, payload,
        f"fileFormatVersion: 2\nguid: {model_guid}\n".encode("ascii"),
        asset_type="MESH_ASSET", operation="CREATE", strategy="REGENERATE_FROM_BLENDER",
        export_identity={"export_object_id": object_id}))
    task = {"kind": "BUILD_EXPORTED_STATIC_V1", "export_object_id": object_id,
            "model_guid": model_guid, "model_sha256": _sha(payload),
            "prefab_path": prefab_path, "materials": material_records, "material_slots": slots}
    first_party = Path(__file__).resolve().parents[1] / "unity_editor"
    support = (
        ("Assets/VAPBExport/VapbExportObjectMarker.cs", first_party / "VapbExportObjectMarker.cs"),
        ("Assets/VAPBExport/Editor/VapbFinalStateFinalizer.cs",
         first_party / "Editor/VapbFinalStateFinalizer.cs"),
    )
    support_guids = {path: _sha(path.encode())[:32] for path, _ in support}
    manifest_path = "Assets/VAPBExport/manifest.json"
    manifest_guid = _sha(manifest_path.encode())[:32]
    manifest = ExportManifest(
        schema_version=SCHEMA_VERSION,
        generator=GeneratorInfo("0.4.0-alpha", bpy.app.version_string),
        source_packages=(), source_assets=(),
        export_assets=tuple({"node_id": item.pathname, "node_type": item.asset_type,
            "operation": item.operation, "strategy": item.strategy,
            "desired_export_path": item.pathname,
            "source_identity": item.source_identity,
            "export_identity": {"export_guid": item.guid}}
            for item in selected.entries),
        export_roots=(object_id,), renderer_mappings=(), mesh_mappings=(),
        material_mappings=tuple(material_records), texture_mappings=(), bone_mappings=(),
        shape_key_mappings=(), prefab_source_chains=(), component_provenance=(),
        reachability=(), reference_rebind_tasks=(task,), unity_postimport_identity_map=(),
        external_dependencies=tuple(record['shader'] for record in material_records
            if record['shader']['classification'] == 'UNRESOLVED_BUT_PRESERVED'),
        unsupported_preserved_state=(), warnings=(), errors=())
    selected.add(StagedUnityAsset(manifest_guid, manifest_path,
        manifest.to_json().encode("utf-8"),
        f"fileFormatVersion: 2\nguid: {manifest_guid}\n".encode("ascii"), operation="CREATE"))
    for path, source in support:
        guid = support_guids[path]
        selected.add(StagedUnityAsset(guid, path, source.read_bytes(),
            f"fileFormatVersion: 2\nguid: {guid}\n".encode("ascii"), operation="CREATE"))
    UnityPackageWriter().write(selected, output)
    # Export labels live in the output copy/Recipe; never write into the editing scene.
    return manifest
