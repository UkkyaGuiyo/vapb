"""Join package Renderer occurrences to native FBX objects by exact witness IDs.

This is a read-only plan. Material and Prefab semantics stay in the package
projection; callers must not apply a row with an issue.
"""

from __future__ import annotations

import json

from ..unity.occurrence_projection import occurrence_identity
from .fbx_receipt import RECEIPT_VERSION


def _edge_path(obj):
    raw = obj.get("_vapb_model_instance_edge_path")
    if raw is None:
        return []
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def plan_witness_realizations(records, objects, witness):
    """Return unique (occurrence, Mesh Object) pairs and explicit failures."""
    bindings, issues = [], []
    objects = tuple(objects)
    for record in records:
        occurrence = record.get("occurrence_id", "")

        def reject(code):
            issues.append({"occurrence_id": occurrence, "code": code})

        if witness is None:
            reject("WITNESS_MISSING")
            continue
        try:
            if occurrence != occurrence_identity(record):
                reject("OCCURRENCE_IDENTITY_MISMATCH")
                continue
            mesh = record["mesh"]
            row = witness.mesh(mesh["mesh_guid"], mesh["mesh_file_id"])
            if row is None:
                reject("WITNESS_MISSING")
                continue
            source = record["source_key"]
            if source["source_kind"] == "MODEL_SOURCE":
                owner = record["owner"]
                if (source["source_asset_guid"].lower() != row.asset_guid
                        or int(source["renderer_file_id"]) != row.renderer_local_id
                        or int(owner["owner_game_object_id"]) != row.game_object_local_id
                        or int(record["renderer_class_id"]) != row.class_id):
                    reject("SOURCE_IDENTITY_MISMATCH")
                    continue
            elif source["source_kind"] != "PREFAB_LOCAL":
                reject("SOURCE_IDENTITY_MISMATCH")
                continue
            path = list(record["instance_edge_path"])
            candidates = [obj for obj in objects
                          if getattr(obj, "type", None) == "MESH"
                          and obj.get("_vapb_root_context_id") == record["root_context_id"]
                          and obj.get("unity_source_package_id") == mesh["source_package_id"]
                          and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == row.asset_guid
                          and str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() == mesh["source_sha256"].lower()
                          and str(obj.get("_vapb_fbx_model_uid", "")) == str(row.model_uid)
                          and str(obj.get("_vapb_fbx_geometry_uid", "")) == str(row.geometry_uid)
                          and _edge_path(obj) == path
                          and obj.get("_vapb_fbx_realization_id")]
            if not candidates:
                reject("NATIVE_MISSING")
            elif len(candidates) != 1:
                reject("NATIVE_AMBIGUOUS")
            else:
                bindings.append((record, candidates[0]))
        except (KeyError, TypeError, ValueError, AttributeError):
            reject("INCOMPLETE_IDENTITY")
    claims = {}
    for record, obj in bindings:
        claims[id(obj)] = claims.get(id(obj), 0) + 1
    unique = []
    for record, obj in bindings:
        if claims[id(obj)] == 1:
            unique.append((record, obj))
        else:
            issues.append({"occurrence_id": record["occurrence_id"],
                           "code": "NATIVE_AMBIGUOUS"})
    return unique, issues


def plan_witness_material_dependencies(bindings, package_sha256):
    """Use only serialized Material references from proven occurrence rows."""
    dependencies = []
    for record, obj in bindings:
        if record.get("material_status") not in {"EXACT", "PARTIAL"}:
            continue
        for slot, reference in record.get("materials", {}).items():
            if not isinstance(slot, int) or slot < 0:
                continue
            explicit_null = (reference is None and record.get("material_status") == "EXACT"
                             and isinstance(record.get("material_slot_count"), int)
                             and slot < record["material_slot_count"])
            if not explicit_null and (not isinstance(reference, dict)
                                      or not reference.get("guid") or not reference.get("file_id")):
                continue
            dependency = {
                "dependency_type": "CLEAR_MATERIAL_SLOT" if explicit_null else "PREFAB_RENDERER_MATERIAL",
                "consumer_package_id": record["mesh"]["source_package_id"],
                "consumer_root_context_id": record["root_context_id"],
                "consumer_occurrence_id": record["occurrence_id"],
                "consumer_native_realization_id": str(obj["_vapb_fbx_realization_id"]),
                "consumer_source_package_sha256": package_sha256,
                "consumer_fbx_guid": record["mesh"]["mesh_guid"],
                "consumer_fbx_sha256": record["mesh"]["source_sha256"],
                "consumer_fbx_model_uid": str(obj["_vapb_fbx_model_uid"]),
                "consumer_fbx_geometry_uid": str(obj["_vapb_fbx_geometry_uid"]),
                "consumer_fbx_object_receipt_id": str(obj["_vapb_fbx_object_receipt_id"]),
                "consumer_fbx_mesh_receipt_id": str(obj["_vapb_fbx_mesh_receipt_id"]),
                "consumer_slot_index": slot,
                "identity_bridge": "UNITY_MODEL_WITNESS",
            }
            if not explicit_null:
                dependency["target_guid"] = str(reference["guid"]).lower()
                dependency["target_file_id"] = str(reference["file_id"])
            dependencies.append(dependency)
    return dependencies


def find_witness_consumer(record, objects):
    """Resolve a saved dependency by occurrence and unique native realization."""
    realization = record.get("consumer_native_realization_id")
    context = record.get("consumer_root_context_id")
    package = record.get("consumer_package_id")
    if not realization or not context or not package or not record.get("consumer_occurrence_id"):
        return None
    objects = tuple(objects)
    roots = [obj for obj in objects
             if obj.get("_vapb_root_context_id") == context
             and obj.get("_vapb_renderer_occurrences") is not None
             and obj.get("_vapb_witness_package_sha256") == record.get("consumer_source_package_sha256")]
    if len(roots) != 1:
        return None
    try:
        raw = roots[0]["_vapb_renderer_occurrences"]
        projection = json.loads(raw) if isinstance(raw, str) else raw
        matching = [item for item in projection["records"]
                    if item.get("occurrence_id") == record["consumer_occurrence_id"]]
        if len(matching) != 1 or matching[0]["occurrence_id"] != occurrence_identity(matching[0]):
            return None
        projected_mesh = matching[0]["mesh"]
        if (projected_mesh["mesh_guid"] != record["consumer_fbx_guid"]
                or projected_mesh["source_sha256"] != record["consumer_fbx_sha256"]):
            return None
        materials = matching[0]["materials"]
        slot = record["consumer_slot_index"]
        if str(slot) in materials:
            reference = materials[str(slot)]
        elif slot in materials:
            reference = materials[slot]
        else:
            return None
        if record.get("dependency_type") == "CLEAR_MATERIAL_SLOT":
            if (reference is not None or matching[0].get("material_status") != "EXACT"
                    or not isinstance(matching[0].get("material_slot_count"), int)
                    or not isinstance(slot, int) or slot < 0
                    or slot >= matching[0]["material_slot_count"]):
                return None
        elif (not isinstance(reference, dict)
              or str(reference.get("guid", "")).lower() != str(record.get("target_guid", "")).lower()
              or str(reference.get("file_id", "")) != str(record.get("target_file_id", ""))):
            return None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    matches = [obj for obj in objects
               if getattr(obj, "type", None) == "MESH"
               and obj.get("_vapb_fbx_realization_id") == realization
               and obj.get("_vapb_root_context_id") == context
               and obj.get("unity_source_package_id") == package
               and obj.get("_vapb_fbx_receipt_version") == RECEIPT_VERSION
               and obj.get("_vapb_fbx_source_asset_guid") == record.get("consumer_fbx_guid")
               and obj.get("_vapb_fbx_source_asset_sha256") == record.get("consumer_fbx_sha256")
               and obj.get("_vapb_fbx_model_uid") == record.get("consumer_fbx_model_uid")
               and obj.get("_vapb_fbx_geometry_uid") == record.get("consumer_fbx_geometry_uid")
               and obj.get("_vapb_fbx_object_receipt_id") == record.get("consumer_fbx_object_receipt_id")
               and obj.get("_vapb_fbx_mesh_receipt_id") == record.get("consumer_fbx_mesh_receipt_id")
               and getattr(obj, "data", None) is not None
               and obj.data.get("_vapb_fbx_receipt_version") == RECEIPT_VERSION
               and obj.data.get("_vapb_fbx_source_asset_sha256") == record.get("consumer_fbx_sha256")
               and obj.data.get("_vapb_fbx_geometry_uid") == record.get("consumer_fbx_geometry_uid")
               and obj.data.get("_vapb_fbx_mesh_receipt_id") == record.get("consumer_fbx_mesh_receipt_id")]
    return matches[0] if len(matches) == 1 else None


def reserve_witness_slots(dependencies, objects):
    """Stabilize shared Mesh slot capacity before any slot snapshots are saved."""
    ready, rejected = [], []
    objects = tuple(objects)
    for dependency in dependencies:
        obj = find_witness_consumer(dependency, objects)
        slot = dependency.get("consumer_slot_index")
        if (obj is None or not isinstance(slot, int) or slot < 0
                or getattr(obj, "data", None) is None
                or not hasattr(obj.data, "materials")):
            rejected.append({"occurrence_id": dependency.get("consumer_occurrence_id", ""),
                             "code": "WITNESS_CONSUMER_MISSING"})
            continue
        while len(obj.data.materials) <= slot:
            obj.data.materials.append(None)
        ready.append(dependency)
    return ready, rejected
