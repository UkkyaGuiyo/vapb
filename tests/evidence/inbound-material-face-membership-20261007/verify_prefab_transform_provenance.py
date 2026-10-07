#!/usr/bin/env python3
"""Offline reconstruction of the pinned Prefab Renderer-to-root Unity transform."""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1] / "unity_model_material_probe" / "fixtures" / "ThreeSlotSource.unitypackage"
PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
PREFAB_PATH = "Assets/PublicMaterialSource/Direct.prefab"
PREFAB_SHA256 = "0d33eb041145f0c73cb69e61de720b580a33aa56e8d432ba04ce110618e50843"
UNITY_JSON = HERE / "unity-diagnostic.json"
UNITY_JSON_SHA256 = "f93f3e51f5c9435b291909cc105ef1f8b88de91ab5c8f9a988d06cebf2471079"
OWNERSHIP_JSON = HERE / "frame-diagnostic-ownership.json"
OWNERSHIP_JSON_SHA256 = "52c15704c9adb65691489712cb1360f89877505ac3cc124e26fd1bf8b97623c9"
OUTPUT = HERE / "prefab-transform-provenance.json"
TOLERANCE = 1.0e-4


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def fadd(a, b):
    return f32(f32(a) + f32(b))


def fsub(a, b):
    return f32(f32(a) - f32(b))


def fmul(a, b):
    return f32(f32(a) * f32(b))


def fdiv(a, b):
    return f32(f32(a) / f32(b))


def identity():
    return [[f32(r == c) for c in range(4)] for r in range(4)]


def matrix_multiply(a, b):
    out = identity()
    for r in range(4):
        for c in range(4):
            value = f32(0)
            for k in range(4):
                value = fadd(value, fmul(a[r][k], b[k][c]))
            out[r][c] = value
    return out


def local_trs(position, quaternion, scale):
    x, y, z, w = map(f32, quaternion)
    two = f32(2)
    # Unity Quaternion-to-matrix arithmetic, preserving float32 operations.
    xx, yy, zz = fmul(x, x), fmul(y, y), fmul(z, z)
    xy, xz, yz = fmul(x, y), fmul(x, z), fmul(y, z)
    xw, yw, zw = fmul(x, w), fmul(y, w), fmul(z, w)
    r = [
        [fsub(1, fmul(two, fadd(yy, zz))), fmul(two, fsub(xy, zw)), fmul(two, fadd(xz, yw))],
        [fmul(two, fadd(xy, zw)), fsub(1, fmul(two, fadd(xx, zz))), fmul(two, fsub(yz, xw))],
        [fmul(two, fsub(xz, yw)), fmul(two, fadd(yz, xw)), fsub(1, fmul(two, fadd(xx, yy)))],
    ]
    matrix = identity()
    for row in range(3):
        for col in range(3):
            matrix[row][col] = fmul(r[row][col], scale[col])
        matrix[row][3] = f32(position[row])
    return matrix


def extract_asset(package_path: Path, asset_path: str) -> bytes:
    # The package digest is checked by main before this archive is opened.
    with tarfile.open(package_path, "r:gz") as archive:
        matches = []
        for member in archive.getmembers():
            if not member.name.endswith("/pathname"):
                continue
            stream = archive.extractfile(member)
            if stream is None or stream.read().decode("utf-8", "strict").strip() != asset_path:
                continue
            prefix = member.name.rsplit("/", 1)[0]
            asset = archive.extractfile(prefix + "/asset")
            if asset is None:
                raise ValueError("PACKAGE_ASSET_MISSING")
            matches.append(asset.read())
        if len(matches) != 1:
            raise ValueError("PACKAGE_ASSET_PATH_NOT_UNIQUE")
        return matches[0]


def parse_documents(text):
    headers = list(re.finditer(r"(?m)^--- !u!(\d+) &(-?\d+)\s*$", text))
    docs = {}
    for index, header in enumerate(headers):
        class_id, file_id = int(header.group(1)), int(header.group(2))
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        if file_id in docs:
            raise ValueError("DUPLICATE_SERIALIZED_FILE_ID")
        docs[file_id] = {"class_id": class_id, "body": text[header.end():end]}
    if not docs:
        raise ValueError("PREFAB_HAS_NO_SERIALIZED_DOCUMENTS")
    return docs


def scalar_ref(body, field):
    match = re.search(r"(?m)^\s*" + re.escape(field) + r":\s*\{fileID:\s*(-?\d+)", body)
    if not match:
        raise ValueError("REFERENCE_MISSING:" + field)
    return int(match.group(1))


def list_refs(body, field, item_prefix):
    match = re.search(r"(?ms)^\s*" + re.escape(field) + r":\s*(.*?)(?=^\s*\w|\Z)", body)
    if not match:
        return []
    return [int(v) for v in re.findall(item_prefix + r"\s*\{fileID:\s*(-?\d+)", match.group(1))]


def vector(body, field, keys):
    match = re.search(r"(?m)^\s*" + re.escape(field) + r":\s*\{([^}]*)\}", body)
    if not match:
        raise ValueError("TRANSFORM_VECTOR_MISSING:" + field)
    values = dict((k, float(v)) for k, v in re.findall(r"([xyzw]):\s*([-+0-9.eE]+)", match.group(1)))
    if any(key not in values for key in keys):
        raise ValueError("TRANSFORM_VECTOR_COMPONENT_MISSING:" + field)
    return [f32(values[key]) for key in keys]


def reconstruct(prefab_bytes, mesh_guid, mesh_file_id):
    docs = parse_documents(prefab_bytes.decode("utf-8", "strict"))
    renderer_matches = []
    for file_id, doc in docs.items():
        if doc["class_id"] != 137:
            continue
        mesh = re.search(r"(?m)^\s*m_Mesh:\s*\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]+)", doc["body"])
        if mesh and int(mesh.group(1)) == int(mesh_file_id) and mesh.group(2).lower() == mesh_guid.lower():
            renderer_matches.append((file_id, doc))
    if len(renderer_matches) != 1:
        raise ValueError("SOURCE_RENDERER_REFERENCE_NOT_UNIQUE")
    renderer_id, renderer_doc = renderer_matches[0]
    game_object_id = scalar_ref(renderer_doc["body"], "m_GameObject")
    game_object = docs.get(game_object_id)
    if game_object is None or game_object["class_id"] != 1:
        raise ValueError("RENDERER_GAMEOBJECT_REFERENCE_INVALID")
    components = list_refs(game_object["body"], "m_Component", r"-\s*component:")
    if renderer_id not in components:
        raise ValueError("GAMEOBJECT_RENDERER_COMPONENT_LINK_MISSING")
    transform_ids = [ref for ref in components if ref in docs and docs[ref]["class_id"] == 4]
    if len(transform_ids) != 1:
        raise ValueError("GAMEOBJECT_TRANSFORM_LINK_NOT_UNIQUE")
    transform_id = transform_ids[0]
    if scalar_ref(docs[transform_id]["body"], "m_GameObject") != game_object_id:
        raise ValueError("TRANSFORM_GAMEOBJECT_BACKLINK_MISMATCH")

    child_to_parent = {}
    chain_child_first = []
    visited = set()
    current = transform_id
    while current:
        if current in visited:
            raise ValueError("TRANSFORM_PARENT_CYCLE")
        visited.add(current)
        transform = docs.get(current)
        if transform is None or transform["class_id"] != 4:
            raise ValueError("TRANSFORM_REFERENCE_INVALID")
        body = transform["body"]
        parent_id = scalar_ref(body, "m_Father")
        children = list_refs(body, "m_Children", r"-")
        if parent_id:
            parent = docs.get(parent_id)
            if parent is None or parent["class_id"] != 4:
                raise ValueError("PARENT_TRANSFORM_REFERENCE_INVALID")
            if current not in list_refs(parent["body"], "m_Children", r"-"):
                raise ValueError("PARENT_CHILD_LINK_NOT_RECIPROCAL")
        chain_child_first.append({"transform_file_id": current,
                                  "game_object_file_id": scalar_ref(body, "m_GameObject"),
                                  "parent_file_id": parent_id,
                                  "child_file_ids": children,
                                  "position_f32": vector(body, "m_LocalPosition", "xyz"),
                                  "rotation_xyzw_f32": vector(body, "m_LocalRotation", "xyzw"),
                                  "scale_f32": vector(body, "m_LocalScale", "xyz")})
        current = parent_id
    chain = list(reversed(chain_child_first))
    world = identity()
    for item in chain:
        item["local_matrix_f32"] = local_trs(item["position_f32"], item["rotation_xyzw_f32"], item["scale_f32"])
        world = matrix_multiply(world, item["local_matrix_f32"])
    return {"renderer_file_id": renderer_id, "renderer_game_object_file_id": game_object_id,
            "renderer_transform_file_id": transform_id, "root_transform_file_id": chain[0]["transform_file_id"],
            "root_game_object_file_id": chain[0]["game_object_file_id"], "chain_root_to_renderer": chain,
            "composed_matrix_f32": world}


def ownership_matrix(ownership):
    if ownership.get("status") != "UNPROVEN_FRAME_CANDIDATE_ONLY" or ownership.get("mapping") is not None:
        raise ValueError("OWNERSHIP_FRAME_RESULT_NOT_FAIL_CLOSED")
    unity = ownership.get("unity")
    unity_meta = ownership.get("unity_meta")
    if not isinstance(unity, dict) or not isinstance(unity_meta, dict) or unity_meta.get("C_independently_justified") is not False:
        raise ValueError("C_MUST_REMAIN_UNPROVEN")
    matrix = unity.get("M")
    if not isinstance(matrix, list) or len(matrix) != 4 or any(not isinstance(row, list) or len(row) != 4 for row in matrix):
        raise ValueError("OWNERSHIP_M_INVALID")
    return [[float(v) for v in row] for row in matrix]


def main():
    if OUTPUT.exists():
        raise FileExistsError("OUTPUT_ALREADY_EXISTS")
    actual_package_hash = file_sha256(PACKAGE)
    if actual_package_hash != PACKAGE_SHA256:
        raise ValueError("PINNED_PACKAGE_SHA256_MISMATCH")
    # Package bytes are not opened until their pinned digest passes.
    prefab = extract_asset(PACKAGE, PREFAB_PATH)
    actual_prefab_hash = sha256_bytes(prefab)
    if actual_prefab_hash != PREFAB_SHA256:
        raise ValueError("PINNED_PREFAB_ASSET_SHA256_MISMATCH")
    if file_sha256(UNITY_JSON) != UNITY_JSON_SHA256:
        raise ValueError("PINNED_UNITY_DIAGNOSTIC_SHA256_MISMATCH")
    if file_sha256(OWNERSHIP_JSON) != OWNERSHIP_JSON_SHA256:
        raise ValueError("PINNED_OWNERSHIP_RESULT_SHA256_MISMATCH")
    unity = json.loads(UNITY_JSON.read_text(encoding="utf-8"))
    ownership = json.loads(OWNERSHIP_JSON.read_text(encoding="utf-8"))
    target = ownership_matrix(ownership)
    chain = reconstruct(prefab, unity["source_renderer_mesh_guid"], unity["source_renderer_mesh_local_file_id"])
    actual = chain["composed_matrix_f32"]
    residual = [[actual[r][c] - target[r][c] for c in range(4)] for r in range(4)]
    max_abs = max(abs(value) for row in residual for value in row)
    result = {
        "status": "UNPROVEN_FRAME_CANDIDATE_ONLY",
        "mapping": None,
        "C_independently_justified": False,
        "question": "Whether the recorded Unity mesh-to-Prefab-root M is reproduced by the authored Prefab Transform chain.",
        "prefab_chain_reproduces_recorded_M_within_tolerance": max_abs <= TOLERANCE,
        "source": {"package_path_in_repo": "tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage",
                   "package_sha256": actual_package_hash, "prefab_asset_path": PREFAB_PATH,
                   "prefab_asset_sha256": actual_prefab_hash,
                   "unity_diagnostic_sha256": UNITY_JSON_SHA256,
                   "ownership_frame_result_sha256": OWNERSHIP_JSON_SHA256},
        "serialized_reference_trace": chain,
        "comparison": {"recorded_M": target, "reconstructed_M_f32": actual,
                       "residual_reconstructed_minus_recorded": residual,
                       "max_abs_residual": max_abs, "absolute_tolerance": TOLERANCE,
                       "all_16_values_within_tolerance": max_abs <= TOLERANCE},
        "interpretation": "This experiment only checks whether recorded M follows the authored Prefab transform chain. It does not independently justify C, prove the Unity model importer factorization, or establish face mapping.",
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "mapping": None,
                      "prefab_chain_reproduces_recorded_M_within_tolerance": result["prefab_chain_reproduces_recorded_M_within_tolerance"],
                      "max_abs_residual": max_abs, "absolute_tolerance": TOLERANCE,
                      "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
