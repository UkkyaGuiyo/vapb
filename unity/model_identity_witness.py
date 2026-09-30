"""Validate an optional Unity-observed bridge to native FBX model identities.

The witness supplies generated subasset IDs only. Prefab, Material, and
occurrence semantics must still come from the UnityPackage itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Mapping

from ..blender.fbx_receipt import RawFbxSemanticIndex, source_sha256


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_GUID = re.compile(r"[0-9a-f]{32}\Z")
_UNITY_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+[abfpc][0-9]+\Z")


class ModelWitnessError(ValueError):
    pass


@dataclass(frozen=True)
class ModelAssetRevision:
    fbx_sha256: str
    meta_sha256: str
    fbx_index: RawFbxSemanticIndex
    skin_bone_uids: Mapping[int, frozenset[str]] | None = None


@dataclass(frozen=True)
class ModelIdentityRow:
    asset_guid: str
    model_uid: int
    geometry_uid: int
    transform_local_id: int
    game_object_local_id: int
    class_id: int
    renderer_local_id: int
    mesh_local_id: int
    bone_model_uids: tuple[int, ...] = ()
    root_bone_model_uid: int | None = None
    source_bone_world_matrices: tuple[tuple[float, ...], ...] = ()


class ModelWitnessIndex:
    def __init__(self, rows: list[ModelIdentityRow],
                 source_shas: Mapping[str, str]):
        self.rows = tuple(rows)
        self.source_shas = dict(source_shas)
        self._by_mesh = {(row.asset_guid, row.mesh_local_id): row for row in rows}

    def mesh(self, asset_guid: str, mesh_local_id: int) -> ModelIdentityRow | None:
        return self._by_mesh.get((str(asset_guid).lower(), int(mesh_local_id)))

    def source_rows(self, asset_guid: str) -> tuple[ModelIdentityRow, ...]:
        guid = str(asset_guid).lower()
        return tuple(row for row in self.rows if row.asset_guid == guid)


def _fields(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ModelWitnessError(f"Invalid {label} fields")
    return value


def _hex(value: object, pattern: re.Pattern, label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value.lower()):
        raise ModelWitnessError(f"Invalid {label}")
    return value.lower()


def _signed(value: object, label: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        raise ModelWitnessError(f"Invalid {label}")
    number = int(value)
    if number == 0 or not -(2 ** 63) <= number < 2 ** 63:
        raise ModelWitnessError(f"Invalid {label}")
    return number


def validate_model_witness(document: object, package_sha256: str,
                           revisions: Mapping[str, ModelAssetRevision]) -> ModelWitnessIndex:
    """Reject the whole sidecar if any identity or source revision is unclear."""
    root = _fields(document, {"schema_version", "source_unitypackage_sha256",
                              "unity_version", "source_validation", "assets"}, "witness")
    if root["schema_version"] not in ("vapb-model-identity-witness-v1", "vapb-model-identity-witness-v2"):
        raise ModelWitnessError("Unsupported witness schema")
    validation = _fields(root["source_validation"],
                         {"probe_pass", "original_revision_equivalent"},
                         "source validation")
    if validation["probe_pass"] is not True or validation["original_revision_equivalent"] is not True:
        raise ModelWitnessError("Unity source witness did not pass revision checks")
    expected_package = _hex(package_sha256, _SHA, "source package SHA256")
    if _hex(root["source_unitypackage_sha256"], _SHA, "witness package SHA256") != expected_package:
        raise ModelWitnessError("Source package revision mismatch")
    version = root["unity_version"]
    if not isinstance(version, str) or not _UNITY_VERSION.fullmatch(version):
        raise ModelWitnessError("Unity version is missing or invalid")
    assets = root["assets"]
    if not isinstance(assets, list) or not assets:
        raise ModelWitnessError("Witness has no model assets")
    rows: list[ModelIdentityRow] = []
    seen_assets: set[str] = set()
    seen_meshes: set[tuple[str, int]] = set()
    seen_renderers: set[tuple[str, int]] = set()
    for asset_value in assets:
        asset = _fields(asset_value, {"asset_guid", "source_fbx_sha256",
                                      "source_meta_sha256", "models"}, "asset")
        guid = _hex(asset["asset_guid"], _GUID, "asset GUID")
        if guid in seen_assets:
            raise ModelWitnessError("Duplicate witness asset")
        seen_assets.add(guid)
        revision = revisions.get(guid)
        if revision is None:
            raise ModelWitnessError("Witness asset is not in the source package")
        if (_hex(asset["source_fbx_sha256"], _SHA, "FBX SHA256") != revision.fbx_sha256.lower()
                or _hex(asset["source_meta_sha256"], _SHA, "meta SHA256") != revision.meta_sha256.lower()):
            raise ModelWitnessError("FBX or importer revision mismatch")
        models = asset["models"]
        if not isinstance(models, list) or not models:
            raise ModelWitnessError("Witness asset has no model rows")
        seen_models: set[int] = set()
        for model_value in models:
            model = _fields(model_value, {"model_uid", "geometry_uid",
                                          "transform_local_id", "game_object_local_id",
                                          "renderers"}, "model")
            model_uid = _signed(model["model_uid"], "Model UID")
            geometry_uid = _signed(model["geometry_uid"], "Geometry UID")
            transform_id = _signed(model["transform_local_id"], "Transform localID")
            owner_id = _signed(model["game_object_local_id"], "GameObject localID")
            if (model_uid in seen_models or not revision.fbx_index.unique_source_model(model_uid)
                    or revision.fbx_index.geometry_for_model(model_uid) != geometry_uid):
                raise ModelWitnessError("Model/Geometry source relation is ambiguous or mismatched")
            seen_models.add(model_uid)
            renderers = model["renderers"]
            if not isinstance(renderers, list) or not renderers:
                raise ModelWitnessError("Witness model has no Renderer")
            for renderer_value in renderers:
                fields = {"class_id", "renderer_local_id", "mesh_local_id"}
                if root['schema_version'].endswith('v2') and isinstance(renderer_value, dict) and 'skin' in renderer_value:
                    fields.add('skin')
                renderer = _fields(renderer_value, fields, "Renderer")
                class_id = renderer["class_id"]
                if type(class_id) is not int or class_id not in (23, 137):
                    raise ModelWitnessError("Unsupported Renderer class")
                renderer_id = _signed(renderer["renderer_local_id"], "Renderer localID")
                mesh_id = _signed(renderer["mesh_local_id"], "Mesh localID")
                renderer_key = (guid, renderer_id)
                mesh_key = (guid, mesh_id)
                if renderer_key in seen_renderers or mesh_key in seen_meshes:
                    raise ModelWitnessError("Duplicate generated subasset identity")
                seen_renderers.add(renderer_key)
                seen_meshes.add(mesh_key)
                bone_uids, root_uid, source_frames = (), None, ()
                if 'skin' in renderer:
                    skin_fields = {'ordered_bone_model_uids', 'root_bone_model_uid'}
                    if 'source_bone_world_matrices' in renderer['skin']:
                        skin_fields.add('source_bone_world_matrices')
                    skin = _fields(renderer['skin'], skin_fields, 'Skin')
                    values = skin['ordered_bone_model_uids']
                    if class_id != 137 or not isinstance(values, list) or not values:
                        raise ModelWitnessError('Invalid witnessed Skin slots')
                    bone_uids = tuple(_signed(value, 'Bone Model UID') for value in values)
                    root_uid = _signed(skin['root_bone_model_uid'], 'rootBone Model UID')
                    if (len(set(bone_uids)) != len(bone_uids) or root_uid not in bone_uids
                            or any(not revision.fbx_index.unique_source_model(uid) for uid in bone_uids)
                            or revision.skin_bone_uids is None
                            or revision.skin_bone_uids.get(model_uid) != frozenset(str(uid) for uid in bone_uids)):
                        raise ModelWitnessError('Skin slots disagree with source FBX membership')
                    if 'source_bone_world_matrices' in skin:
                        frames = skin['source_bone_world_matrices']
                        if not isinstance(frames, list) or len(frames) != len(bone_uids):
                            raise ModelWitnessError('Skin source frame count mismatch')
                        for frame in frames:
                            if (not isinstance(frame, list) or len(frame) != 16
                                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in frame)
                                    or any(abs(frame[i]-value) > 1e-6 for i, value in ((3,0),(7,0),(11,0),(15,1)))):
                                raise ModelWitnessError('Invalid source Bone frame')
                            a,b,c,d,e,f,g,h,i = (frame[n] for n in (0,4,8,1,5,9,2,6,10))
                            if abs(a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)) < 1e-12:
                                raise ModelWitnessError('Singular source Bone frame')
                        source_frames = tuple(tuple(float(v) for v in frame) for frame in frames)
                rows.append(ModelIdentityRow(guid, model_uid, geometry_uid, transform_id,
                                             owner_id, class_id, renderer_id, mesh_id, bone_uids, root_uid, source_frames))
    return ModelWitnessIndex(rows, {
        asset["asset_guid"].lower(): asset["source_fbx_sha256"].lower()
        for asset in assets
    })


def load_model_witness(path: Path, package_sha256: str, asset_db) -> ModelWitnessIndex:
    """Load only model revisions actually present in the extracted package."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        assets = document["assets"]
        if not isinstance(assets, list):
            raise ModelWitnessError("Invalid witness asset list")
        revisions = {}
        for asset in assets:
            guid = _hex(asset["asset_guid"], _GUID, "asset GUID")
            entry = asset_db.find_guid(guid)
            if entry is None or entry.path.suffix.lower() != ".fbx":
                raise ModelWitnessError("Witness model is not in the package")
            meta = Path(str(entry.path) + ".meta")
            if not entry.path.is_file() or not meta.is_file():
                raise ModelWitnessError("Witness source FBX or importer meta is unavailable")
            skin_membership = {}
            if document.get('schema_version') == 'vapb-model-identity-witness-v2':
                from ..blender.fbx_witness import source_skin_bone_uids
                for model in asset['models']:
                    if any('skin' in renderer for renderer in model['renderers']):
                        skin_membership[int(model['model_uid'])] = source_skin_bone_uids(
                            entry.path, model['model_uid'], model['geometry_uid'])
            revisions[guid] = ModelAssetRevision(
                source_sha256(entry.path), source_sha256(meta),
                RawFbxSemanticIndex.from_file(entry.path),
                skin_membership,
            )
        return validate_model_witness(document, package_sha256, revisions)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        if isinstance(exc, ModelWitnessError):
            raise
        raise ModelWitnessError("Invalid or unavailable model witness") from exc


def build_model_witness_from_probe(probe: dict, report: dict, package_sha256: str,
                                   revisions: Mapping[str, ModelAssetRevision]) -> dict:
    """Promote a passing first-party Unity probe to a scoped sidecar.

    Raw FBX proves Geometry UID; the Unity probe supplies generated IDs. Bone
    and other non-Mesh Model rows are excluded rather than given guessed IDs.
    """
    if (not isinstance(probe, dict) or probe.get("schema_version") != "vapb-source-fbx-model-witness-1"
            or not isinstance(report, dict)
            or any(report.get(key) is not True for key in
                   ("pass", "originalRevisionEquivalent", "sourceMetaRestored", "sourceRawRestored"))):
        raise ModelWitnessError("Unity source probe did not pass")
    guid = _hex(probe.get("model_guid"), _GUID, "probe model GUID")
    revision = revisions.get(guid)
    if revision is None:
        raise ModelWitnessError("Probe model is not in the source package")
    models = probe.get("models")
    if not isinstance(models, list):
        raise ModelWitnessError("Probe model list is invalid")
    selected = []
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("renderers"), list):
            raise ModelWitnessError("Probe model is invalid")
        if not model["renderers"]:
            continue
        uid = _signed(model.get("model_uid"), "probe Model UID")
        geometry = revision.fbx_index.geometry_for_model(uid)
        if geometry is None or not revision.fbx_index.unique_source_model(uid):
            raise ModelWitnessError("Probe Model has no unique source Geometry")
        renderer_rows = []
        for renderer in model["renderers"]:
            if not isinstance(renderer, dict):
                raise ModelWitnessError("Probe Renderer is invalid")
            try:
                class_id = int(renderer.get("class_id"))
            except (TypeError, ValueError) as exc:
                raise ModelWitnessError("Probe Renderer class is invalid") from exc
            renderer_rows.append({
                "class_id": class_id,
                "renderer_local_id": renderer.get("renderer_local_id"),
                "mesh_local_id": renderer.get("mesh_local_id"),
            })
        selected.append({
            "model_uid": str(uid), "geometry_uid": str(geometry),
            "transform_local_id": model.get("transform_local_id"),
            "game_object_local_id": model.get("game_object_local_id"),
            "renderers": renderer_rows,
        })
    document = {
        "schema_version": "vapb-model-identity-witness-v1",
        "source_unitypackage_sha256": package_sha256,
        "unity_version": probe.get("unity_version"),
        "source_validation": {"probe_pass": True, "original_revision_equivalent": True},
        "assets": [{"asset_guid": guid,
                    "source_fbx_sha256": probe.get("source_fbx_sha256"),
                    "source_meta_sha256": probe.get("source_meta_sha256"),
                    "models": selected}],
    }
    validate_model_witness(document, package_sha256, revisions)
    return document
