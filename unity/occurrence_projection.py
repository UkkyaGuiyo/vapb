"""Project actual serialized Prefab instance edges to scoped Renderer occurrences."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Callable, Sequence

from .prefab_parser import PrefabData, ref_file_id, ref_guid


@dataclass(frozen=True)
class PrefabSource:
    prefab: PrefabData | None
    package_id: str
    member_id: str
    revision_sha256: str
    asset_guid: str = ""

    @classmethod
    def from_prefab(cls, prefab: PrefabData, package_id: str, member_id: str) -> "PrefabSource":
        return cls(prefab, package_id, member_id, hashlib.sha256(prefab.path.read_bytes()).hexdigest())


@dataclass
class ProjectionResult:
    records: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"records": self.records, "issues": self.issues}


def _witnessed_prefab_model(record: dict, witness):
    """Prove a Prefab-local Renderer reaches a witnessed model Mesh through its source chain."""
    if witness is None:
        return None
    try:
        if record["occurrence_id"] != occurrence_identity(record):
            return None
        path = record["instance_edge_path"]
        if not path or record["source_key"]["source_kind"] != "PREFAB_LOCAL":
            return None
        expected = (record["root_package_id"], record["root_asset_guid"],
                    record["root_revision_sha256"])
        for edge in path:
            if (edge["container_package_id"], edge["container_asset_guid"],
                    edge["container_revision_sha256"]) != expected:
                return None
            expected = (edge["source_package_id"], edge["source_prefab_guid"],
                        edge["source_revision_sha256"])
        if expected != (record["source_package_id"],
                        record["source_key"]["source_asset_guid"],
                        record["source_revision_sha256"]):
            return None
        mesh = record["mesh"]
        guid = mesh["mesh_guid"].lower()
        if witness.source_shas.get(guid) != mesh["source_sha256"].lower():
            return None
        row = witness.mesh(guid, mesh["mesh_file_id"])
        if row is None or row.asset_guid != guid or row.class_id != record["renderer_class_id"]:
            return None
        return row
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def model_instance_plans(projection: ProjectionResult, model_witness=None) -> list[tuple[str, list[dict], tuple | None]]:
    """Return model edges with exact native targets for witnessed Prefab renderers."""
    result = {}
    for record in projection.records:
        if record.get("source_key", {}).get("source_kind") == "MODEL_SOURCE":
            guid = record["source_key"]["source_asset_guid"]
            target = None
        else:
            row = _witnessed_prefab_model(record, model_witness)
            if row is None:
                continue
            guid = row.asset_guid
            target = (row.model_uid, row.geometry_uid)
        path = record["instance_edge_path"]
        key = (guid, json.dumps(path, sort_keys=True))
        if key not in result:
            result[key] = (path, set() if target is not None else None)
        if target is None:
            result[key] = (path, None)
        elif result[key][1] is not None:
            result[key][1].add(target)
    for issue in projection.issues:
        if issue.get("code") != "UNRESOLVED_SOURCE":
            continue
        guid = issue["source_asset_guid"]
        path = issue["instance_edge_path"]
        key = (guid, json.dumps(path, sort_keys=True))
        if key not in result:
            result[key] = (path, None)
    return [(guid, path, None if targets is None else tuple(sorted(targets)))
            for (guid, _), (path, targets) in result.items()]


def model_instance_sources(projection: ProjectionResult, model_witness=None) -> list[tuple[str, list[dict]]]:
    """Return each model edge once; Prefab-local edges require an exact witness."""
    return [(guid, path) for guid, path, _ in model_instance_plans(projection, model_witness)]


def occurrence_identity(record: dict) -> str:
    """Revision-independent identity of a selected root, edge path, and source Renderer."""
    scope = [record["root_context_id"], record["root_package_id"],
             record["root_member_id"], record["root_asset_guid"],
             [[step["container_package_id"], step["container_asset_guid"],
               step["prefab_instance_file_id"], step["source_package_id"],
               step["source_prefab_guid"]] for step in record["instance_edge_path"]],
             record["source_package_id"], record["source_key"]["source_asset_guid"],
             record["source_key"]["renderer_file_id"]]
    return hashlib.sha256(json.dumps(scope, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def _reference(value: object, *, preserve_raw_file_id: bool = False) -> dict | None:
    if not isinstance(value, dict):
        return None
    guid = ref_guid(value)
    file_id = ref_file_id(value)
    if not guid or file_id is None or file_id == 0:
        return None
    reference = {"guid": guid.lower(), "file_id": file_id}
    if preserve_raw_file_id:
        reference["raw_file_id"] = value.get("fileID")
    return reference


def _source_guid(source: PrefabSource) -> str:
    return (source.asset_guid or (source.prefab.asset_guid if source.prefab else "")).lower()


def _skin_projection(prefab: PrefabData, renderer: object) -> dict:
    """Only direct, local serialized Transform references establish skin slots."""
    unknown = {"status": "UNKNOWN", "bones": [], "root_bone_transform_file_id": ""}
    values = renderer.data.get("m_Bones")
    root_ref = renderer.data.get("m_RootBone")
    if not isinstance(values, list) or not values or not isinstance(root_ref, dict):
        return unknown
    refs = values + [root_ref]
    if any(not isinstance(ref, dict) or "guid" in ref or ref_file_id(ref) in (None, 0)
           for ref in refs):
        return unknown
    ids = [ref_file_id(ref) for ref in refs]
    if len(set(ids[:-1])) != len(ids) - 1 or any(file_id not in prefab.transforms for file_id in ids):
        return unknown
    rows = []
    for file_id in ids[:-1]:
        transform = prefab.transforms[file_id]
        owner = prefab.game_objects.get(transform.game_object_id)
        if owner is None:
            return unknown
        rows.append({"transform_file_id": str(file_id), "display_name": owner.name,
                     "parent_transform_file_id": str(transform.parent_id or 0)})
    root_transform = prefab.transforms[ids[-1]]
    root_owner = prefab.game_objects.get(root_transform.game_object_id)
    if root_owner is None:
        return unknown
    return {"status": "EXACT", "bones": rows,
            "root_bone_transform_file_id": str(ids[-1]),
            "root_bone_display_name": root_owner.name}


def project_occurrences(
    root: PrefabSource,
    root_context_id: str,
    source_loader: Callable[[str, str], PrefabSource | Sequence[PrefabSource] | None],
    *,
    model_witness=None,
) -> ProjectionResult:
    """Resolve one selected root; source_loader receives container package ID and GUID.

    Only directly serialized Renderer documents establish component identity.
    Unreadable binary model source relations remain unresolved.
    """
    result = ProjectionResult()

    def issue(code: str, path: list[dict], **details: object) -> None:
        result.issues.append({"code": code, "root_context_id": root_context_id,
                              "instance_edge_path": [dict(step) for step in path], **details})

    if not root_context_id or not root.package_id or not root.member_id or not root.revision_sha256 or not _source_guid(root):
        issue("INVALID_ROOT_SCOPE", [])
        return result

    def visit(source: PrefabSource, path: list[dict], active: tuple[tuple[str, str], ...]) -> list[dict]:
        guid = _source_guid(source)
        identity = (source.package_id, guid)
        if identity in active:
            issue("CYCLE", path, source_package_id=source.package_id, source_asset_guid=guid)
            return []
        if source.prefab is None:
            rows = (model_witness.source_rows(guid) if model_witness is not None
                    and model_witness.source_shas.get(guid) == source.revision_sha256 else ())
            if not rows:
                issue("UNRESOLVED_SOURCE", path, source_package_id=source.package_id, source_asset_guid=guid)
                return []
            records = []
            for row in rows:
                record = {
                    "root_context_id": root_context_id,
                    "root_package_id": root.package_id,
                    "root_member_id": root.member_id,
                    "root_asset_guid": _source_guid(root),
                    "root_revision_sha256": root.revision_sha256,
                    "instance_edge_path": [dict(step) for step in path],
                    "source_package_id": source.package_id,
                    "source_member_id": source.member_id,
                    "source_revision_sha256": source.revision_sha256,
                    "source_key": {"source_kind": "MODEL_SOURCE", "source_asset_guid": guid,
                                   "renderer_file_id": row.renderer_local_id},
                    "renderer_class_id": row.class_id,
                    "owner": {"source_kind": "MODEL_SOURCE", "source_asset_guid": guid,
                              "owner_game_object_id": row.game_object_local_id},
                    "owner_name": "",
                    "mesh": {"mesh_guid": guid, "mesh_file_id": row.mesh_local_id},
                    "materials": {},
                    "material_slot_count": None,
                    "material_status": "PARTIAL",
                }
                record["occurrence_id"] = occurrence_identity(record)
                records.append(record)
            return records
        if not source.revision_sha256 or not source.member_id or not guid or guid != source.prefab.asset_guid.lower():
            issue("INVALID_SOURCE_SCOPE", path, source_package_id=source.package_id, source_asset_guid=guid)
            return []
        prefab = source.prefab
        file_ids = [document.file_id for document in prefab.documents]
        if len(file_ids) != len(set(file_ids)):
            issue("DUPLICATE_SOURCE_FILE_ID", path, source_asset_guid=guid)
            return []
        documents = {d.file_id: d for d in prefab.documents}
        records: list[dict] = []
        for renderer in prefab.renderer_documents():
            owner_id = ref_file_id(renderer.data.get("m_GameObject"))
            owner = prefab.game_objects.get(owner_id) if owner_id is not None else None
            if owner is None or renderer.file_id not in owner.component_ids:
                issue("INVALID_OWNER", path, source_asset_guid=guid, renderer_file_id=renderer.file_id)
                continue
            mesh = _reference(renderer.data.get("m_Mesh"))
            if renderer.class_id == 23:
                filters = [documents[cid] for cid in owner.component_ids
                           if cid in documents and documents[cid].class_id == 33
                           and ref_file_id(documents[cid].data.get("m_GameObject")) == owner_id]
                if len(filters) != 1:
                    issue("INVALID_MESH_FILTER", path, source_asset_guid=guid, renderer_file_id=renderer.file_id)
                    continue
                mesh = _reference(filters[0].data.get("m_Mesh"))
            if mesh is None:
                issue("INVALID_MESH", path, source_asset_guid=guid, renderer_file_id=renderer.file_id)
                continue
            if "m_Materials" in renderer.data:
                values = renderer.data["m_Materials"]
            elif "m_Material" in renderer.data:
                values = [renderer.data["m_Material"]]
            else:
                values = []
            if not isinstance(values, list):
                values = [values]
            materials: dict[int, dict | None] = {}
            material_status = "EXACT"
            for slot, value in enumerate(values):
                if isinstance(value, dict) and ref_file_id(value) == 0:
                    materials[slot] = None
                elif reference := _reference(value, preserve_raw_file_id=True):
                    materials[slot] = {**reference, "source_package_id": source.package_id}
                else:
                    material_status = "UNKNOWN"
                    materials[slot] = None
                    issue("MALFORMED_MATERIAL_REFERENCE", path, source_asset_guid=guid,
                          renderer_file_id=renderer.file_id, slot_index=slot)
            record = {
                "root_context_id": root_context_id,
                "root_package_id": root.package_id,
                "root_member_id": root.member_id,
                "root_asset_guid": _source_guid(root),
                "root_revision_sha256": root.revision_sha256,
                "instance_edge_path": [dict(step) for step in path],
                "source_package_id": source.package_id,
                "source_member_id": source.member_id,
                "source_revision_sha256": source.revision_sha256,
                "source_key": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": guid,
                               "renderer_file_id": renderer.file_id},
                "renderer_class_id": renderer.class_id,
                "owner": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": guid,
                          "owner_game_object_id": owner_id},
                "owner_name": owner.name,
                "mesh": {"mesh_guid": mesh["guid"], "mesh_file_id": mesh["file_id"]},
                "materials": materials,
                "material_slot_count": len(values),
                "material_status": material_status,
            }
            if renderer.class_id == 137:
                record["skin"] = _skin_projection(prefab, renderer)
                weights = renderer.data.get('m_BlendShapeWeights')
                record['blend_shape_weights'] = ([float(value) for value in weights]
                    if isinstance(weights, list) and all(type(value) in (int, float) and math.isfinite(value) for value in weights)
                    else None)
            record["occurrence_id"] = occurrence_identity(record)
            records.append(record)
        for document in prefab.documents:
            if document.class_id != 1001:
                continue
            value = document.data.get("m_SourcePrefab")
            source_ref = _reference(value)
            if source_ref is None:
                wrapped = re.search(r"m_SourcePrefab:\s*\{([^}]*)\}", document.raw, re.DOTALL)
                if wrapped:
                    file_match = re.search(r"\bfileID:\s*(-?\d+)", wrapped.group(1))
                    guid_match = re.search(r"\bguid:\s*([0-9a-fA-F]{32})\b", wrapped.group(1))
                    if file_match and guid_match and int(file_match.group(1)) != 0:
                        source_ref = {"file_id": int(file_match.group(1)),
                                      "guid": guid_match.group(1).lower()}
            if source_ref is None or not re.fullmatch(r"[0-9a-f]{32}", source_ref["guid"]):
                issue("MALFORMED_INSTANCE", path, container_asset_guid=guid,
                      prefab_instance_file_id=document.file_id)
                continue
            child_guid = source_ref["guid"]
            edge = {"container_asset_guid": guid,
                    "container_package_id": source.package_id,
                    "container_revision_sha256": source.revision_sha256,
                    "prefab_instance_file_id": document.file_id,
                    "source_prefab_guid": child_guid}
            child_path = path + [edge]
            resolved = source_loader(source.package_id, child_guid)
            candidates = list(resolved) if isinstance(resolved, (list, tuple)) else ([] if resolved is None else [resolved])
            if not candidates:
                issue("MISSING_SOURCE", child_path, source_asset_guid=child_guid)
                continue
            if len(candidates) != 1:
                issue("AMBIGUOUS_SOURCE", child_path, source_asset_guid=child_guid)
                continue
            child = candidates[0]
            if _source_guid(child) != child_guid:
                issue("SOURCE_GUID_MISMATCH", child_path, source_asset_guid=child_guid)
                continue
            edge["source_package_id"] = child.package_id
            edge["source_member_id"] = child.member_id
            edge["source_revision_sha256"] = child.revision_sha256
            child_records = visit(child, child_path, active + (identity,))
            for modification in prefab.modifications():
                if modification.prefab_instance_file_id != document.file_id:
                    continue
                if re.match(r"^(m_Bones(?:\.|$)|m_RootBone(?:\.|$)|m_Mesh(?:\.|$))", modification.property_path):
                    matches = [record for record in child_records
                               if record["renderer_class_id"] == 137
                               and record["source_key"]["source_asset_guid"] == modification.target_guid.lower()
                               and record["source_key"]["renderer_file_id"] == modification.target_file_id]
                    for record in matches if matches else child_records:
                        if "skin" in record:
                            record["skin"]["status"] = "UNKNOWN"
                    issue("UNRESOLVED_SKIN_OVERRIDE", child_path,
                          target_source_guid=modification.target_guid,
                          target_renderer_file_id=modification.target_file_id)
                    continue
                match = re.fullmatch(r"m_Materials\.Array\.data\[(\d+)\]", modification.property_path)
                if not match:
                    continue
                slot = int(match.group(1))
                matches = [record for record in child_records
                           if record["source_key"]["source_asset_guid"] == modification.target_guid.lower()
                           and record["source_key"]["renderer_file_id"] == modification.target_file_id]
                material = _reference(modification.object_reference, preserve_raw_file_id=True)
                explicit_null = (isinstance(modification.object_reference, dict)
                                 and ref_file_id(modification.object_reference) == 0
                                 and not ref_guid(modification.object_reference))
                if len(matches) != 1 or (material is None and not explicit_null):
                    # A stripped component in the child asset can alias a
                    # Renderer below one of its nested Prefab instances. The
                    # next source local ID may be Unity-generated and absent
                    # from the serialized source, so never treat that alias
                    # as an unrelated override or guess its final Renderer.
                    alias_scope = []
                    alias = (next((item for item in child.prefab.documents
                                   if item.file_id == modification.target_file_id
                                   and item.class_id in (23, 137)
                                   and "stripped" in item.raw), None)
                             if child.prefab is not None
                             and modification.target_guid.lower() == child_guid else None)
                    if alias is not None and not matches:
                        nested_id = ref_file_id(alias.data.get("m_PrefabInstance"))
                        nested = next((item for item in child.prefab.documents
                                       if item.file_id == nested_id and item.class_id == 1001), None)
                        corresponding = _reference(alias.data.get("m_CorrespondingSourceObject"))
                        nested_source = (_reference(nested.data.get("m_SourcePrefab"))
                                         if nested is not None else None)
                        scoped = (corresponding is not None and nested_source is not None
                                  and corresponding["guid"] == nested_source["guid"])
                        if scoped:
                            alias_scope = [record for record in child_records
                                           if record["renderer_class_id"] == alias.class_id
                                           and len(record["instance_edge_path"]) > len(child_path)
                                           and record["instance_edge_path"][len(child_path)]["container_asset_guid"] == child_guid
                                           and record["instance_edge_path"][len(child_path)]["prefab_instance_file_id"] == nested_id]
                        else:
                            # The alias is real but its source/instance edge
                            # is not trustworthy. Bound uncertainty to this
                            # child Prefab, never the selected root.
                            alias_scope = [record for record in child_records
                                           if record["renderer_class_id"] == alias.class_id]
                    for record in matches or alias_scope:
                        record["material_status"] = "UNKNOWN"
                    code = ("UNRESOLVED_ALIAS_OVERRIDE" if alias is not None and not matches
                            else "AMBIGUOUS_OVERRIDE_TARGET" if len(matches) > 1
                            else "UNRESOLVED_OVERRIDE")
                    alias_details = ({"alias_nested_instance_file_id": nested_id,
                                      "uncertainty_scope": "NESTED_INSTANCE" if scoped else "CHILD_PREFAB"}
                                     if alias is not None and not matches else {})
                    issue(code,
                          child_path, target_source_guid=modification.target_guid,
                          target_renderer_file_id=modification.target_file_id, slot_index=slot,
                          **alias_details)
                    continue
                if (matches[0]["material_slot_count"] is not None
                        and slot >= matches[0]["material_slot_count"]):
                    matches[0]["material_status"] = "UNKNOWN"
                    issue("OVERRIDE_SLOT_OUT_OF_RANGE", child_path,
                          target_source_guid=modification.target_guid,
                          target_renderer_file_id=modification.target_file_id, slot_index=slot)
                    continue
                matches[0]["materials"][slot] = (
                    None if explicit_null else {**material, "source_package_id": source.package_id})
            records.extend(child_records)
        return records

    result.records = visit(root, [], ())
    return result
