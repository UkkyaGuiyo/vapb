"""Prepare four frozen holdouts for the existing Unity observation probe.
Usage: python prepare_unity_manifest.py MANIFEST PREREG_DIR MANIFEST_SHA NEW_OUTPUT
No Unity launch, project creation, FBX modification or candidate fitting occurs.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def adapt_manifest(manifest, contract):
    if (manifest.get("schema") != "vapb-coordinate-holdout-manifest-v1"
            or contract.get("schema") != "vapb-coordinate-holdout-contract-v1"
            or manifest.get("contract") != contract
            or manifest.get("blender_version") != "5.2.1"):
        raise ValueError("HOLDOUT_CONTRACT_MISMATCH")
    cases = manifest.get("cases", [])
    if [row.get("id") for row in cases] != ["H0", "H1", "H2", "H3"]:
        raise ValueError("HOLDOUT_CASE_SET_OR_ORDER_INVALID")
    frozen_cases = contract["cases"]
    if [row.get("id") for row in frozen_cases] != ["H0", "H1", "H2", "H3"]:
        raise ValueError("HOLDOUT_CONTRACT_CASE_SET_INVALID")
    rows = []
    for row, frozen in zip(cases, frozen_cases):
        if any(row.get(key) != value for key, value in frozen.items()):
            raise ValueError("HOLDOUT_CASE_CONTRACT_MISMATCH")
        if row.get("filename") != row["id"] + ".fbx":
            raise ValueError("HOLDOUT_FILENAME_INVALID")
        digest = row.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("HOLDOUT_INPUT_SHA_INVALID")
        materials = row.get("materials_by_fixture_identity", [])
        if ([m.get("fixture_material_id") for m in materials] != contract["geometry"]["materials"]
                or len({m.get("name") for m in materials}) != 3
                or len({m.get("fbx_object_uid") for m in materials}) != 3):
            raise ValueError("HOLDOUT_MATERIAL_KEYS_INVALID")
        rows.append({**copy.deepcopy(frozen), "filename": row["filename"], "sha256": digest,
                     "factor": "independent-holdout",
                     "source_material_names": [m["name"] for m in materials],
                     "source_material_ids": [m["fixture_material_id"] for m in materials],
                     "source_material_fbx_uids": [m["fbx_object_uid"] for m in materials]})
    geometry = contract["geometry"]
    return {"schema": "vapb-coordinate-holdout-unity-input-v1", "blender_version": "5.2.1",
            "spec": {"schema": "vapb-coordinate-holdout-probe-spec-v1", "geometry": {
                "geometry_id": geometry["geometry_id"], "materials": geometry["materials"],
                "faces": [{"face_id": face["face_id"], "material": face["material_id"],
                           "uvs": [{"x": uv[0], "y": uv[1]} for uv in face["uvs"]]}
                          for face in geometry["faces"]]}}, "cases": rows}


def prepare(manifest_path, prereg_dir, expected_manifest_sha, output):
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha:
        raise ValueError("MANIFEST_EXTERNAL_HASH_MISMATCH")
    manifest = json.loads(manifest_bytes)
    prereg_bytes = (prereg_dir / "preregistration.json").read_bytes()
    prereg_hash = hashlib.sha256(prereg_bytes).hexdigest()
    prereg = json.loads(prereg_bytes)
    if prereg.get("status") != "FROZEN_BEFORE_EXPORT_AND_IMPORT":
        raise ValueError("PREREGISTRATION_STATUS_INVALID")
    artifacts = {}
    for filename, key in (("contract.json", "contract_sha256"), ("authored-oracle.json", "authored_oracle_sha256")):
        raw = (prereg_dir / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != prereg.get(key):
            raise ValueError("PREREGISTRATION_ARTIFACT_HASH_MISMATCH")
        artifacts[filename] = json.loads(raw)
    if (manifest.get("preregistration_sha256") != prereg_hash
            or manifest.get("source_sha256") != prereg.get("source_sha256")):
        raise ValueError("MANIFEST_PREREGISTRATION_MISMATCH")
    result = adapt_manifest(manifest, artifacts["contract.json"])
    source_root = Path(__file__).resolve().parents[1] / "coordinate_holdout_20261007"
    actual_sources = {p.name: sha256(p) for p in source_root.glob("*.py")}
    if actual_sources != prereg["source_sha256"]:
        raise ValueError("FROZEN_SOURCE_HASH_MISMATCH")
    for row in result["cases"]:
        if sha256(manifest_path.parent / row["filename"]) != row["sha256"]:
            raise ValueError("HOLDOUT_FBX_HASH_MISMATCH")
    result["source_manifest_sha256"] = expected_manifest_sha
    result["preregistration_sha256"] = prereg_hash
    probe_dir = source_root.parent / "coordinate_intervention_20261007/Editor"
    result["adapter_sources_sha256"] = {"prepare_unity_manifest.py": sha256(__file__),
        **{p.name: sha256(p) for p in probe_dir.glob("*.cs")}}
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return result

if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("EXPECTED_MANIFEST_PREREG_MANIFEST_SHA_NEW_OUTPUT")
    prepare(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
    print("UNITY_INPUT_MANIFEST_SHA256=" + sha256(sys.argv[4]))
