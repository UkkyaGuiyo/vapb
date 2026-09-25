"""Source-side FBX identity and Blender realization receipts.

The receipt deliberately stops at the boundary that the source FBX and the
official Blender importer can prove: FBX Model UID -> Geometry UID -> the
Object created during this import.  Unity local file IDs are not inferred.
"""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


RECEIPT_VERSION = "vapb_fbx_realization_receipt_v1"


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

    def __init__(self, links: list[FbxModelLink]):
        self.links = tuple(links)
        by_model: dict[int, list[int]] = {}
        for link in links:
            by_model.setdefault(link.model_uid, []).append(link.geometry_uid)
        self._by_model = {key: tuple(value) for key, value in by_model.items()}

    def geometry_for_model(self, model_uid: int) -> int | None:
        values = self._by_model.get(int(model_uid), ())
        return values[0] if len(values) == 1 else None

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
        models = {
            _uid(item.props[0])
            for item in objects.elems
            if item.id == b"Model" and item.props and _uid(item.props[0]) is not None
        }
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
        return cls(links)


@dataclass(frozen=True)
class FbxImportReceipt:
    source_asset_guid: str
    source_asset_sha256: str
    fbx_model_uid: int
    fbx_geometry_uid: int
    blender_object_receipt_id: str
    blender_mesh_receipt_id: str
    evidence: str = "OFFICIAL_IMPORTER_MODEL_HOOK"


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
    """Reject copied metadata when the current Blender IDs differ."""
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

    sha256 = source_sha256(path)
    captures: list[tuple[int, Any]] = []

    def hook(self: Any, fbx_tmpl: Any, settings: Any) -> Any:
        result = original(self, fbx_tmpl, settings)
        model_uid = _uid(getattr(self, "fbx_elem", None).props[0]) if getattr(self, "fbx_elem", None) else None
        if result is not None and model_uid is not None:
            captures.append((model_uid, result))
        return result

    helper_type.build_node_obj = hook
    try:
        import_call()
    finally:
        helper_type.build_node_obj = original

    receipts: list[FbxImportReceipt] = []
    for model_uid, obj in captures:
        geometry_uid = semantic.geometry_for_model(model_uid)
        if geometry_uid is None:
            continue
        receipt = make_receipt(model_uid, geometry_uid, source_asset_guid, sha256)
        persist_receipt(obj, receipt)
        receipts.append(receipt)
    return receipts
