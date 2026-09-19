from __future__ import annotations

import hashlib
import re
from typing import Any


class InputInvalid(ValueError):
    pass


_GUID = re.compile(r"(?i)^[0-9a-f]{32}$")


def _id(kind: str, *parts: Any) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return f"{kind}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _raw_observed(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    version = str(raw.get("schemaVersion", ""))
    if version == "0.2" and isinstance(raw.get("observed"), dict):
        return "0.2", raw["observed"]
    if version == "0.1" and isinstance(raw.get("prefabs"), list):
        return "0.1", raw
    raise InputInvalid(f"INPUT_INVALID: unsupported or malformed schema {version!r}")


def _add_entity(entities: list[dict[str, Any]], kind: str, identity: Any, attributes: dict[str, Any]) -> str:
    entity_id = _id(kind, identity, attributes.get("type"), attributes.get("path"), attributes.get("ordinal"))
    if any(item["id"] == entity_id for item in entities):
        return entity_id
    entities.append({"id": entity_id, "kind": kind, "identity": identity, "attributes": attributes})
    return entity_id


def adapt_observation(raw: dict[str, Any], *, raw_sha256: str, source_label: str) -> dict[str, Any]:
    source_schema, observed = _raw_observed(raw)
    entities: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    supported = ["prefab", "object", "renderer"]
    coverage_unknown = []
    if source_schema == "0.2":
        supported += ["mesh", "material", "texture_property", "property_modification"]
    else:
        coverage_unknown = ["mesh", "material", "texture_property", "property_modification"]
    coverage = {"supported": supported, "unknown": coverage_unknown, "unsupported": []}
    for prefab_ordinal, prefab in enumerate(observed.get("prefabs", [])):
        prefab_identity = (prefab.get("guid"), prefab.get("assetPath"), prefab_ordinal)
        prefab_id = _add_entity(entities, "prefab", prefab_identity, {"path": prefab.get("assetPath"), "ordinal": prefab_ordinal, "guid": prefab.get("guid")})
        seen_global: dict[str, str] = {}
        for object_ordinal, obj in enumerate(prefab.get("objects", [])):
            object_identity = obj.get("globalObjectId") or (obj.get("guid"), obj.get("localFileID"), object_ordinal)
            object_attrs = {
                "type": obj.get("type"), "path": obj.get("hierarchyPath"),
                "ordinal": object_ordinal, "globalObjectId": obj.get("globalObjectId"),
                "hasAvatar": obj.get("hasAvatar"), "avatarIsHuman": obj.get("avatarIsHuman"),
                "avatarIsValid": obj.get("avatarIsValid"), "hasRootBone": obj.get("hasRootBone"),
                "blendShapeCount": obj.get("blendShapeCount"), "boneCount": obj.get("boneCount"),
            }
            object_id = _add_entity(entities, "object", object_identity, object_attrs)
            edges.append({"from": prefab_id, "role": "CONTAINS", "to": object_id, "ordinal": object_ordinal})
            global_id = obj.get("globalObjectId")
            if global_id and global_id in seen_global and seen_global[global_id] != obj.get("type"):
                anomalies.append({"code": "IDENTITY_COLLISION", "severity": "ERROR", "entity": object_id, "evidence": {"globalObjectId": global_id}})
            if global_id: seen_global[global_id] = obj.get("type")
            for material_ordinal, material in enumerate(obj.get("materials", [])):
                if not material.get("guid"):
                    anomalies.append({"code": "MAT_SLOT_EMPTY", "severity": "WARNING", "entity": object_id, "evidence": {"slot": material.get("slot", material_ordinal)}})
                    continue
                material_id = _add_entity(entities, "material", (material.get("guid"), material.get("localFileID")), {"type": "Material", "shader": material.get("shaderName"), "slot": material.get("slot", material_ordinal)})
                edges.append({"from": object_id, "role": "BINDS_MATERIAL", "to": material_id, "ordinal": material.get("slot", material_ordinal)})
                for prop_ordinal, texture in enumerate(material.get("textureProperties", [])):
                    if texture.get("guid"):
                        texture_id = _add_entity(entities, "texture", (texture.get("guid"), texture.get("localFileID")), {"type": "Texture", "property": texture.get("propertyName")})
                        edges.append({"from": material_id, "role": "REFERENCES_TEXTURE", "to": texture_id, "property": texture.get("propertyName"), "ordinal": prop_ordinal, "resolved": texture.get("resolved", True)})
                    elif texture.get("propertyName"):
                        anomalies.append({"code": "MAT_TEXTURE_REFERENCE_UNRESOLVED", "severity": "WARNING", "entity": material_id, "evidence": {"property": texture.get("propertyName")}})
            if obj.get("meshGuid"):
                mesh_id = _add_entity(entities, "mesh", (obj.get("meshGuid"), obj.get("meshLocalFileID")), {"type": "Mesh", "blendShapeCount": obj.get("blendShapeCount"), "boneCount": obj.get("boneCount")})
                edges.append({"from": object_id, "role": "USES_MESH", "to": mesh_id})
            if obj.get("sourceGuid"):
                source_id = _add_entity(entities, "asset", (obj.get("sourceGuid"), obj.get("sourceLocalFileID")), {"type": obj.get("sourceType"), "path": obj.get("sourceAssetPath")})
                edges.append({"from": object_id, "role": "INSTANCE_OF_SOURCE", "to": source_id})
            if obj.get("originalSourceGuid"):
                original_id = _add_entity(entities, "asset", (obj.get("originalSourceGuid"), obj.get("originalSourceLocalFileID")), {"type": obj.get("originalSourceType"), "path": obj.get("originalSourceAssetPath")})
                edges.append({"from": object_id, "role": "INSTANCE_OF_ORIGINAL_SOURCE", "to": original_id})
        for modification in prefab.get("propertyModifications", []):
            if modification.get("resolutionStatus") not in (None, "RESOLVED_BY_PREFAB_API"):
                anomalies.append({"code": "PROPERTY_REFERENCE_UNRESOLVED", "severity": "WARNING", "entity": prefab_id, "evidence": {"status": modification.get("resolutionStatus")}})
    if not observed.get("prefabs"):
        coverage["unknown"].append("prefab_observation")
    return {
        "canonicalVersion": "1",
        "producer": {"sourceSchema": source_schema, "unityVersion": raw.get("unityVersion", observed.get("unityVersion")), "accessMethod": raw.get("accessMethod", "UNKNOWN")},
        "provenance": {"rawSha256": raw_sha256, "sourceLabel": source_label, "runId": raw.get("runId", observed.get("runId"))},
        "coverage": coverage,
        "observed": {"entities": entities, "edges": edges, "anomalies": list(observed.get("anomalies", []))},
        "derived": {"adapterAnomalies": anomalies},
    }
