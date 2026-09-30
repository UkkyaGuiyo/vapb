"""Source-side FBX identity and Blender realization receipts.

The receipt deliberately stops at the boundary that the source FBX and the
official Blender importer can prove: FBX Model UID -> Geometry UID -> the
Object created during this import.  Unity local file IDs are not inferred.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import struct
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


RECEIPT_VERSION = "vapb_fbx_realization_receipt_v1"


def _shape_fingerprint(key, basis=None):
    values = bytearray()
    if basis is not None and len(key.data) != len(basis.data):
        raise ValueError('MISSING_KEYBLOCK')
    for index, point in enumerate(key.data):
        xyz = [float(point.co[axis]) - (float(basis.data[index].co[axis]) if basis else 0)
               for axis in range(3)]
        if not all(math.isfinite(value) for value in xyz):
            raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
        values.extend(struct.pack('<3f', *xyz))
    return hashlib.sha256(values).hexdigest()


def persist_shape_receipts(mesh, sha256, geometry_uid, captures):
    """Bind the official importer's returned channel UID to its actual KeyBlock.

    KeyBlocks do not support ID properties. Store import-captured handles as
    Key-local indices with immutable delta/basis corroboration; labels are absent.
    A reorder/edit invalidates this import proof rather than rebinding by search.
    """
    keys = mesh.shape_keys
    blocks = list(keys.key_blocks)
    if len(captures) != len(blocks) - 1:
        raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
    rows = []
    for channel_uid, shape_uid, key in captures:
        index = blocks.index(key)
        if index == 0 or key.relative_key != blocks[0]:
            raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
        rows.append(dict(channel_uid=int(channel_uid), shape_uid=int(shape_uid), key_index=index,
                         delta_sha256=_shape_fingerprint(key, blocks[0])))
    if len({row['channel_uid'] for row in rows}) != len(rows) or len({row['key_index'] for row in rows}) != len(rows):
        raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
    table = dict(schema='vapb-fbx-shape-receipt-1', fbx_sha256=sha256,
                 geometry_uid=int(geometry_uid), basis_sha256=_shape_fingerprint(blocks[0]), channels=rows)
    payload = json.dumps(table, sort_keys=True)
    keys['_vapb_fbx_shape_receipts'] = payload
    keys['_vapb_fbx_shape_receipt_sha256'] = hashlib.sha256(payload.encode()).hexdigest()


def validate_shape_receipts(mesh, sha256, geometry_uid):
    """Return receipt-selected KeyBlocks or reject; never rematch edited keys."""
    keys = getattr(mesh, 'shape_keys', None)
    try:
        payload = keys['_vapb_fbx_shape_receipts']
        if hashlib.sha256(payload.encode()).hexdigest() != keys['_vapb_fbx_shape_receipt_sha256']:
            raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
        table = json.loads(payload)
        if (table['schema'] != 'vapb-fbx-shape-receipt-1' or table['fbx_sha256'] != sha256
                or table['geometry_uid'] != int(geometry_uid)):
            raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
        blocks = list(keys.key_blocks)
        rows = table['channels']
        if len(blocks) != len(rows) + 1 or _shape_fingerprint(blocks[0]) != table['basis_sha256']:
            raise ValueError('MISSING_KEYBLOCK')
        mapped = {}
        used = set()
        for row in rows:
            uid, index = row['channel_uid'], row['key_index']
            if (type(uid) is not int or not uid or uid in mapped or type(index) is not int
                    or index <= 0 or index >= len(blocks) or index in used):
                raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
            key = blocks[index]
            if key.relative_key != blocks[0] or _shape_fingerprint(key, blocks[0]) != row['delta_sha256']:
                raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
            mapped[uid] = key
            used.add(index)
        return mapped
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError('CHANNEL_IDENTITY_UNPROVEN') from exc


def _uid(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class FbxModelLink:
    model_uid: int
    geometry_uid: int


class RawFbxSemanticIndex:
    """The minimal raw-FBX graph needed for realization provenance."""

    def __init__(self, links: list[FbxModelLink], model_uids: list[int] | None = None):
        self.links = tuple(links)
        self._model_uid_counts: dict[int, int] = {}
        for uid in model_uids or []:
            self._model_uid_counts[uid] = self._model_uid_counts.get(uid, 0) + 1
        by_model: dict[int, list[int]] = {}
        for link in links:
            by_model.setdefault(link.model_uid, []).append(link.geometry_uid)
        self._by_model = {key: tuple(value) for key, value in by_model.items()}

    def geometry_for_model(self, model_uid: int) -> int | None:
        values = self._by_model.get(int(model_uid), ())
        return values[0] if len(values) == 1 else None

    def unique_source_model(self, model_uid: int) -> bool:
        return self._model_uid_counts.get(model_uid) == 1

    @classmethod
    def from_file(cls, path: Path) -> "RawFbxSemanticIndex":
        # Blender ships and uses this parser for its official FBX importer.
        # Import it only inside Blender; the pure data model remains testable
        # without a Blender installation.
        from io_scene_fbx.parse_fbx import parse  # type: ignore

        root, _version = parse(str(path), use_namedtuple=True)
        objects = next((item for item in root.elems if item.id == b"Objects"), None)
        connections = next((item for item in root.elems if item.id == b"Connections"), None)
        if objects is None or connections is None:
            return cls([])
        model_uids = [
            _uid(item.props[0])
            for item in objects.elems
            if item.id == b"Model" and item.props and _uid(item.props[0]) is not None
        ]
        models = set(model_uids)
        geometries = {
            _uid(item.props[0])
            for item in objects.elems
            if item.id == b"Geometry"
            and len(item.props) > 2
            and item.props[2] == b"Mesh"
            and _uid(item.props[0]) is not None
        }
        links: list[FbxModelLink] = []
        for item in connections.elems:
            if item.id != b"C" or len(item.props) < 3 or item.props[0] != b"OO":
                continue
            source = _uid(item.props[1])
            destination = _uid(item.props[2])
            if source in geometries and destination in models:
                links.append(FbxModelLink(destination, source))
        return cls(links, model_uids)


@dataclass(frozen=True)
class FbxImportReceipt:
    source_asset_guid: str
    source_asset_sha256: str
    fbx_model_uid: int
    fbx_geometry_uid: int
    blender_object_receipt_id: str
    blender_mesh_receipt_id: str
    evidence: str = "OFFICIAL_IMPORTER_MODEL_HOOK"


@dataclass(frozen=True)
class FbxBoneReceipt:
    source_asset_guid: str
    source_asset_sha256: str
    fbx_model_uid: int
    blender_bone_receipt_id: str
    evidence: str = "OFFICIAL_IMPORTER_BUILD_SKELETON_RETURN"


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_receipt(model_uid: int, geometry_uid: int, source_asset_guid: str, sha256: str) -> FbxImportReceipt:
    prefix = f"{sha256}:{model_uid}:{geometry_uid}"
    return FbxImportReceipt(
        source_asset_guid=source_asset_guid.lower(),
        source_asset_sha256=sha256,
        fbx_model_uid=model_uid,
        fbx_geometry_uid=geometry_uid,
        blender_object_receipt_id=f"vapb-fbx-object:{hashlib.sha256(prefix.encode()).hexdigest()}",
        blender_mesh_receipt_id=f"vapb-fbx-mesh:{hashlib.sha256(f'{sha256}:{geometry_uid}'.encode()).hexdigest()}",
    )


def persist_receipt(obj: Any, receipt: FbxImportReceipt) -> None:
    """Persist only semantic, hash-bound values; never a runtime pointer."""
    values = {
        "_vapb_fbx_receipt_version": RECEIPT_VERSION,
        "_vapb_fbx_source_asset_guid": receipt.source_asset_guid,
        "_vapb_fbx_source_asset_sha256": receipt.source_asset_sha256,
        "_vapb_fbx_model_uid": str(receipt.fbx_model_uid),
        "_vapb_fbx_geometry_uid": str(receipt.fbx_geometry_uid),
        "_vapb_fbx_object_receipt_id": receipt.blender_object_receipt_id,
        "_vapb_fbx_mesh_receipt_id": receipt.blender_mesh_receipt_id,
        "_vapb_fbx_receipt_evidence": receipt.evidence,
        "_vapb_fbx_realization_id": str(uuid.uuid4()),
    }
    for key, value in values.items():
        obj[key] = value
    data = getattr(obj, "data", None)
    object_session_uid = getattr(obj, "session_uid", None)
    if object_session_uid is not None:
        obj["_vapb_fbx_object_session_uid"] = str(object_session_uid)
    if data is not None:
        data["_vapb_fbx_receipt_version"] = RECEIPT_VERSION
        data["_vapb_fbx_source_asset_sha256"] = receipt.source_asset_sha256
        data["_vapb_fbx_geometry_uid"] = str(receipt.fbx_geometry_uid)
        data["_vapb_fbx_mesh_receipt_id"] = receipt.blender_mesh_receipt_id
        mesh_session_uid = getattr(data, "session_uid", None)
        if mesh_session_uid is not None:
            data["_vapb_fbx_mesh_session_uid"] = str(mesh_session_uid)


def validate_receipt_continuity(obj: Any) -> bool:
    """Check same-session continuity, not persistent identity after reopening."""
    stored_object = obj.get("_vapb_fbx_object_session_uid")
    data = getattr(obj, "data", None)
    stored_mesh = data.get("_vapb_fbx_mesh_session_uid") if data is not None else None
    current_object = getattr(obj, "session_uid", None)
    current_mesh = getattr(data, "session_uid", None) if data is not None else None
    return (
        stored_object is not None
        and stored_mesh is not None
        and current_object is not None
        and current_mesh is not None
        and str(current_object) == str(stored_object)
        and str(current_mesh) == str(stored_mesh)
    )


def make_bone_receipt(model_uid: int, source_asset_guid: str, sha256: str) -> FbxBoneReceipt:
    source_asset_guid = source_asset_guid.lower()
    return FbxBoneReceipt(
        source_asset_guid=source_asset_guid,
        source_asset_sha256=sha256,
        fbx_model_uid=model_uid,
        blender_bone_receipt_id=f"vapb-fbx-bone:{hashlib.sha256(f'{source_asset_guid}:{sha256}:{model_uid}'.encode()).hexdigest()}",
    )


def persist_bone_receipt(bone: Any, receipt: FbxBoneReceipt) -> None:
    """Tag the EditBone returned by Blender's creator while it is still valid."""
    values = {
        "_vapb_fbx_receipt_version": RECEIPT_VERSION,
        "_vapb_fbx_source_asset_guid": receipt.source_asset_guid,
        "_vapb_fbx_source_asset_sha256": receipt.source_asset_sha256,
        "_vapb_fbx_model_uid": str(receipt.fbx_model_uid),
        "_vapb_fbx_bone_receipt_id": receipt.blender_bone_receipt_id,
        "_vapb_fbx_bone_realization_id": str(uuid.uuid4()),
        "_vapb_fbx_receipt_evidence": receipt.evidence,
    }
    for key, value in values.items():
        bone[key] = value


def copy_with_receipt(source: Any) -> Any:
    """Observe a native Object copy and retain its proven FBX lineage.

    The source receipt identifies a source primitive, while realization IDs
    distinguish objects. Shared Mesh metadata is never rewritten. Unity
    Renderer/occurrence bindings cannot be inherited from a different object.
    An unobserved copy or reopened object needs other evidence; this function
    must not upgrade its copied metadata to a verified import receipt.
    """
    proven = validate_receipt_continuity(source) and bool(
        source.get("_vapb_fbx_realization_id")
    )
    member = source.copy()
    for key in list(member.keys()):
        if key.startswith("_vapb_fbx_") or key == "_vapb_renderer_bindings":
            del member[key]
    if proven and member.data is source.data:
        for key in source.keys():
            if key.startswith("_vapb_fbx_"):
                member[key] = source[key]
        member["_vapb_fbx_source_realization_id"] = source["_vapb_fbx_realization_id"]
        member["_vapb_fbx_realization_id"] = str(uuid.uuid4())
        member["_vapb_fbx_object_session_uid"] = str(member.session_uid)
        member["_vapb_fbx_receipt_evidence"] = "OBSERVED_OBJECT_COPY"
    return member


def import_with_receipts(
    path: Path,
    import_call: Callable[[], None],
    source_asset_guid: str,
    bpy_module: Any,
) -> list[FbxImportReceipt]:
    """Run one official import with a temporary, signature-gated hook."""
    try:
        from io_scene_fbx import import_fbx as native_importer  # type: ignore

        helper_type = native_importer.FbxImportHelperNode
        original = helper_type.build_node_obj
        signature = inspect.signature(original)
        if tuple(signature.parameters)[:3] != ("self", "fbx_tmpl", "settings"):
            import_call()
            return []
        semantic = RawFbxSemanticIndex.from_file(path)
    except (ImportError, AttributeError, OSError, TypeError, ValueError):
        import_call()
        return []

    try:
        original_bone = helper_type.build_skeleton
        original_pose = helper_type.set_pose_matrix_and_custom_props
        bone_supported = (
            tuple(inspect.signature(original_bone).parameters) ==
            ("self", "arm", "parent_matrix", "settings", "parent_bone_size")
            and tuple(inspect.signature(original_pose).parameters) == ("self", "arm", "settings")
        )
    except (AttributeError, TypeError, ValueError):
        bone_supported = False

    sha256 = source_sha256(path)
    captures: list[tuple[int, Any]] = []
    bone_captures: dict[int, dict[str, str]] = {}
    shape_captures = {}
    original_shapes = getattr(native_importer, 'blen_read_shapes', None)
    shape_supported = (callable(original_shapes) and tuple(inspect.signature(original_shapes).parameters)
                       == ('fbx_tmpl', 'fbx_data', 'objects', 'me', 'scene'))

    def shape_hook(fbx_tmpl, fbx_data, objects, me, scene):
        result = original_shapes(fbx_tmpl, fbx_data, objects, me, scene)
        if result:
            rows = []
            for uid, keys in result.items():
                source = [row for row in fbx_data if row[0] == uid]
                if len(keys) != 1 or len(source) != 1 or len(source[0][3]) != 1:
                    continue  # Progressive shapes require independent support.
                rows.append((uid, source[0][1].props[0], keys[0]))
            shape_captures[id(me)] = rows
        return result

    def hook(self: Any, fbx_tmpl: Any, settings: Any) -> Any:
        result = original(self, fbx_tmpl, settings)
        model_uid = _uid(getattr(self, "fbx_elem", None).props[0]) if getattr(self, "fbx_elem", None) else None
        if result is not None and model_uid is not None:
            captures.append((model_uid, result))
        return result

    def bone_hook(self: Any, arm: Any, parent_matrix: Any, settings: Any, parent_bone_size: float = 1) -> Any:
        bone = original_bone(self, arm, parent_matrix, settings, parent_bone_size)
        elem = getattr(self, "fbx_elem", None)
        model_uid = _uid(elem.props[0]) if elem is not None and elem.props else None
        if bone is not None and model_uid is not None and semantic.unique_source_model(model_uid):
            persist_bone_receipt(bone, make_bone_receipt(model_uid, source_asset_guid, sha256))
            bone_captures[id(self)] = {key: bone[key] for key in bone.keys() if key.startswith("_vapb_fbx_")}
        return bone

    def pose_hook(self: Any, arm: Any, settings: Any) -> Any:
        result = original_pose(self, arm, settings)
        values = bone_captures.get(id(self))
        if values is not None:
            # The official importer assigned bl_bone from the newly created
            # EditBone.name and uses this same key to resolve its PoseBone.
            pose_bone = self.bl_obj.pose.bones[self.bl_bone]
            if all(pose_bone.bone.get(key) == value for key, value in values.items()):
                for key, value in values.items():
                    pose_bone[key] = value
        return result

    try:
        helper_type.build_node_obj = hook
        if shape_supported:
            native_importer.blen_read_shapes = shape_hook
        if bone_supported:
            helper_type.build_skeleton = bone_hook
            helper_type.set_pose_matrix_and_custom_props = pose_hook
        import_call()
    finally:
        helper_type.build_node_obj = original
        if shape_supported:
            native_importer.blen_read_shapes = original_shapes
        if bone_supported:
            helper_type.build_skeleton = original_bone
            helper_type.set_pose_matrix_and_custom_props = original_pose

    receipts: list[FbxImportReceipt] = []
    for model_uid, obj in captures:
        geometry_uid = semantic.geometry_for_model(model_uid)
        if geometry_uid is None:
            continue
        receipt = make_receipt(model_uid, geometry_uid, source_asset_guid, sha256)
        persist_receipt(obj, receipt)
        if getattr(obj, 'type', None) == 'MESH' and id(obj.data) in shape_captures:
            persist_shape_receipts(obj.data, sha256, geometry_uid, shape_captures[id(obj.data)])
        receipts.append(receipt)
    return receipts
