"""Persistent, scoped evidence for a user's Renderer to native Object choice.

This module has no Blender dependency so the identity checks can be exercised
without an open scene. Names and session UIDs are deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from ..unity.occurrence_projection import occurrence_identity
from .fbx_receipt import RECEIPT_VERSION


class BindingError(ValueError):
    pass


def _need(value: Any, label: str) -> str:
    if value is None or str(value) == "":
        raise BindingError(f"Missing {label}")
    return str(value)


def _property(obj: Any, key: str) -> str:
    return _need(obj.get(key), key)


def semantic_owner_id(record: dict) -> str:
    """Logical owner ID; revision, displayed name, and Blender pointer excluded."""
    try:
        owner = record["owner"]
        source = record["source_key"]
        scope = [record["root_context_id"], record["root_package_id"],
                 record["root_member_id"], record["root_asset_guid"],
                 [[edge["container_package_id"], edge["container_asset_guid"],
                   str(edge["prefab_instance_file_id"]), edge["source_package_id"],
                   edge["source_prefab_guid"]] for edge in record["instance_edge_path"]],
                 record["source_package_id"], source["source_asset_guid"],
                 str(owner["owner_game_object_id"])]
    except (KeyError, TypeError) as exc:
        raise BindingError("Incomplete semantic owner scope") from exc
    if any(not str(part) for part in scope if not isinstance(part, list)):
        raise BindingError("Incomplete semantic owner scope")
    return hashlib.sha256(json.dumps(scope, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def _unique(objects: Iterable[Any], key: str, value: str) -> None:
    if sum(str(obj.get(key, "")) == value for obj in objects) != 1:
        raise BindingError(f"Non-unique {key}")


def _receipt(obj: Any, record: dict) -> dict:
    data = getattr(obj, "data", None)
    if data is None:
        raise BindingError("Mesh datablock missing")
    if (_property(obj, "_vapb_fbx_receipt_version") != RECEIPT_VERSION
            or _property(data, "_vapb_fbx_receipt_version") != RECEIPT_VERSION):
        raise BindingError("FBX receipt version mismatch")
    mesh = record.get("mesh", {})
    expected_guid = _need(mesh.get("mesh_guid"), "mesh GUID").lower()
    expected_sha = _need(mesh.get("source_sha256"), "mesh SHA256").lower()
    expected_package = _need(mesh.get("source_package_id"), "mesh package")
    if _property(obj, "unity_source_package_id") != expected_package:
        raise BindingError("Mesh package mismatch")
    if _property(obj, "_vapb_fbx_source_asset_guid").lower() != expected_guid:
        raise BindingError("Mesh GUID mismatch")
    if _property(obj, "_vapb_fbx_source_asset_sha256").lower() != expected_sha:
        raise BindingError("Mesh SHA256 mismatch")
    if _property(data, "_vapb_fbx_source_asset_sha256").lower() != expected_sha:
        raise BindingError("Mesh datablock SHA256 mismatch")
    for obj_key, data_key in (("_vapb_fbx_geometry_uid", "_vapb_fbx_geometry_uid"),
                              ("_vapb_fbx_mesh_receipt_id", "_vapb_fbx_mesh_receipt_id")):
        if _property(obj, obj_key) != _property(data, data_key):
            raise BindingError(f"Mesh datablock {data_key} mismatch")
    return {"source_package_id": expected_package, "mesh_guid": expected_guid,
            "mesh_file_id": _need(mesh.get("mesh_file_id"), "mesh file ID"),
            "source_sha256": expected_sha,
            "fbx_model_uid": _property(obj, "_vapb_fbx_model_uid"),
            "fbx_geometry_uid": _property(obj, "_vapb_fbx_geometry_uid"),
            "fbx_object_receipt_id": _property(obj, "_vapb_fbx_object_receipt_id"),
            "fbx_mesh_receipt_id": _property(obj, "_vapb_fbx_mesh_receipt_id")}


def _authoritative_record(root: Any, record: dict) -> None:
    raw = root.get("_vapb_renderer_occurrences")
    try:
        projection = json.loads(raw) if isinstance(raw, str) else raw
        records = projection["records"]
        matches = [candidate for candidate in records
                   if candidate.get("occurrence_id") == record.get("occurrence_id")]
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise BindingError("Root projection is missing or malformed") from exc
    if len(matches) != 1 or matches[0] != record:
        raise BindingError("Occurrence differs from root projection")


def validate_binding(record: dict, root: Any, mesh_obj: Any,
                     all_objects: Iterable[Any], armature_obj: Any = None,
                     *, _revalidating: bool = False) -> dict:
    """Return a self-contained link only when all independent scopes agree."""
    objects = tuple(all_objects)
    if not isinstance(record, dict):
        raise BindingError("Invalid occurrence record")
    _authoritative_record(root, record)
    if not any(obj is mesh_obj for obj in objects) or getattr(mesh_obj, "type", None) != "MESH":
        raise BindingError("Selected mesh is not a scene Mesh Object")
    root_context = _property(root, "_vapb_root_context_id")
    if sum(obj.get("_vapb_root_context_id") == root_context and
           obj.get("_vapb_renderer_occurrences") is not None for obj in objects) != 1:
        raise BindingError("Root context is not unique")
    if _need(record.get("root_context_id"), "occurrence root") != root_context:
        raise BindingError("Root context mismatch")
    if _property(mesh_obj, "_vapb_root_context_id") != root_context:
        raise BindingError("Mesh root context mismatch")
    occurrence = _need(record.get("occurrence_id"), "occurrence ID")
    try:
        if occurrence != occurrence_identity(record):
            raise BindingError("Occurrence identity mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        raise BindingError("Incomplete occurrence identity") from exc
    package = _need(record.get("source_package_id"), "renderer source package")
    owner_id = semantic_owner_id(record)
    owners = [obj for obj in objects if str(obj.get("_vapb_semantic_owner_id", "")) == owner_id]
    if len(owners) != 1:
        raise BindingError("Semantic owner missing or duplicated")
    owner = owners[0]
    if _property(owner, "_vapb_root_context_id") != root_context or _property(owner, "unity_source_package_id") != package:
        raise BindingError("Semantic owner scope mismatch")
    realization = _property(mesh_obj, "_vapb_fbx_realization_id")
    _unique(objects, "_vapb_fbx_realization_id", realization)
    receipt = _receipt(mesh_obj, record)
    existing = mesh_obj.get("_vapb_renderer_binding")
    if existing and not _revalidating:
        raise BindingError("Mesh Object already has a Renderer binding")
    for obj in objects:
        if obj is mesh_obj and _revalidating:
            continue
        binding = obj.get("_vapb_renderer_binding")
        if binding:
            try:
                linked = json.loads(binding) if isinstance(binding, str) else binding
            except (TypeError, ValueError) as exc:
                raise BindingError("Malformed existing Renderer binding") from exc
            if linked.get("occurrence_id") == occurrence:
                raise BindingError("Renderer occurrence already bound")
    armature_id = None
    if int(record.get("renderer_class_id", 0)) == 137:
        modifiers = [modifier for modifier in getattr(mesh_obj, "modifiers", ())
                     if getattr(modifier, "type", None) == "ARMATURE"]
        if len(modifiers) != 1 or getattr(modifiers[0], "object", None) is None:
            raise BindingError("Skinned Renderer needs one armature modifier target")
        target = modifiers[0].object
        if armature_obj is not None and armature_obj is not target:
            raise BindingError("Armature target mismatch")
        if not any(obj is target for obj in objects) or getattr(target, "type", None) != "ARMATURE":
            raise BindingError("Armature target is outside the scene")
        if (_property(target, "_vapb_root_context_id") != root_context
                or _property(target, "unity_source_package_id") != receipt["source_package_id"]):
            raise BindingError("Armature scope mismatch")
        armature_id = _property(target, "_vapb_native_object_id")
        _unique(objects, "_vapb_native_object_id", armature_id)
    elif int(record.get("renderer_class_id", 0)) != 23:
        raise BindingError("Unsupported Renderer class")
    return {"evidence": "USER_CONFIRMED", "occurrence_id": occurrence,
            "occurrence": record, "root_context_id": root_context,
            "source_package_id": package, "semantic_owner_id": owner_id,
            "native_realization_id": realization, "armature_native_object_id": armature_id,
            "mesh_receipt": receipt}


def validate_existing_binding(binding: dict, root: Any, mesh_obj: Any,
                              all_objects: Iterable[Any]) -> dict:
    """Revalidate after file reload without session UIDs or object names."""
    if binding.get("evidence") != "USER_CONFIRMED":
        raise BindingError("Binding evidence is not user confirmation")
    record = binding.get("occurrence")
    if not isinstance(record, dict) or binding.get("occurrence_id") != record.get("occurrence_id"):
        raise BindingError("Stored occurrence mismatch")
    if binding.get("native_realization_id") != mesh_obj.get("_vapb_fbx_realization_id"):
        raise BindingError("Stored realization mismatch")
    checked = validate_binding(record, root, mesh_obj, all_objects, _revalidating=True)
    if checked != binding:
        raise BindingError("Stored binding evidence changed")
    return checked


SKIN_BINDING_VERSION = "1"
_BONE_KEYS = ("_vapb_fbx_bone_realization_id", "_vapb_fbx_bone_receipt_id",
              "_vapb_fbx_model_uid", "_vapb_fbx_source_asset_guid",
              "_vapb_fbx_source_asset_sha256")


def _stored_renderer_binding(mesh_obj: Any, root: Any, objects: tuple) -> dict:
    raw = mesh_obj.get("_vapb_renderer_binding")
    try:
        binding = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError) as exc:
        raise BindingError("Malformed Renderer binding") from exc
    if not isinstance(binding, dict):
        raise BindingError("Renderer binding missing")
    return validate_existing_binding(binding, root, mesh_obj, objects)


def _skin_ids(record: dict) -> tuple[list[str], str]:
    skin = record.get("skin")
    if not isinstance(skin, dict) or skin.get("status") != "EXACT":
        raise BindingError("Skin projection is unresolved")
    rows = skin.get("bones")
    root_id = str(skin.get("root_bone_transform_file_id", ""))
    if not isinstance(rows, list) or not rows or not root_id:
        raise BindingError("Skin projection is incomplete")
    ids = [str(row.get("transform_file_id", "")) for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or len(set(ids)) != len(ids) or any(not item for item in ids):
        raise BindingError("Skin bone slots are incomplete")
    return ids, root_id


def _skin_armature(mesh_obj: Any, binding: dict, objects: tuple) -> Any:
    modifiers = [modifier for modifier in getattr(mesh_obj, "modifiers", ())
                 if getattr(modifier, "type", None) == "ARMATURE"]
    if len(modifiers) != 1 or getattr(modifiers[0], "object", None) is None:
        raise BindingError("Skin armature target is unresolved")
    armature = modifiers[0].object
    if not any(obj is armature for obj in objects) or getattr(armature, "type", None) != "ARMATURE":
        raise BindingError("Skin armature target is outside the scene")
    if str(armature.get("_vapb_native_object_id", "")) != binding.get("armature_native_object_id"):
        raise BindingError("Skin armature identity changed")
    return armature


def _bone_values(bone: Any) -> dict:
    if str(bone.get("_vapb_fbx_receipt_version", "")) != RECEIPT_VERSION:
        raise BindingError("Native Bone receipt version mismatch")
    values = {key: _property(bone, key) for key in _BONE_KEYS}
    guid = values["_vapb_fbx_source_asset_guid"]
    sha = values["_vapb_fbx_source_asset_sha256"]
    uid = values["_vapb_fbx_model_uid"]
    expected_receipt = "vapb-fbx-bone:" + hashlib.sha256(f"{guid}:{sha}:{uid}".encode()).hexdigest()
    if (len(guid) != 32 or len(sha) != 64 or any(c not in "0123456789abcdef" for c in guid + sha)
            or values["_vapb_fbx_bone_receipt_id"] != expected_receipt):
        raise BindingError("Native Bone source receipt is invalid")
    evidence = str(bone.get("_vapb_fbx_receipt_evidence", ""))
    if evidence not in {"OFFICIAL_IMPORTER_BUILD_SKELETON_RETURN", "OBSERVED_BONE_TRANSPLANT"}:
        raise BindingError("Native Bone creation evidence missing")
    if evidence == "OBSERVED_BONE_TRANSPLANT" and not bone.get("_vapb_fbx_source_realization_id"):
        raise BindingError("Transplanted Bone source realization missing")
    values["_vapb_fbx_receipt_evidence"] = evidence
    values["_vapb_fbx_source_realization_id"] = str(bone.get("_vapb_fbx_source_realization_id", ""))
    return values


def _native_bones(armature: Any) -> list[Any]:
    data = getattr(armature, "data", None)
    if data is None or not hasattr(data, "bones"):
        raise BindingError("Armature Bone datablocks missing")
    return list(data.bones)


def make_skin_binding(mesh_obj: Any, root: Any, all_objects: Iterable[Any],
                      selections: dict[str, str]) -> dict:
    """Capture explicit Unity Transform -> observed native Bone choices."""
    objects = tuple(all_objects)
    renderer = _stored_renderer_binding(mesh_obj, root, objects)
    record = renderer["occurrence"]
    if record.get("renderer_class_id") != 137:
        raise BindingError("Renderer is not skinned")
    ids, root_id = _skin_ids(record)
    expected = ids + ([] if root_id in ids else [root_id])
    if not isinstance(selections, dict) or set(selections) != set(expected):
        raise BindingError("Every source Bone and root needs one explicit choice")
    armature = _skin_armature(mesh_obj, renderer, objects)
    bones = _native_bones(armature)
    mappings = []
    used = set()
    for transform_id in expected:
        name = selections[transform_id]
        matches = [bone for bone in bones if bone.name == name]
        if len(matches) != 1:
            raise BindingError("Selected native Bone missing or ambiguous")
        values = _bone_values(matches[0])
        realization = values["_vapb_fbx_bone_realization_id"]
        if sum(bone.get("_vapb_fbx_bone_realization_id") == realization for bone in bones) != 1 or realization in used:
            raise BindingError("Native Bone realization is duplicate")
        used.add(realization)
        mappings.append({"target_transform_file_id": transform_id,
                         "edited_bone_realization_id": realization,
                         "native_bone_receipt_id": values["_vapb_fbx_bone_receipt_id"],
                         "source_fbx_model_uid": values["_vapb_fbx_model_uid"],
                         "source_fbx_guid": values["_vapb_fbx_source_asset_guid"],
                         "source_fbx_sha256": values["_vapb_fbx_source_asset_sha256"],
                         "creation_evidence": values["_vapb_fbx_receipt_evidence"],
                         "source_bone_realization_id": values["_vapb_fbx_source_realization_id"]})
    binding = {"version": SKIN_BINDING_VERSION,
               "renderer_occurrence_id": renderer["occurrence_id"],
               "source_revision_sha256": record["source_revision_sha256"],
               "root_revision_sha256": record["root_revision_sha256"],
               "root_context_id": renderer["root_context_id"],
               "native_mesh_realization_id": renderer["native_realization_id"],
               "armature_native_object_id": renderer["armature_native_object_id"],
               "root_bone_target_transform_file_id": root_id, "mappings": mappings}
    return binding


def validate_skin_binding(mesh_obj: Any, root: Any, all_objects: Iterable[Any]) -> dict:
    """Revalidate persisted skin choices without using Blender Bone names."""
    objects = tuple(all_objects)
    renderer = _stored_renderer_binding(mesh_obj, root, objects)
    record = renderer["occurrence"]
    ids, root_id = _skin_ids(record)
    raw = mesh_obj.get("_vapb_skin_binding")
    try:
        binding = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError) as exc:
        raise BindingError("Malformed Skin binding") from exc
    if not isinstance(binding, dict) or binding.get("version") != SKIN_BINDING_VERSION:
        raise BindingError("Skin binding missing or unsupported")
    checks = {"renderer_occurrence_id": renderer["occurrence_id"],
              "source_revision_sha256": record["source_revision_sha256"],
              "root_revision_sha256": record["root_revision_sha256"],
              "root_context_id": renderer["root_context_id"],
              "native_mesh_realization_id": renderer["native_realization_id"],
              "armature_native_object_id": renderer["armature_native_object_id"],
              "root_bone_target_transform_file_id": root_id}
    if any(binding.get(key) != value for key, value in checks.items()):
        raise BindingError("Skin binding scope changed")
    expected = ids + ([] if root_id in ids else [root_id])
    mappings = binding.get("mappings")
    if not isinstance(mappings, list) or [row.get("target_transform_file_id") for row in mappings
                                              if isinstance(row, dict)] != expected or len(mappings) != len(expected):
        raise BindingError("Skin source Bone list changed")
    armature = _skin_armature(mesh_obj, renderer, objects)
    bones = _native_bones(armature)
    used = set()
    for row in mappings:
        realization = row.get("edited_bone_realization_id")
        matches = [bone for bone in bones if bone.get("_vapb_fbx_bone_realization_id") == realization]
        if not realization or len(matches) != 1 or realization in used:
            raise BindingError("Native Bone realization missing or duplicate")
        used.add(realization)
        values = _bone_values(matches[0])
        if any(row.get(key) != values[source] for key, source in (
                ("native_bone_receipt_id", "_vapb_fbx_bone_receipt_id"),
                ("source_fbx_model_uid", "_vapb_fbx_model_uid"),
                ("source_fbx_guid", "_vapb_fbx_source_asset_guid"),
                ("source_fbx_sha256", "_vapb_fbx_source_asset_sha256"),
                ("creation_evidence", "_vapb_fbx_receipt_evidence"),
                ("source_bone_realization_id", "_vapb_fbx_source_realization_id"))):
            raise BindingError("Native Bone receipt changed")
    return binding
