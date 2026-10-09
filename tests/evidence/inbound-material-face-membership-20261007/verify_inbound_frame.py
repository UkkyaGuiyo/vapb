#!/usr/bin/env python3
"""Offline, fail-closed derivation of the pinned FBX/Unity/Blender frame.

Evidence tooling only. Reads pinned files, never starts Blender or Unity, never fits a
transform, and does not produce a material mapping. Requires Blender 5.2's io_scene_fbx
source tree for the exact importer axis/unit and transform conventions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
import tarfile
import errno
import tempfile
import types
from contextlib import contextmanager

PIN_CAPTURE = "c0949a10fa0b4ab789d21d62ee4381742240d116f7de5067048fbd7a19f686a7"
PIN_COMPARISON = "7d23b9ab0d06ff8a8ff307e9489d2d422ca4b37bfeb938aac7170e61429d7918"
PIN_UNITY = "af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2"
PIN_PACKAGE = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
PIN_FBX = "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5"
PIN_META = "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d"
PIN_BLENDER_SOURCE = {
    "import_fbx.py": "262127c8e6af3e748d696d81070366f39e449aa73e6bc1d9463092b5cbf86741",
    "fbx_utils.py": "66a15d79d5eaf490176b439f22fb01963efcd46e06702eff224a84135e636fb3",
    "parse_fbx.py": "96fe3f11b5c9b2950d9c434857e3b0db1a1b558510e2ad360b767643a69c2047",
}
TOL = 2.0e-5


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@contextmanager
def owned_temp_bytes(directory: Path, payload: bytes):
    """Create a unique temp file exclusively; clean up only while its inode is ours."""
    fd, raw_path = tempfile.mkstemp(prefix="vapb-frame-", suffix=".input.fbx", dir=directory)
    path = Path(raw_path)
    identity = None
    try:
        identity = os.fstat(fd)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(payload)
            stream.flush()
        yield path
    finally:
        if fd >= 0:
            os.close(fd)
        if identity is not None:
            try:
                current = path.lstat()
            except FileNotFoundError:
                pass
            else:
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    path.unlink()


def temp_file_controls():
    """Exercise collision, concurrent use, and exception cleanup without touching inputs."""
    import concurrent.futures
    import threading
    import tempfile as tempfile_module

    with tempfile_module.TemporaryDirectory(prefix="vapb-temp-controls-") as raw_dir:
        directory = Path(raw_dir)
        preexisting = directory / "result.json.input.fbx"
        preexisting.write_bytes(b"keep")
        try:
            with owned_temp_bytes(directory, b"new") as created:
                if created == preexisting or created.read_bytes() != b"new":
                    raise AssertionError("TEMP_PREEXISTING_COLLISION_CONTROL_FAILED")
        finally:
            if preexisting.read_bytes() != b"keep":
                raise AssertionError("TEMP_PREEXISTING_CONTENT_CHANGED")

        dangling_link = directory / "result.json.dangling.input.fbx"
        try:
            os.symlink("missing-target.fbx", dangling_link)
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.EACCES) and getattr(exc, "winerror", None) != 1314:
                raise
            dangling_symlink_preserved = "SKIPPED_PERMISSION_DENIED"
        else:
            with owned_temp_bytes(directory, b"new") as created:
                if created == dangling_link or created.read_bytes() != b"new":
                    raise AssertionError("TEMP_DANGLING_SYMLINK_COLLISION_CONTROL_FAILED")
            if not dangling_link.is_symlink() or dangling_link.readlink() != Path("missing-target.fbx"):
                raise AssertionError("TEMP_DANGLING_SYMLINK_CHANGED")
            dangling_symlink_preserved = True

        def one(payload):
            with owned_temp_bytes(directory, payload) as path:
                rendezvous.wait(timeout=5)
                return path.name, path.read_bytes()

        rendezvous = threading.Barrier(2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            concurrent = list(pool.map(one, (b"left", b"right")))
        if len({name for name, _ in concurrent}) != 2 or {body for _, body in concurrent} != {b"left", b"right"}:
            raise AssertionError("TEMP_CONCURRENT_UNIQUENESS_CONTROL_FAILED")

        failed_path = None
        try:
            with owned_temp_bytes(directory, b"cleanup") as path:
                failed_path = path
                raise RuntimeError("synthetic parse failure")
        except RuntimeError as exc:
            if str(exc) != "synthetic parse failure":
                raise
        if failed_path is None or failed_path.exists():
            raise AssertionError("TEMP_FAILURE_CLEANUP_CONTROL_FAILED")

        replacement_path = None
        with owned_temp_bytes(directory, b"owned") as owned_path:
            moved_path = owned_path.with_name(owned_path.name + ".moved")
            owned_path.rename(moved_path)
            replacement_path = owned_path
            replacement_path.write_bytes(b"replacement")
        if replacement_path.read_bytes() != b"replacement":
            raise AssertionError("TEMP_FOREIGN_REPLACEMENT_REMOVED")

        source_dir = directory / "synthetic-source"
        source_dir.mkdir()
        (source_dir / "parse_fbx.py").write_bytes(b"synthetic revision")
        try:
            validate_blender_sources(source_dir, {"parse_fbx.py": "0" * 64})
        except ValueError as exc:
            wrong_revision_rejected = str(exc) == "BLENDER_SOURCE_HASH_MISMATCH:parse_fbx.py"
        else:
            wrong_revision_rejected = False
        if not wrong_revision_rejected:
            raise AssertionError("BLENDER_WRONG_REVISION_CONTROL_FAILED")
    return {"preexisting_path_preserved": True,
            "dangling_symlink_preserved": dangling_symlink_preserved,
            "concurrent_same_output_calls_use_distinct_temp_paths": True,
            "failure_cleanup_removes_owned_temp": True,
            "replaced_path_is_not_removed_during_cleanup": True,
            "wrong_blender_revision_rejected_before_import": wrong_revision_rejected}


def jsonable(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, (list, tuple)):
        return [jsonable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return value


def mm(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def ident():
    return [[float(r == c) for c in range(4)] for r in range(4)]


def trans(v):
    m = ident()
    m[0][3], m[1][3], m[2][3] = map(float, v)
    return m


def scale(v):
    m = ident()
    for i in range(3):
        m[i][i] = float(v[i])
    return m


def rot_xyz(deg, order="XYZ"):
    by_axis = {}
    for axis, value in zip("XYZ", deg):
        a = math.radians(float(value))
        c, s = math.cos(a), math.sin(a)
        m = ident()
        i, j = {"X": (1, 2), "Y": (2, 0), "Z": (0, 1)}[axis]
        m[i][i] = c; m[i][j] = -s
        m[j][i] = s; m[j][j] = c
        by_axis[axis] = m
    out = ident()
    for axis in reversed(order):
        out = mm(out, by_axis[axis])
    return out


def point(m, p):
    v = [float(p[0]), float(p[1]), float(p[2]), 1.0]
    q = [sum(m[r][c] * v[c] for c in range(4)) for r in range(4)]
    return tuple(q[:3])


def det3(m):
    a = m
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def max_residual(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4))


def quant(p):
    return tuple(round(float(x), 6) for x in p)


def tri_counter(tris, matrix, reverse=False):
    out = Counter()
    for tri in tris:
        pts = [quant(point(matrix, p)) for p in tri]
        if reverse:
            pts = [pts[0], pts[2], pts[1]]
        out[tuple(pts)] += 1
    return out


def node_children(node, key):
    return [n for n in node.elems if n.id == key]


def props70(node):
    containers = node_children(node, b"Properties70")
    if len(containers) > 1:
        raise ValueError("AMBIGUOUS_PROPERTIES70")
    result = {}
    if containers:
        for row in containers[0].elems:
            if row.id != b"P" or not row.props:
                continue
            key = row.props[0].decode("utf-8", "replace") if isinstance(row.props[0], bytes) else str(row.props[0])
            if key in result:
                raise ValueError("DUPLICATE_FBX_PROPERTY:" + key)
            result[key] = list(row.props[4:])
    return result


def val(props, key, default):
    raw = props.get(key)
    return list(default) if raw is None else [x.decode("utf-8", "replace") if isinstance(x, bytes) else x for x in raw]


def vec(props, key, default):
    row = val(props, key, default)
    return [float(x) for x in row[:3]]


def scalar(props, key, default):
    row = val(props, key, [default])
    return float(row[0])


def integer(props, key, default):
    row = val(props, key, [default])
    return int(row[0])


def fbx_node_matrix(node):
    p = props70(node)
    loc = vec(p, "Lcl Translation", (0, 0, 0))
    rot = vec(p, "Lcl Rotation", (0, 0, 0))
    sca = vec(p, "Lcl Scaling", (1, 1, 1))
    geom_loc = vec(p, "GeometricTranslation", (0, 0, 0))
    geom_rot = vec(p, "GeometricRotation", (0, 0, 0))
    geom_sca = vec(p, "GeometricScaling", (1, 1, 1))
    rot_active = bool(integer(p, "RotationActive", 0))
    # Blender's importer forces XYZ when RotationActive is false.
    rot_order = ({0: "XYZ", 1: "XZY", 2: "YZX", 3: "YXZ", 4: "ZXY", 5: "ZYX", 6: "XYZ"}
                 .get(integer(p, "RotationOrder", 0)) if rot_active else "XYZ")
    if rot_order is None:
        raise ValueError("UNSUPPORTED_ROTATION_ORDER")
    pre = vec(p, "PreRotation", (0, 0, 0)) if rot_active else (0, 0, 0)
    post = vec(p, "PostRotation", (0, 0, 0)) if rot_active else (0, 0, 0)
    roff = vec(p, "RotationOffset", (0, 0, 0))
    rpiv = vec(p, "RotationPivot", (0, 0, 0))
    soff = vec(p, "ScalingOffset", (0, 0, 0))
    spiv = vec(p, "ScalingPivot", (0, 0, 0))
    # FBX SDK/Maya transform order as implemented by Blender 5.2 import_fbx.py.
    # PostRotation is inverse in FBX. Invert the orthogonal matrix by transpose.
    post_inv = rot_xyz(post)
    post_inv = [list(row) for row in zip(*post_inv)]
    base = mm(mm(mm(mm(mm(mm(trans(loc), trans(roff)), trans(rpiv)), rot_xyz(pre)),
                        rot_xyz(rot, rot_order)), post_inv), trans([-x for x in rpiv]))
    base = mm(mm(mm(base, trans(soff)), trans(spiv)), scale(sca))
    base = mm(base, trans([-x for x in spiv]))
    geom = mm(mm(trans(geom_loc), rot_xyz(geom_rot)), scale(geom_sca))
    return base, geom, p


def load_parser(addon_dir):
    addon_dir = addon_dir.resolve()
    validate_blender_sources(addon_dir)
    package_name = "_vapb_offline_io_scene_fbx"
    pkg = types.ModuleType(package_name)
    pkg.__path__ = [str(addon_dir)]
    sys.modules[package_name] = pkg
    return importlib.import_module(package_name + ".parse_fbx")


def validate_blender_sources(addon_dir, expected=PIN_BLENDER_SOURCE):
    """Verify all importer/parser source files before executing parser code."""
    for name, pinned in expected.items():
        path = addon_dir / name
        if not path.is_file():
            raise ValueError("BLENDER_PINNED_SOURCE_MISSING:" + name)
        if sha256(path) != pinned:
            raise ValueError("BLENDER_SOURCE_HASH_MISMATCH:" + name)
    return True


def unitypackage_asset(package, unity_path):
    with tarfile.open(package, "r:gz") as tf:
        matches = []
        for member in tf.getmembers():
            if not member.name.endswith("/pathname"):
                continue
            stream = tf.extractfile(member)
            if stream and stream.read().decode("utf-8", "replace").strip() == unity_path:
                prefix = member.name.rsplit("/", 1)[0]
                asset = tf.extractfile(prefix + "/asset")
                meta = tf.extractfile(prefix + "/asset.meta")
                if asset is None or meta is None:
                    raise ValueError("UNITYPACKAGE_ASSET_META_MISSING")
                matches.append((asset.read(), meta.read()))
        if len(matches) != 1:
            raise ValueError("UNITYPACKAGE_ASSET_PATH_NOT_UNIQUE")
        return matches[0]


def frame_from_fbx(parse_fbx, fbx_path):
    root, version = parse_fbx.parse(str(fbx_path), use_namedtuple=True)
    blocks = {n.id: n for n in root.elems}
    settings = blocks.get(b"GlobalSettings")
    objects, conns = blocks.get(b"Objects"), blocks.get(b"Connections")
    if not settings or not objects or not conns:
        raise ValueError("FBX_REQUIRED_BLOCK_MISSING")
    by_uid = {}
    for n in objects.elems:
        if not n.props or not isinstance(n.props[0], int) or n.props[0] in by_uid:
            raise ValueError("FBX_OBJECT_UID_MISSING_OR_DUPLICATE")
        by_uid[n.props[0]] = n
    connections = []
    for n in conns.elems:
        if n.id == b"C" and len(n.props) >= 3 and n.props[0] == b"OO":
            connections.append((int(n.props[1]), int(n.props[2])))
    model_uid, geom_uid = 208084244, 329684292
    model, geom = by_uid.get(model_uid), by_uid.get(geom_uid)
    if model is None or model.id != b"Model" or geom is None or geom.id != b"Geometry":
        raise ValueError("PINNED_FB X_MODEL_GEOMETRY_MISSING".replace(" ", ""))
    if connections.count((geom_uid, model_uid)) != 1:
        raise ValueError("GEOMETRY_MODEL_EDGE_NOT_UNIQUE")

    chain = []
    current = model_uid
    seen = set()
    while current != 0:
        if current in seen or current not in by_uid:
            raise ValueError("FBX_PARENT_CHAIN_CYCLE_OR_MISSING")
        seen.add(current)
        n = by_uid[current]
        if n.id not in (b"Model", b"NodeAttribute"):
            raise ValueError("UNSUPPORTED_FBX_PARENT_NODE")
        parents = [dst for src, dst in connections if src == current and dst != 0 and by_uid.get(dst, None) is not None and by_uid[dst].id in (b"Model", b"NodeAttribute")]
        parents += [dst for src, dst in connections if src == current and dst == 0]
        if len(parents) > 1:
            raise ValueError("AMBIGUOUS_FBX_PARENT_EDGE")
        chain.append(n)
        current = parents[0] if parents else 0
    chain.reverse()
    world = ident()
    chain_rows = []
    final_geom = ident()
    for index, n in enumerate(chain):
        base, geom_mat, props = fbx_node_matrix(n)
        world = mm(world, base)
        if index == len(chain) - 1:
            final_geom = geom_mat
        chain_rows.append({"uid": int(n.props[0]), "kind": n.id.decode(), "local_base": base,
                           "geometric": geom_mat, "has_nondefault_geometric": geom_mat != ident(),
                           "geometric_inherited": False})
    world = mm(world, final_geom)

    gp = props70(settings)
    up = (integer(gp, "UpAxis", 2), integer(gp, "UpAxisSign", 1))
    front = (integer(gp, "FrontAxis", 1), integer(gp, "FrontAxisSign", 1))
    coord = (integer(gp, "CoordAxis", 0), integer(gp, "CoordAxisSign", 1))
    # Invert the exact Blender RIGHT_HAND_AXES table tuple (Up, Front, Coord).
    lut = {
        ((1, 1), (2, 1), (0, 1)): ("Y", "-Z"),
        ((1, 1), (2, -1), (0, -1)): ("Y", "Z"),
        ((2, 1), (1, -1), (0, 1)): ("Z", "Y"),
    }
    axis_key = lut.get((up, front, coord))
    if axis_key is None:
        raise ValueError("FBX_AXIS_LUT_UNSUPPORTED_OR_INCONSISTENT")
    # Blender 5.2 import_fbx: reverse RIGHT_HAND_AXES LUT, then axis_conversion.
    # For this pinned axis tuple, axis_conversion(from_forward='-Z', from_up='Y') is Rx(+90).
    if axis_key != ("Y", "-Z"):
        raise ValueError("ONLY_PINNED_BLENDER_AXIS_CONVERSION_SUPPORTED")
    scene_unit_factor = 100.0  # Blender importer default scene unit system NONE.
    unit = scalar(gp, "UnitScaleFactor", 1.0) / scene_unit_factor
    rx90 = rot_xyz((90, 0, 0))
    g = mm(scale((unit, unit, unit)), rx90)

    vertices_node = next((n for n in geom.elems if n.id == b"Vertices"), None)
    indices_node = next((n for n in geom.elems if n.id == b"PolygonVertexIndex"), None)
    if vertices_node is None or indices_node is None:
        raise ValueError("FBX_GEOMETRY_VERTEX_ARRAY_MISSING")
    flat_v = vertices_node.props[0]
    vertices = [tuple(float(flat_v[i + k]) for k in range(3)) for i in range(0, len(flat_v), 3)]
    raw_idx = list(indices_node.props[0])
    polys, current_poly = [], []
    for encoded in raw_idx:
        end = int(encoded) < 0
        index = -int(encoded) - 1 if end else int(encoded)
        if index < 0 or index >= len(vertices):
            raise ValueError("FBX_POLYGON_INDEX_OUT_OF_RANGE")
        current_poly.append(index)
        if end:
            polys.append(current_poly); current_poly = []
    if current_poly or not polys or any(len(p) != 3 for p in polys):
        raise ValueError("NON_TRIANGLE_OR_INCOMPLETE_FB X_POLYGON".replace(" ", ""))
    triangles = [tuple(vertices[i] for i in poly) for poly in polys]
    return {"version": version, "global_props": gp, "g": g, "chain": chain_rows,
            "l": world, "vertices": vertices, "triangles": triangles,
            "polygon_indices": polys, "model_uid": model_uid, "geometry_uid": geom_uid}


def matrix_from_unity(diag):
    m = diag.get("source_mesh_to_prefab_root")
    if not isinstance(m, dict):
        raise ValueError("UNITY_SOURCE_MESH_TO_ROOT_MISSING")
    out = ident()
    for r in range(3):
        for c in range(4):
            out[r][c] = float(m[f"e{r}{c}"])
    return out


def unity_triangles(diag):
    verts = diag.get("source_mesh_vertices")
    subs = diag.get("source_submeshes")
    if not isinstance(verts, list) or not isinstance(subs, list) or not verts or not subs:
        raise ValueError("UNITY_SOURCE_GEOMETRY_MISSING")
    vv = [(float(v["x"]), float(v["y"]), float(v["z"])) for v in verts]
    out = []
    for sm in subs:
        idx = sm.get("indices")
        if not isinstance(idx, list) or not idx or len(idx) % 3:
            raise ValueError("UNITY_SUBMESH_INDICES_INVALID")
        for i in range(0, len(idx), 3):
            ids = idx[i:i+3]
            if any(type(k) is not int or k < 0 or k >= len(vv) for k in ids):
                raise ValueError("UNITY_INDEX_INVALID")
            out.append(tuple(vv[k] for k in ids))
    return out


def controls(fbx, matrix, basis):
    g, l = fbx["g"], fbx["l"]
    raw_tris = fbx["triangles"]
    base = mm(g, l)
    axis_mut = [row[:] for row in g]; axis_mut[1][2] *= -1
    unit_mut = mm(scale((10, 10, 10)), g)
    model_mut = mm(g, mm(rot_xyz((0.5, 0, 0)), l))
    c = scale((0.01, 0.01, 0.01)); c[0][0] *= -1
    reflected_candidate = scale((0.01, 0.01, 0.01)); reflected_candidate[0][0] *= -1
    no_reflection = scale((0.01, 0.01, 0.01))
    reflected_frame = mm(mm(basis, matrix), reflected_candidate)
    nonreflected_frame = mm(mm(basis, matrix), no_reflection)
    mutated = {
        "axis_change_rejected": max_residual(base, mm(axis_mut, l)) > TOL,
        "unit_change_rejected": max_residual(base, mm(unit_mut, l)) > TOL,
        "model_change_rejected": max_residual(base, model_mut) > TOL,
        "reflection_candidate_closes": max_residual(base, reflected_frame) < TOL,
        "reflection_change_rejected": max_residual(base, nonreflected_frame) > TOL,
        "index_reversal_is_separate": tri_counter(raw_tris, base) != tri_counter(
            [tuple((t[0], t[2], t[1]) for t in raw_tris)[i] for i in range(len(raw_tris))], base),
    }
    if not all(mutated.values()):
        raise AssertionError("FRAME_PERTURBATION_CONTROL_FAILED:" + repr(mutated))
    return mutated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", type=Path, required=True)
    ap.add_argument("--comparison", type=Path, required=True)
    ap.add_argument("--unity-json", type=Path, required=True)
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--blender-fbx-source", type=Path, required=True,
                    help="Blender 5.2 scripts/addons_core/io_scene_fbx directory")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    for path, pinned, label in ((args.capture, PIN_CAPTURE, "capture"),
                                (args.comparison, PIN_COMPARISON, "comparison"),
                                (args.unity_json, PIN_UNITY, "unity_json"),
                                (args.package, PIN_PACKAGE, "package")):
        if sha256(path) != pinned:
            raise ValueError("PINNED_INPUT_HASH_MISMATCH:" + label)
    if args.output.exists():
        raise FileExistsError("OUTPUT_ALREADY_EXISTS")
    fbx_bytes, meta_bytes = unitypackage_asset(args.package, "Assets/PublicMaterialSource/Input.fbx")
    if hashlib.sha256(fbx_bytes).hexdigest() != PIN_FBX or hashlib.sha256(meta_bytes).hexdigest() != PIN_META:
        raise ValueError("UNITYPACKAGE_SOURCE_FBX_OR_META_HASH_MISMATCH")
    meta = meta_bytes.decode("utf-8", "strict")
    if not re.search(r"(?m)^\s*bakeAxisConversion:\s*0\s*$", meta):
        raise ValueError("PINNED_META_BAKE_AXIS_SETTING_UNEXPECTED")
    if not re.search(r"(?m)^\s*useFileUnits:\s*1\s*$", meta) or not re.search(r"(?m)^\s*useFileScale:\s*1\s*$", meta):
        raise ValueError("PINNED_META_UNIT_SETTINGS_UNEXPECTED")
    # Parse via the standard file API using a unique, exclusively-owned temp file.
    with owned_temp_bytes(args.output.parent, fbx_bytes) as temp_fbx:
        parser = load_parser(args.blender_fbx_source)
        fbx = frame_from_fbx(parser, temp_fbx)

    capture = json.loads(args.capture.read_text(encoding="utf-8"))
    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    diag = json.loads(args.unity_json.read_text(encoding="utf-8"))
    if comparison.get("status") != "UNPROVEN_ORIENTATION_OR_FRAME" or comparison.get("mapping") is not None:
        raise ValueError("BASELINE_COMPARISON_NOT_FAIL_CLOSED")
    if diag.get("status") != "DIAGNOSTIC_ONLY":
        raise ValueError("UNITY_REPORT_NOT_DIAGNOSTIC_ONLY")
    m = matrix_from_unity(diag)
    b = [[-1.,0.,0.,0.],[0.,0.,-1.,0.],[0.,1.,0.,0.],[0.,0.,0.,1.]]
    c = scale((0.01, 0.01, 0.01)); c[0][0] *= -1
    gl = mm(fbx["g"], fbx["l"])
    bmc = mm(mm(b, m), c)
    native_mesh = capture["raw_input_fbx_native_import"][0]
    native = native_mesh["point_transform"]
    raw_corners = fbx["triangles"]
    transformed_native = tri_counter(raw_corners, gl)
    captured = [tuple(tuple(float(x) for x in p) for p in tri["corners"])
                for tri in native_mesh["triangles"]]
    captured_match = transformed_native == tri_counter(captured, ident())
    unity_tris = unity_triangles(diag)
    unity_to_blender = tri_counter(unity_tris, mm(b, m))
    predicted_raw = tri_counter(raw_corners, gl)
    direct = unity_to_blender == predicted_raw
    reverse = unity_to_blender == tri_counter(raw_corners, gl, reverse=True)
    # C is deliberately a candidate: bakeAxisConversion=0 says the importer keeps
    # conversion on hierarchy, but does not independently establish this factorization.
    unity_with_c = tri_counter(unity_tris, mm(b, m))
    c_test = tri_counter([tuple(point(c, p) for p in t) for t in raw_corners], mm(b, m)) == predicted_raw
    ctl = controls(fbx, m, b)
    raw_unoriented_signatures = [tuple(sorted(quant(p) for p in tri)) for tri in raw_corners]
    unique_signature_count = len(set(raw_unoriented_signatures))
    if unique_signature_count != len(raw_corners):
        raise ValueError("RAW_FBX_TRIANGLE_GEOMETRY_NOT_UNIQUE_UNORIENTED")
    unity_vertices = [(float(v["x"]), float(v["y"]), float(v["z"]))
                      for v in diag["source_mesh_vertices"]]
    candidate_vertices = [point(c, v) for v in fbx["vertices"]]
    candidate_c_mesh_vertices_match = set(map(quant, unity_vertices)) == set(map(quant, candidate_vertices))
    candidate_c_mesh_triangles_direct = tri_counter(unity_tris, ident()) == tri_counter(
        [tuple(point(c, p) for p in tri) for tri in raw_corners], ident())
    candidate_c_mesh_triangles_reverse = tri_counter(unity_tris, ident()) == tri_counter(
        [tuple(point(c, p) for p in (tri[0], tri[2], tri[1])) for tri in raw_corners], ident())
    result = {
        "status": "UNPROVEN_FRAME_CANDIDATE_ONLY",
        "mapping": None,
        "input_sha256": {"capture": PIN_CAPTURE, "comparison": PIN_COMPARISON,
                         "unity_json": PIN_UNITY, "package": PIN_PACKAGE,
                         "source_fbx": PIN_FBX, "source_fbx_meta": PIN_META},
        "blender_importer_source": {
            "version_claim": "Blender 5.2 pinned installed source; no Blender process launched",
            "import_fbx_sha256": sha256(args.blender_fbx_source / "import_fbx.py"),
            "fbx_utils_sha256": sha256(args.blender_fbx_source / "fbx_utils.py"),
            "parse_fbx_sha256": sha256(args.blender_fbx_source / "parse_fbx.py"),
            "unit_rule": "UnitScaleFactor / units_blender_to_fbx_factor(scene); NONE factor=100",
            "axis_rule": "reverse RIGHT_HAND_AXES then axis_conversion(from_forward=-Z, from_up=Y)",
            "transform_rule": "Parent @ T @ Roff @ Rp @ Rpre @ R @ inverse(Rpost) @ inverse(Rp) @ Soff @ Sp @ S @ inverse(Sp); geometric T @ R @ S",
        },
        "parser_load_safety": {
            "pinned_source_hashes_validated_before_import": True,
            "pinned_source_hashes": PIN_BLENDER_SOURCE,
            "sys_dont_write_bytecode": sys.dont_write_bytecode,
        },
        "unity_meta": {"bakeAxisConversion": 0, "useFileUnits": 1, "useFileScale": 1,
                       "C_independently_justified": False,
                       "reason": "metadata does not independently establish candidate mesh-local factor C=.01*reflectX"},
        "fbx": {"version": fbx["version"], "global_axis_unit_properties": jsonable(fbx["global_props"]),
                "model_geometry_uid": [fbx["model_uid"], fbx["geometry_uid"]],
                "parent_chain": fbx["chain"], "G": fbx["g"], "L_and_parent_chain": fbx["l"],
                "det_G": det3(fbx["g"]), "det_L": det3(fbx["l"]), "triangle_count": len(raw_corners)},
        "unity": {"M": m, "det_M": det3(m), "B": b, "det_B": det3(b),
                  "candidate_C": c, "det_C": det3(c)},
        "matrix_checks": {"GL_vs_captured_native_point_transform_max_abs": max_residual(gl, native),
                          "BMC_vs_GL_max_abs_candidate_only": max_residual(bmc, gl),
                          "all_captured_raw_triangles_match_GL": captured_match,
                          "unity_vs_GL_direct_full_triangle_counter": direct,
                          "unity_vs_GL_uniform_reverse_full_triangle_counter": reverse,
                          "candidate_C_algebraic_frame_closure_not_Unity_mesh_local_measurement": c_test,
                          "candidate_C_matches_Unity_mesh_local_vertex_position_set_allowing_splits": candidate_c_mesh_vertices_match,
                          "candidate_C_matches_Unity_mesh_local_triangle_counter_direct": candidate_c_mesh_triangles_direct,
                          "candidate_C_matches_Unity_mesh_local_triangle_counter_reverse": candidate_c_mesh_triangles_reverse,
                          "raw_unoriented_triangle_signature_count": unique_signature_count,
                          "raw_unoriented_triangle_signatures_unique": unique_signature_count == len(raw_corners),
                          "triangle_count_cardinality_matches": len(raw_corners) == len(unity_tris),
                          "full_corner_multiset_matches_under_observed_uniform_reverse": reverse},
        "controls": {**ctl, "temp_file_ownership": temp_file_controls()},
        "interpretation": "Even a numeric candidate match is not a proven Unity importer factorization or winding rule; keep mapping null until C and orientation parity have independent source authority.",
    }
    if not captured_match or max_residual(gl, native) > TOL or len(raw_corners) != len(unity_tris):
        result["status"] = "UNPROVEN_FRAME_CANDIDATE_MISMATCH"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output),
                      "mapping": None, "controls": ctl}, indent=2))
    return 0


def diagnose_pinned_uv_source_frame(fbx_path, snapshot_path, old_diagnostic_path, blender_fbx_source):
    """Read-only fixture diagnosis using UV identity before position/normal checks.

    No production mapping, fitted transform or Material-based correspondence.
    Ambiguous UV triangle/corner signatures refuse; the predeclared C is only
    certified for this pinned source observation, never used by the importer.
    """
    parser=load_parser(blender_fbx_source)
    fbx=Path(fbx_path);assert sha256(fbx)==PIN_FBX
    root,_=parser.parse(str(fbx),use_namedtuple=True)
    geo=next(n for block in root.elems if block.id==b'Objects' for n in block.elems if n.id==b'Geometry' and n.props[0]==329684292)
    get=lambda node,key:next(child.props[0] for child in node.elems if child.id==key)
    uv_layer=next(n for n in geo.elems if n.id==b'LayerElementUV')
    normal_layer=next(n for n in geo.elems if n.id==b'LayerElementNormal')
    for layer in (uv_layer,normal_layer):
     assert get(layer,b'MappingInformationType')==b'ByPolygonVertex' and get(layer,b'ReferenceInformationType')==b'IndexToDirect'
    uv_values=list(get(uv_layer,b'UV'));uv_indices=list(get(uv_layer,b'UVIndex'))
    normal_values=list(get(normal_layer,b'Normals'));normal_indices=list(get(normal_layer,b'NormalsIndex'))
    positions=list(get(geo,b'Vertices'));raw_indices=list(get(geo,b'PolygonVertexIndex'))
    assert len(raw_indices)==36 and all(value<0 for value in raw_indices[2::3])
    raw_points=[tuple(positions[3*i:3*i+3]) for i in range(len(positions)//3)]
    raw_corner_ids=[-v-1 if v<0 else v for v in raw_indices]
    raw_uv=[tuple(uv_values[2*i:2*i+2]) for i in uv_indices]
    raw_normals=[tuple(normal_values[3*i:3*i+3]) for i in normal_indices]
    snapshot=json.loads(Path(snapshot_path).read_text(encoding='utf-8-sig'));assert snapshot['pass'] and snapshot['source_sha256']==PIN_FBX
    old=json.loads(Path(old_diagnostic_path).read_text())
    assert snapshot['asset_guid']==old['source_renderer_mesh_guid'] and int(snapshot['mesh_file_id'])==old['source_renderer_mesh_local_file_id']
    assert snapshot['source_local_vertices']==old['source_mesh_vertices']
    assert [s['indices'] for s in snapshot['source_submeshes']]==[s['indices'] for s in old['source_submeshes']]
    vec=lambda row:tuple(row[axis] for axis in ('x','y','z'))
    uv=lambda row:tuple(row[axis] for axis in ('x','y'))
    q=lambda v:tuple(v)
    signature=lambda values:tuple(sorted(values))
    cyclic=lambda values:min(tuple(values[i:]+values[:i]) for i in range(3))
    raw_triangles=[list(range(i,i+3)) for i in range(0,36,3)]
    raw_keys=[signature([q(raw_uv[i]) for i in tri]) for tri in raw_triangles]
    assert len(set(raw_keys))==12,'UV_TRIANGLE_SIGNATURE_AMBIGUOUS'
    lookup=dict(zip(raw_keys,raw_triangles))
    actual_tris=[s['indices'][i:i+3] for s in snapshot['source_submeshes'] for i in range(0,len(s['indices']),3)]
    actual_keys=[signature([uv(snapshot['source_uv0'][i]) for i in tri]) for tri in actual_tris]
    assert Counter(raw_keys)==Counter(actual_keys),'UV_TRIANGLE_MULTISET_MISMATCH'
    pos_error=normal_error=0;reverse=direct=0;dot_min=1;rows=[]
    cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    sub=lambda a,b:tuple(x-y for x,y in zip(a,b))
    unit=lambda v:tuple(x/math.sqrt(sum(y*y for y in v)) for x in v)
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    for tri,key in zip(actual_tris,actual_keys):
     raw=lookup[key];corner_lookup={q(raw_uv[i]):i for i in raw};assert len(corner_lookup)==3
     raw_oriented=[q(raw_uv[i]) for i in raw];actual_oriented=[uv(snapshot['source_uv0'][i]) for i in tri]
     is_reverse=cyclic(list(reversed(raw_oriented)))==cyclic(actual_oriented)
     is_direct=cyclic(raw_oriented)==cyclic(actual_oriented)
     reverse+=is_reverse;direct+=is_direct
     for i in tri:
      raw_corner=corner_lookup[uv(snapshot['source_uv0'][i])]
      point=raw_points[raw_corner_ids[raw_corner]];expected=(-point[0]*.01,point[1]*.01,point[2]*.01)
      actual=vec(snapshot['source_local_vertices'][i]);pos_error=max(pos_error,max(abs(a-b) for a,b in zip(expected,actual)))
      n=raw_normals[raw_corner];expected_normal=unit((-n[0],n[1],n[2]));actual_normal=unit(vec(snapshot['source_local_normals'][i]))
      normal_error=max(normal_error,max(abs(a-b) for a,b in zip(expected_normal,actual_normal)))
     points=[vec(snapshot['source_local_vertices'][i]) for i in tri]
     face_normal=unit(cross(sub(points[1],points[0]),sub(points[2],points[0])))
     for i in tri:dot_min=min(dot_min,dot(face_normal,unit(vec(snapshot['source_local_normals'][i]))))
     rows.append({'uv_signature':key,'direct_order':is_direct,'reversed_order':is_reverse})
    assert pos_error<1e-7 and normal_error<1e-5 and reverse==12 and direct==0
    assert dot_min>.999,'GEOMETRY_NORMAL_FACING_MISMATCH'
    # Controls concern this bounded read-only diagnosis, not a production mapping.
    wrong_axis_error=max(abs(-raw_points[raw_corner_ids[c]][1]*.01-vec(snapshot['source_local_vertices'][i])[1]) for tri,key in zip(actual_tris,actual_keys) for i in tri for c in [dict((q(raw_uv[j]),j) for j in lookup[key])[uv(snapshot['source_uv0'][i])]])
    changed_keys=actual_keys.copy();changed_keys[0]=tuple([(123.,456.)]*3)
    duplicate_keys=actual_keys.copy();duplicate_keys[0]=duplicate_keys[1]
    one_reversed=list(actual_tris[0]);one_reversed.reverse()
    assert wrong_axis_error>.001 and Counter(changed_keys)!=Counter(raw_keys) and Counter(duplicate_keys)!=Counter(raw_keys)
    assert cyclic([uv(snapshot['source_uv0'][i]) for i in one_reversed])==cyclic([q(raw_uv[i]) for i in lookup[actual_keys[0]]])
    report={'status':'PINNED_SOURCE_FRAME_AND_WINDING_EXPLAINED_BY_INDEPENDENT_UV_CORRESPONDENCE',
     'scope':'same pinned source FBX/Unity Mesh, not a production import mapping or broad roundtrip PASS',
     'source_fbx_sha256':sha256(fbx),'source_mesh_guid':snapshot['asset_guid'],'source_mesh_file_id':snapshot['mesh_file_id'],
     'old_source_vertices_and_submesh_indices_exactly_match_new_read_only_observation':True,
     'old_source_metadata_context':'old report remains untouched; current explicit-remap meta differs, but exact same source vertex/index arrays and Mesh GUID/fileID join are required',
     'correspondence_basis':'only unordered UV triangle triples and exact within-triangle UV corner identity; no positions, Material identity, slot count, normal or fitted transform used to select matches',
     'uv_triangle_count':12,'uv_signatures_unique':True,'uv_corner_identity':'exact source UV pairs (dyadic values in this fixture)',
     'predeclared_C':[[ -.01,0,0],[0,.01,0],[0,0,.01]],'det_C':-1e-6,
     'position_C_max_absolute_residual':pos_error,'normal_C_inverse_transpose_max_normalized_residual':normal_error,
     'direct_order_count':direct,'uniform_reversed_order_count':reverse,'minimum_geometric_face_normal_vs_imported_corner_normal_dot':dot_min,
     'diagnosis':'index reversal accompanies the measured negative-determinant mesh-local coordinate conversion; inverse-transpose normal transport remains aligned with geometric facing, so the observed reversal alone is not an inverted-normal product defect',
     'controls':{'wrong_axis_rejected':wrong_axis_error>.001,'changed_UV_rejected':True,'duplicate_UV_triangle_rejected':True,'one_triangle_order_reversal_detected_separately':True},
     'source_probe_hashes_unchanged':snapshot['hashes_unchanged'],
     'limitations':['fixture UV signatures are unique; ambiguous/repeated UVs cannot certify this correspondence','does not generalize C to other import policies or assets','does not supply missing Material correspondence at ordinary product import','does not accept historical confirmed override output or arbitrary edited normals/winding']}
    return report


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FRAME_DIAGNOSTIC_ERROR:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
