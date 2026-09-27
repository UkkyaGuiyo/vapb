"""Bounded Unity Mesh subasset frame for a directly referenced FBX Mesh.

This is deliberately narrower than general FBX node realization. Unity's
MeshFilter references the Mesh resource, not the source FBX Model Object.
The public 2022.3.22f1 oracle verifies this axis/unit convention and the
asymmetric coordinate fixture distinguishes it from the native Object frame.
"""

from __future__ import annotations

import math
from pathlib import Path
import re

from mathutils import Matrix  # type: ignore

from ..unity.prefab_parser import PrefabData, ref_file_id, ref_guid
from .fbx_receipt import source_sha256


def root_direct_mesh_file_id(prefab: PrefabData, mesh_guid: str) -> int | None:
    roots = prefab.root_game_objects()
    if len(roots) != 1:
        return None
    owner = roots[0].file_id
    filters = [doc for doc in prefab.mesh_filter_documents()
               if ref_file_id(doc.data.get("m_GameObject")) == owner]
    renderers = [doc for doc in prefab.renderer_documents()
                 if doc.class_id == 23 and ref_file_id(doc.data.get("m_GameObject")) == owner]
    if len(filters) != 1 or len(renderers) != 1:
        return None
    mesh = filters[0].data.get("m_Mesh")
    file_id = ref_file_id(mesh)
    return file_id if (ref_guid(mesh) or "").lower() == mesh_guid.lower() and file_id else None


def _verified_importer_settings(meta_path: Path) -> bool:
    try:
        text = meta_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if len(re.findall(r"(?m)^ModelImporter:\s*$", text)) != 1:
        return False
    block = re.search(r"(?ms)^  meshes:\s*\n(.*?)(?=^  [A-Za-z_][^:\n]*:|\Z)", text)
    if block is None:
        return False
    values = {}
    for key in ("globalScale", "useFileScale", "useFileUnits", "bakeAxisConversion"):
        matches = re.findall(rf"(?m)^    {key}:\s*([^\s#]+)\s*$", block.group(1))
        if len(matches) != 1:
            return False
        values[key] = matches[0]
    try:
        scale = float(values["globalScale"])
    except ValueError:
        return False
    return (math.isfinite(scale) and math.isclose(scale, 1.0, rel_tol=0.0, abs_tol=1e-9)
            and values["useFileScale"] == "1" and values["useFileUnits"] == "1"
            and values["bakeAxisConversion"] == "0")


def _verified_fbx_axes(path: Path) -> bool:
    from io_scene_fbx import parse_fbx  # type: ignore

    try:
        root, _ = parse_fbx.parse(str(path), use_namedtuple=True)
        settings = [node for node in root.elems if node.id == b"GlobalSettings"]
        if len(settings) != 1:
            return False
        containers = [node for node in settings[0].elems if node.id == b"Properties70"]
        if len(containers) != 1:
            return False
        expected = {b"UpAxis": 1, b"UpAxisSign": 1, b"FrontAxis": 2,
                    b"FrontAxisSign": 1, b"CoordAxis": 0, b"CoordAxisSign": 1,
                    b"UnitScaleFactor": 1.0}
        for name, value in expected.items():
            matches = [node.props[-1] for node in containers[0].elems
                       if node.id == b"P" and node.props and node.props[0] == name]
            if len(matches) != 1 or type(matches[0]) not in (int, float) or matches[0] != value:
                return False
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def verified_direct_mesh_frame(path: Path, native_object) -> Matrix | None:
    """Map this proven FBX/ModelImporter convention into Blender semantic space."""
    try:
        source_hash = source_sha256(path)
    except OSError:
        return None
    if (native_object.type != "MESH" or native_object.parent is not None
            or len(native_object.modifiers) != 0
            or native_object.get("_vapb_fbx_source_asset_sha256") != source_hash
            or not _verified_importer_settings(Path(str(path) + ".meta"))
            or not _verified_fbx_axes(path)):
        return None
    native_linear = native_object.matrix_world.to_3x3()
    if max(abs(native_linear[i][j] - (1.0 if i == j else 0.0))
           for i in range(3) for j in range(3)) > 1e-5:
        return None
    # FBX UnitScaleFactor=1 is centimetres; verified Unity fileScale=0.01.
    # The asymmetric public fixture proves (x, -z, y) for raw Blender Mesh
    # coordinates in this exact axis convention. The FBX Model translation is
    # excluded: MeshFilter references the Mesh subasset directly.
    return Matrix(((0.01, 0.0, 0.0, 0.0),
                   (0.0, 0.0, -0.01, 0.0),
                   (0.0, 0.01, 0.0, 0.0),
                   (0.0, 0.0, 0.0, 1.0)))
