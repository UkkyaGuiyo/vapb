"""Create an immutable preregistration directory before any FBX is exported.

Usage: python prepare_contract.py NEW_PREREGISTRATION_DIR
All source files in this subtree are hashed before outputs are written. Existing
directories and files are never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from contract import CASES, CORNER_UVS, GEOMETRY, TOLERANCE, public_contract, validate_contract
from oracle import (CWORLD, authored_trs, expected_unity_world, local_matrix,
                    point, scale_authored_world)


ROOT = Path(__file__).resolve().parent
CASE_IDS = tuple(case["id"] for case in CASES)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def make_oracle():
    cases = []
    for case in CASES:
        ratio = float(case["unit_scale_length"]) / float(CASES[0]["unit_scale_length"])
        wb = scale_authored_world(authored_trs(case["location"], case["rotation_degrees"], case["scale"]), ratio)
        wu = expected_unity_world(wb, ratio)
        d = local_matrix(ratio)
        corners = []
        for index, uv in enumerate(CORNER_UVS):
            vb = GEOMETRY["vertices"][index]
            corners.append({"u_tag": uv[0], "v_diagnostic": uv[1],
                            "blender_local_authored": vb,
                            "unity_local_candidate": list(point(d, vb)),
                            "blender_world_authored": list(point(wb, vb)),
                            "unity_world_candidate": list(point(CWORLD, point(wb, vb)))})
        cases.append({"id": case["id"], "authored_unit_ratio": ratio,
                      "blender_world_authored": [list(row) for row in wb],
                      "unity_world_candidate": [list(row) for row in wu],
                      "corners": corners})
    return {"schema": "vapb-coordinate-holdout-authored-oracle-v1",
            "meaning": "Pure authored-input calculation only; no importer observation or prior capture is used.",
            "cases": cases}


def write_new(path, content):
    with path.open("xb") as stream:
        stream.write(content)


def create_output_dir(path):
    """Create a fresh artifact directory; refuse any existing path."""
    Path(path).mkdir(parents=True, exist_ok=False)


def validate_authored_oracle(oracle):
    if oracle.get("schema") != "vapb-coordinate-holdout-authored-oracle-v1":
        raise ValueError("AUTHORED_ORACLE_SCHEMA_INVALID")
    cases = oracle.get("cases")
    if not isinstance(cases, list) or tuple(row.get("id") for row in cases) != CASE_IDS:
        raise ValueError("AUTHORED_ORACLE_CASE_SET_INVALID")
    expected_tags = {float(uv[0]) for uv in CORNER_UVS}
    for row in cases:
        corners = row.get("corners")
        if not isinstance(corners, list) or len(corners) != 18:
            raise ValueError("AUTHORED_ORACLE_CORNER_COUNT_INVALID:" + str(row.get("id")))
        tags = [float(c.get("u_tag")) for c in corners]
        if len(set(tags)) != 18 or set(tags) != expected_tags or not all(math.isfinite(t) for t in tags):
            raise ValueError("AUTHORED_ORACLE_TAG_SET_INVALID:" + str(row.get("id")))
        if not math.isfinite(float(row.get("authored_unit_ratio", math.nan))) or float(row["authored_unit_ratio"]) <= 0:
            raise ValueError("AUTHORED_ORACLE_UNIT_RATIO_INVALID:" + str(row.get("id")))
        for corner in corners:
            for key in ("blender_local_authored", "unity_local_candidate", "blender_world_authored", "unity_world_candidate"):
                vector = corner.get(key)
                if not isinstance(vector, list) or len(vector) != 3 or any(not math.isfinite(float(x)) for x in vector):
                    raise ValueError("AUTHORED_ORACLE_VECTOR_INVALID:%s:%s" % (row.get("id"), key))
        for key in ("blender_world_authored", "unity_world_candidate"):
            matrix = row.get(key)
            if (not isinstance(matrix, list) or len(matrix) != 4
                    or any(not isinstance(line, list) or len(line) != 4 for line in matrix)
                    or any(not math.isfinite(float(x)) for line in matrix for x in line)):
                raise ValueError("AUTHORED_ORACLE_MATRIX_INVALID:%s:%s" % (row.get("id"), key))
    return True


def verify_frozen_payload(prereg, source_hashes, contract_bytes, oracle_bytes):
    if prereg.get("schema") != "vapb-coordinate-holdout-preregistration-v1":
        raise ValueError("PREREGISTRATION_SCHEMA_INVALID")
    if prereg.get("source_sha256") != source_hashes:
        raise ValueError("PREREGISTRATION_SOURCE_HASH_MISMATCH")
    if hashlib.sha256(contract_bytes).hexdigest() != prereg.get("contract_sha256"):
        raise ValueError("PREREGISTRATION_CONTRACT_HASH_MISMATCH")
    if hashlib.sha256(oracle_bytes).hexdigest() != prereg.get("authored_oracle_sha256"):
        raise ValueError("PREREGISTRATION_ORACLE_HASH_MISMATCH")
    return True


def prepare(destination):
    errors = validate_contract()
    if errors:
        raise ValueError("INVALID_CONTRACT:" + ",".join(errors))
    source_files = sorted(p for p in ROOT.glob("*.py") if p.is_file())
    source_hashes = {p.name: sha256(p) for p in source_files}
    contract = public_contract()
    oracle = make_oracle()
    validate_authored_oracle(oracle)
    for row in oracle["cases"]:
        if len(row["corners"]) != 18 or not all(
                math.isfinite(float(x)) for matrix in (row["blender_world_authored"], row["unity_world_candidate"])
                for line in matrix for x in line):
            raise ValueError("AUTHORED_ORACLE_NONFINITE_OR_INCOMPLETE")
    create_output_dir(destination)
    contract_bytes = canonical_bytes(contract)
    oracle_bytes = canonical_bytes(oracle)
    verify_frozen_payload({"schema": "vapb-coordinate-holdout-preregistration-v1",
                           "source_sha256": source_hashes,
                           "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
                           "authored_oracle_sha256": hashlib.sha256(oracle_bytes).hexdigest()},
                          source_hashes, contract_bytes, oracle_bytes)
    write_new(destination / "contract.json", contract_bytes)
    write_new(destination / "authored-oracle.json", oracle_bytes)
    prereg = {
        "schema": "vapb-coordinate-holdout-preregistration-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": source_hashes,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "authored_oracle_sha256": hashlib.sha256(oracle_bytes).hexdigest(),
        "tolerance": TOLERANCE,
        "status": "FROZEN_BEFORE_EXPORT_AND_IMPORT",
    }
    write_new(destination / "preregistration.json", canonical_bytes(prereg))
    return prereg


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        raise SystemExit("EXPECTED_NEW_PREREGISTRATION_DIRECTORY")
    result = prepare(Path(args[0]).resolve())
    print("PREREGISTRATION_CREATED=" + str(Path(args[0]).resolve()))
    print("SOURCE_FILES=" + str(len(result["source_sha256"])))
    print("CONTRACT_SHA256=" + result["contract_sha256"])
    print("ORACLE_SHA256=" + result["authored_oracle_sha256"])
