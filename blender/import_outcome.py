"""Read existing Blender scene import evidence without modifying it."""

from __future__ import annotations

import json

from .dependency_resolver import load_dependency_registry
from .model_witness_bridge import find_witness_consumer
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
    realized_renderer_occurrences = {
        str(obj.get("_vapb_renderer_occurrence_id"))
        for obj in scene.objects
        if obj.type == "MESH" and obj.data is not None
        and obj.get("_vapb_renderer_occurrence_id")
    }
    for record in dependencies:
        occurrence_id = record.get("consumer_occurrence_id")
        if (occurrence_id and record.get("dependency_type") in {
                "PREFAB_RENDERER_MATERIAL", "CLEAR_MATERIAL_SLOT"}
                and find_witness_consumer(record, scene.objects) is not None):
            realized_renderer_occurrences.add(str(occurrence_id))
    outcome = summarize_import_outcome(
        projections, dependencies, verified_null_slots, edited_null_slots,
        realized_renderer_occurrences,
    )
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
