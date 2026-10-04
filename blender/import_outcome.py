"""Read existing Blender scene import evidence without modifying it."""

from __future__ import annotations

import json

from .dependency_resolver import load_dependency_registry
from .fbx_importer import summarize_fbx_import_contexts
from .fbx_receipt import validate_persistent_receipt
from .model_witness_bridge import find_witness_consumer
from ..unity.occurrence_projection import occurrence_identity
from ..unity.import_outcome import summarize_import_outcome


def scene_import_outcome(scene):
    projections = []
    for root in scene.objects:
        raw = root.get("_vapb_renderer_occurrences")
        if not raw:
            continue
        try:
            projection = json.loads(str(raw))
            if not isinstance(projection, dict) or not isinstance(projection.get("issues"), list):
                raise ValueError("invalid projection")
            projections.append(projection)
        except (TypeError, ValueError, json.JSONDecodeError):
            projections.append({"records": [], "issues": [{"code": "INVALID_SAVED_PROJECTION"}]})
    dependencies = load_dependency_registry(scene).get("dependencies", [])
    verified_null_slots, edited_null_slots = set(), set()
    null_records = [item for item in dependencies if item.get("dependency_type") == "CLEAR_MATERIAL_SLOT"]
    for record in null_records:
        slot = record.get("consumer_slot_index")
        key = (record.get("consumer_root_context_id"), record.get("consumer_occurrence_id"), slot)
        if not isinstance(slot, int) or slot < 0 or sum(
                (item.get("consumer_root_context_id"), item.get("consumer_occurrence_id"),
                 item.get("consumer_slot_index")) == key for item in null_records) != 1:
            continue
        consumer = find_witness_consumer(record, scene.objects)
        if consumer is None or slot >= len(consumer.material_slots):
            continue
        current = consumer.material_slots[slot]
        if (record.get("status") == "NULL_REALIZED" and record.get("binding_status") == "BOUND"
                and record.get("applied_slot_state") == {"link": "OBJECT", "material": None}
                and current.link == "OBJECT" and current.material is None):
            verified_null_slots.add(key)
        elif record.get("status") == "USER_EDIT_PRESERVED" and current.material is not None:
            edited_null_slots.add(key)
    realized_renderer_occurrences = set()
    roots_by_context = {}
    for root in scene.objects:
        context_id = root.get("_vapb_root_context_id")
        if not context_id or root.get("_vapb_renderer_occurrences") is None:
            continue
        roots_by_context.setdefault(str(context_id), []).append(root)
    candidates_by_occurrence = {}
    for obj in scene.objects:
        occurrence_id = obj.get("_vapb_renderer_occurrence_id")
        if getattr(obj, "type", None) != "MESH" or not occurrence_id or not validate_persistent_receipt(obj):
            continue
        context_id = str(obj.get("_vapb_root_context_id", ""))
        roots = roots_by_context.get(context_id, [])
        if len(roots) != 1:
            continue
        try:
            raw = roots[0]["_vapb_renderer_occurrences"]
            projection = json.loads(raw) if isinstance(raw, str) else raw
            rows = [row for row in projection["records"]
                    if row.get("occurrence_id") == occurrence_id
                    and row.get("root_context_id") == context_id
                    and row.get("source_key", {}).get("source_kind") == "PREFAB_LOCAL"
                    and isinstance(row.get("instance_edge_path"), list)
                    and row["instance_edge_path"]]
            if len(rows) != 1 or occurrence_identity(rows[0]) != occurrence_id:
                continue
            row = rows[0]
            mesh = row["mesh"]
            if (str(obj.get("unity_source_package_id", "")) != str(mesh["source_package_id"])
                    or str(obj.get("_vapb_fbx_source_asset_guid", "")).lower()
                    != str(mesh["mesh_guid"]).lower()
                    or str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower()
                    != str(mesh["source_sha256"]).lower()):
                continue
            candidates_by_occurrence.setdefault(str(occurrence_id), []).append(obj)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    realization_evidence = {
        occurrence: {id(obj): obj for obj in candidates}
        for occurrence, candidates in candidates_by_occurrence.items()
    }
    for record in dependencies:
        occurrence_id = record.get("consumer_occurrence_id")
        if (occurrence_id and record.get("dependency_type") in {
                "PREFAB_RENDERER_MATERIAL", "CLEAR_MATERIAL_SLOT"}
                ):
            consumer = find_witness_consumer(record, scene.objects)
            if consumer is None:
                continue
            occurrence = str(occurrence_id)
            realization_evidence.setdefault(occurrence, {})[id(consumer)] = consumer
    realized_renderer_occurrences.update(
        occurrence for occurrence, candidates in realization_evidence.items()
        if len(candidates) == 1
    )
    outcome = summarize_import_outcome(
        projections, dependencies, verified_null_slots, edited_null_slots,
        realized_renderer_occurrences,
    )
    fbx_summary, fbx_history_valid = summarize_fbx_import_contexts(scene)
    failed_fbx_count = fbx_summary["failed"]
    if not fbx_history_valid:
        outcome["counts"]["PARTIAL"] += 1
        outcome["items"].append({
            "category": "PARTIAL",
            "code": "FBX_IMPORT_CONTEXTS_INVALID",
            "scope": "FBX import",
            "reason": "FBX import history is invalid or internally inconsistent.",
            "action": "Reimport the source package and inspect the saved FBX import history.",
        })
        outcome["overall"] = "PARTIAL"
    if failed_fbx_count > 0:
        outcome["counts"]["PARTIAL"] += 1
        outcome["items"].append({
            "category": "PARTIAL",
            "code": "FBX_IMPORT_PARTIAL_FAILURE",
            "scope": "FBX import",
            "reason": f"{failed_fbx_count}件のFBXが失敗するか、Blender Objectを生成しませんでした。",
            "action": "FBX別の状態を確認し、不足するモデルを確認してください。",
        })
        outcome["overall"] = "PARTIAL"
    for obj in scene.objects:
        if obj.get("_vapb_geometry_frame_status") != "UNVERIFIED":
            continue
        outcome["counts"]["UNSUPPORTED"] += 1
        outcome["items"].append({
            "category": "UNSUPPORTED", "code": "DIRECT_MESH_GEOMETRY_FRAME_UNVERIFIED",
            "scope": "直接参照されたモデルMesh",
            "reason": "Unity Mesh資源の座標系と単位への対応は未確認です。",
            "action": "元FBXとModelImporter設定を確認してください。",
        })
        outcome["overall"] = "PARTIAL"
    return outcome
