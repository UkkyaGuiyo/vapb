"""One static Blender final-state Mesh plus its selected Unity Material closure."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tempfile
from uuid import uuid4

from .fbx_export import FBX_EXPORT_PRESET
from .manifest import ExportManifest, GeneratorInfo, SCHEMA_VERSION
from .package_writer import UnityPackageWriter
from .raw_assets import RawAssetRepository
from .staging import StagedUnityAsset, StagingTree
from ..blender.identity_registry import load_scene_registry


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


def _material_texture_guids(payload: bytes) -> set[str]:
    text = payload.decode("utf-8-sig")
    if not re.search(r"(?m)^\s*m_Shader:\s*\{fileID:\s*46,\s*guid:\s*0000000000000000f000000000000000", text):
        raise ValueError("only the synthetic built-in Standard shader is supported")
    result = set()
    for reference in re.findall(r"m_Texture:\s*\{([^{}]*)\}", text):
        file_id = re.search(r"\bfileID:\s*(-?\d+)", reference)
        if file_id is None:
            raise ValueError("Material texture reference has no fileID")
        if int(file_id.group(1)) == 0:
            continue
        guid = re.search(r"\bguid:\s*([0-9a-fA-F]{32})\b", reference)
        if guid is None:
            raise ValueError("Material texture reference has no GUID")
        result.add(guid.group(1).lower())
    return result


def _source_assets(scene, package_id: str):
    package = load_scene_registry(scene).packages.get(package_id)
    if not package:
        raise ValueError("source Material package is unavailable")
    archive = Path(package["source_archive_path"])
    payload = archive.read_bytes()
    if package_id != "sha256:" + _sha(payload) or package["package_sha256"] != _sha(payload):
        raise ValueError("source Material package revision changed")
    return {asset.guid: asset for asset in RawAssetRepository(archive).read_all(payload)}


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
    for slot in mesh.material_slots:
        material = slot.material
        key = material.as_pointer()
        if key not in material_ids:
            material_id = _id(material, "VAPB-MAT-", "_vapb_export_material_id", bpy.data.materials)
            package_id = str(material.get("unity_source_package_id", ""))
            guid = str(material.get("unity_material_guid", "")).lower()
            file_id = str(material.get("unity_material_file_id", ""))
            assets = _source_assets(context.scene, package_id)
            source = assets.get(guid)
            if source is None or not source.pathname.lower().endswith(".mat") or not re.search(
                    rb"(?m)^---\s+!u!21\s+&" + re.escape(file_id.encode()) + rb"\b", source.asset_bytes):
                raise ValueError("Unity Material asset identity is not proven")
            selected.add(StagedUnityAsset(source.guid, source.pathname, source.asset_bytes,
                source.meta_bytes, source.preview_bytes, asset_type="MATERIAL_ASSET"))
            for texture_guid in _material_texture_guids(source.asset_bytes):
                texture = assets.get(texture_guid)
                if texture is None or not re.search(rb"(?m)^TextureImporter:\s*$", texture.meta_bytes):
                    raise ValueError("selected Material Texture provider is unavailable")
                selected.add(StagedUnityAsset(texture.guid, texture.pathname, texture.asset_bytes,
                    texture.meta_bytes, texture.preview_bytes, asset_type="TEXTURE_ASSET"))
            material_ids[key] = material_id
            material_records.append({"export_material_id": material_id,
                                     "guid": guid, "file_id": file_id})
    slots = [{"slot_index": index, "export_material_id": material_ids[slot.material.as_pointer()]}
             for index, slot in enumerate(mesh.material_slots)]

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
            "export_identity": {"export_guid": item.guid}}
            for item in selected.entries),
        export_roots=(object_id,), renderer_mappings=(), mesh_mappings=(),
        material_mappings=tuple(material_records), texture_mappings=(), bone_mappings=(),
        shape_key_mappings=(), prefab_source_chains=(), component_provenance=(),
        reachability=(), reference_rebind_tasks=(task,), unity_postimport_identity_map=(),
        external_dependencies=(), unsupported_preserved_state=(), warnings=(), errors=())
    selected.add(StagedUnityAsset(manifest_guid, manifest_path,
        manifest.to_json().encode("utf-8"),
        f"fileFormatVersion: 2\nguid: {manifest_guid}\n".encode("ascii"), operation="CREATE"))
    for path, source in support:
        guid = support_guids[path]
        selected.add(StagedUnityAsset(guid, path, source.read_bytes(),
            f"fileFormatVersion: 2\nguid: {guid}\n".encode("ascii"), operation="CREATE"))
    UnityPackageWriter().write(selected, output)
    mesh["_vapb_export_object_id"] = object_id
    for slot in mesh.material_slots:
        slot.material["_vapb_export_material_id"] = material_ids[slot.material.as_pointer()]
    return manifest
