from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _entities(canonical: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in canonical["observed"].get("entities", [])}


def _all_anomalies(canonical: dict[str, Any]) -> list[dict[str, Any]]:
    return list(canonical.get("observed", {}).get("anomalies", [])) + list(canonical.get("derived", {}).get("adapterAnomalies", []))


def _prefab_features(prefab_id: str, entities: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    children = [e["to"] for e in edges if e.get("from") == prefab_id and e.get("role") == "CONTAINS"]
    objects = [entities[x] for x in children if x in entities]
    types = Counter(x.get("attributes", {}).get("type") for x in objects)
    material_edges = [e for e in edges if e.get("from") in children and e.get("role") == "BINDS_MATERIAL"]
    mesh_edges = [e for e in edges if e.get("from") in children and e.get("role") == "USES_MESH"]
    animator = [x for x in objects if x.get("attributes", {}).get("type") == "UnityEngine.Animator"]
    skinned = [x for x in objects if x.get("attributes", {}).get("type") == "UnityEngine.SkinnedMeshRenderer"]
    return {
        "objectTypeCounts": sorted((str(k), v) for k, v in types.items()),
        "objectCount": len(objects),
        "animatorCount": len(animator),
        "avatarCount": sum(bool(x.get("attributes", {}).get("hasAvatar")) for x in animator),
        "validAvatarCount": sum(bool(x.get("attributes", {}).get("avatarIsValid")) for x in animator),
        "humanAvatarCount": sum(bool(x.get("attributes", {}).get("avatarIsHuman")) for x in animator),
        "skinnedMeshRendererCount": len(skinned),
        "materialSlotCount": len(material_edges),
        "uniqueMeshCount": len({e["to"] for e in mesh_edges}),
        "blendShapeCount": sum((x.get("attributes", {}).get("blendShapeCount") or 0) for x in skinned),
        "boneReferenceCount": sum((x.get("attributes", {}).get("boneCount") or 0) for x in skinned),
        "rootBoneCount": sum(bool(x.get("attributes", {}).get("hasRootBone")) for x in skinned),
    }


def _signature(features: dict[str, Any]) -> dict[str, Any]:
    payload = {k: features[k] for k in sorted(features)}
    return {"algorithmVersion": "structural-v1", "digest": _digest(payload), "features": payload}


def _dependencies(entities: dict[str, dict[str, Any]], edges: list[dict[str, Any]], anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for edge in edges:
        role = edge.get("role")
        if role == "BINDS_MATERIAL": kind = "MATERIAL_BINDING"
        elif role == "REFERENCES_TEXTURE": kind = "TEXTURE_VISUAL"
        elif role == "USES_MESH": kind = "STRUCTURAL_HARD"
        elif role in ("INSTANCE_OF_SOURCE", "INSTANCE_OF_ORIGINAL_SOURCE"): kind = "SOURCE_IDENTITY"
        else: continue
        result.append({"kind": kind, "status": "OBSERVED_RESOLVED" if edge.get("resolved", True) else "OBSERVED_UNRESOLVED", "role": role})
    for anomaly in anomalies:
        if anomaly.get("code") == "MAT_TEXTURE_REFERENCE_UNRESOLVED":
            result.append({"kind": "TEXTURE_VISUAL", "status": "OBSERVED_UNRESOLVED", "role": "REFERENCES_TEXTURE"})
    return result


def _texture_graph(entities: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    role_map = {
        "_MainTex": "BASE_COLOR", "_BaseMap": "BASE_COLOR", "_BumpMap": "NORMAL",
        "_NormalMap": "NORMAL", "_OcclusionMap": "OCCLUSION", "_EmissionMap": "EMISSION",
        "_MetallicGlossMap": "METALLIC_ROUGHNESS", "_MaskTex": "MASK",
    }
    properties = Counter()
    resolved = Counter()
    for edge in edges:
        if edge.get("role") != "REFERENCES_TEXTURE": continue
        property_name = edge.get("property") or "UNKNOWN_PROPERTY"
        role = role_map.get(property_name, "OTHER")
        properties[role] += 1
        if edge.get("resolved", True): resolved[role] += 1
    return {"roleCounts": dict(sorted(properties.items())), "resolvedRoleCounts": dict(sorted(resolved.items())), "unknownRoleCount": properties.get("OTHER", 0) + properties.get("UNKNOWN_PROPERTY", 0)}


def analyze_observation(canonical: dict[str, Any]) -> dict[str, Any]:
    entities = _entities(canonical)
    edges = canonical["observed"].get("edges", [])
    anomalies = _all_anomalies(canonical)
    prefab_ids = [x["id"] for x in canonical["observed"].get("entities", []) if x.get("kind") == "prefab"]
    signatures = {}
    skeleton = {}
    meshes = {}
    for prefab_id in prefab_ids:
        features = _prefab_features(prefab_id, entities, edges)
        signatures[prefab_id] = _signature(features)
        skeleton_values = {"animatorCount": features["animatorCount"], "boneReferenceCount": features["boneReferenceCount"], "rootBoneCount": features["rootBoneCount"], "humanAvatarCount": features["humanAvatarCount"]}
        skeleton[prefab_id] = {"algorithmVersion": "skeleton-v1", "status": "OBSERVED", "digest": _digest(skeleton_values)}
        meshes[prefab_id] = {"algorithmVersion": "mesh-v1", "status": "STRUCTURAL_ONLY", "digest": _digest({"skinnedMeshRendererCount": features["skinnedMeshRendererCount"], "uniqueMeshCount": features["uniqueMeshCount"], "blendShapeCount": features["blendShapeCount"]})}
    # Public analysis keys are positional only within a sorted structural class;
    # they never expose source path, name, GUID, or input order.
    ordered = sorted(signatures.items(), key=lambda pair: pair[1]["digest"])
    signature_sources = {"prefab": {}, "skeleton": {}, "mesh": {}}
    signatures = {f"candidate-{index}": value for index, (prefab_id, value) in enumerate(ordered)}
    skeleton = {f"candidate-{index}": skeleton[prefab_id] for index, (prefab_id, _) in enumerate(ordered)}
    meshes = {f"candidate-{index}": meshes[prefab_id] for index, (prefab_id, _) in enumerate(ordered)}
    for index, (prefab_id, _) in enumerate(ordered):
        signature_sources["prefab"][f"candidate-{index}"] = prefab_id
        signature_sources["skeleton"][f"candidate-{index}"] = prefab_id
        signature_sources["mesh"][f"candidate-{index}"] = prefab_id
    groups = defaultdict(list)
    for candidate_id, sig in signatures.items(): groups[sig["digest"]].append(candidate_id)
    clusters = [{"signature": key, "members": sorted(value), "size": len(value)} for key, value in sorted(groups.items())]
    distinct = len(signatures)
    incomplete = bool(canonical.get("coverage", {}).get("unknown") or canonical.get("coverage", {}).get("unsupported") or any(item.get("status") == "OBSERVED_UNRESOLVED" for item in _dependencies(entities, edges, anomalies)))
    if distinct == 0: classification = "NO_CANDIDATE"
    elif incomplete: classification = "NO_COMPLETE_CANDIDATE"
    elif len(groups) == 1 and len(signatures) == 1: classification = "UNIQUE_STRUCTURAL_CANDIDATE"
    elif len(groups) == 1: classification = "MULTIPLE_VALID_VARIANTS"
    else: classification = "USER_CHOICE_REQUIRED"
    experiments = []
    if classification in {"USER_CHOICE_REQUIRED", "NO_COMPLETE_CANDIDATE"}:
        experiments.append({"code": "COMPARE_CANDIDATE_SEMANTICS", "status": "PROPOSED", "reason": "structural evidence is not sufficient for automatic selection"})
    for anomaly in anomalies:
        experiments.append({"code": "RECHECK_" + str(anomaly.get("code", "UNKNOWN")), "status": "PROPOSED"})
    return {
        "analysisVersion": "1",
        "inputProvenance": canonical.get("provenance", {}),
        "coverage": canonical.get("coverage", {}),
        "prefabSignatures": signatures,
        "skeletonSignatures": skeleton,
        "meshSignatures": meshes,
        "packageSignature": {"algorithmVersion": "package-v1", "status": "DERIVED", "digest": _digest(sorted(value["digest"] for value in signatures.values()))},
        "signatureSources": signature_sources,
        "clusters": clusters,
        "candidateComparison": {"classification": classification, "candidateCount": distinct, "automaticSelection": False},
        "dependencies": _dependencies(entities, edges, anomalies),
        "materialTextureGraph": _texture_graph(entities, edges),
        "anomalies": anomalies,
        "experiments": experiments,
    }
