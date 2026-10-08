"""One fixed-run comparison using the preregistered scalar oracle; no fitting.
Usage: python compare_fixed_capture.py REPO BLENDER_RUN UNITY_RUN
"""
import hashlib
import json
import sys
from pathlib import Path

repo, blender_run, unity_run = map(Path, sys.argv[1:])
sys.path.insert(0, str(repo / "tests/coordinate_holdout_20261007"))
from oracle import EXPECTED_U_TAGS, maxima_for_case, matrix4, point, validate_u_tags, verdict
from contract import TOLERANCE, public_contract


def digest(raw): return hashlib.sha256(raw).hexdigest()
def read(path):
    raw = path.read_bytes()
    return json.loads(raw), digest(raw)

prepared, prepared_hash = read(repo / "tests/coordinate_holdout_unity_adapter_20261008/prepared-input.json")
assert prepared_hash == "0848806638b57e43f5ff1f245a9e42935ca0184e5df42f7e39f662b175f86af3"
manifest, manifest_hash = read(blender_run / "fixtures/manifest.json")
prereg, prereg_hash = read(blender_run / "preregistration/preregistration.json")
contract, contract_hash = read(blender_run / "preregistration/contract.json")
authored, authored_hash = read(blender_run / "preregistration/authored-oracle.json")
blender, blender_hash = read(blender_run / "blender-capture.json")
unity, unity_hash = read(unity_run / "unity-capture.json")
assert contract == public_contract() == manifest["contract"]
assert contract_hash == prereg["contract_sha256"] and authored_hash == prereg["authored_oracle_sha256"]
assert manifest_hash == prepared["source_manifest_sha256"] == blender["manifest_sha256"]
assert prereg_hash == prepared["preregistration_sha256"] == manifest["preregistration_sha256"] == blender["preregistration_sha256"]
assert unity["manifest_sha256"] == prepared_hash
assert unity["schema"] == "vapb-coordinate-intervention-unity-capture-v1"
assert unity["status"] == "UNITY_FACE_IDENTITY_CAPTURED" and not unity["errors"]
assert unity["unity_version"] == "2022.3.22f1" and blender["blender_version"] == "5.2.1"
ids = ["H0", "H1", "H2", "H3"]
assert [r["case_id"] for r in blender["cases"]] == [r["case_id"] for r in unity["cases"]] == ids
assert [r["id"] for r in prepared["cases"]] == [r["id"] for r in authored["cases"]] == ids
for name, expected in prereg["source_sha256"].items():
    assert digest((repo / "tests/coordinate_holdout_20261007" / name).read_bytes()) == expected
for row in prepared["cases"]:
    assert digest((blender_run / "fixtures" / row["filename"]).read_bytes()) == row["sha256"]
    assert digest((unity_run / "Project/Assets/VapbCoordinateIntervention" / row["filename"]).read_bytes()) == row["sha256"]
for name in ("VapbCoordinateInterventionProbe.cs", "ProbeCaptureExitGuard.cs"):
    assert digest((unity_run / "Project/Assets/Editor" / name).read_bytes()) == prepared["adapter_sources_sha256"][name]

rows, unity_world = [], {}
for b, u, frozen, expected in zip(blender["cases"], unity["cases"], prepared["cases"], authored["cases"]):
    assert b["input_sha256"] == u["input_sha256"] == frozen["sha256"]
    assert len(u["hierarchy"]) == len(u["renderers"]) == 1
    renderer = u["renderers"][0]
    assert renderer["transform_path"] == u["hierarchy"][0]["path"]
    uv, vertices = renderer["uv0"], renderer["vertices_local"]
    assert renderer["vertex_count"] == len(uv) == len(vertices) == 18
    tags = [float(v["x"]) for v in uv]
    validate_u_tags(tags)
    up = {tag: [float(v[k]) for k in ("x", "y", "z")] for tag, v in zip(tags, vertices)}
    bp = {float(tag): value for tag, value in b["corner_points_by_u"].items()}
    flat = u["hierarchy"][0]["world_matrix"]
    assert len(flat) == 16
    uw = matrix4([flat[i:i+4] for i in range(0,16,4)])
    bw = matrix4(b["mesh_world_matrix"])
    maxima = maxima_for_case(bp, up, bw, uw, expected["authored_unit_ratio"])
    unity_world[u["case_id"]] = {tag: point(uw, up[tag]) for tag in EXPECTED_U_TAGS}
    predicted = {float(c["u_tag"]): c["unity_world_candidate"] for c in expected["corners"]}
    authored_max = max(abs(unity_world[u["case_id"]][tag][i] - predicted[tag][i]) for tag in EXPECTED_U_TAGS for i in range(3))
    assert u["face_membership_matches_source_identity"] and u["unmatched_face_count"] == 0
    rows.append({"case_id": u["case_id"], "candidate_maxima": maxima, "candidate_status": verdict(maxima),
                 "unity_authored_world_max_abs": authored_max,
                 "unity_authored_status": "PASS" if authored_max <= TOLERANCE else "FAIL"})
h1 = max(abs(unity_world["H1"][t][i] - unity_world["H0"][t][i]) for t in EXPECTED_U_TAGS for i in range(3))
h2 = max(abs(unity_world["H2"][t][i] - .1 * unity_world["H0"][t][i]) for t in EXPECTED_U_TAGS for i in range(3))
result = {"schema": "vapb-coordinate-holdout-paired-result-v1", "tolerance": TOLERANCE,
          "candidate_status": "PASS" if all(r["candidate_status"] == "PASS" for r in rows) else "FAIL",
          "unity_authored_status": "PASS" if all(r["unity_authored_status"] == "PASS" for r in rows) else "FAIL",
          "unity_within_tool": {"H1_minus_H0_max_abs": h1, "H2_minus_0.1_H0_max_abs": h2,
                                "status": "PASS" if max(h1,h2) <= TOLERANCE else "FAIL"},
          "cases": rows, "blender_capture_sha256": blender_hash, "unity_capture_sha256": unity_hash,
          "prepared_input_sha256": prepared_hash, "source_manifest_sha256": manifest_hash,
          "preregistration_sha256": prereg_hash, "comparison_source_sha256": digest(Path(__file__).read_bytes()),
          "scope": "Four single-root synthetic holdouts only; not external-package Material GUID/fileID or full product round-trip acceptance."}
with (unity_run / "paired-comparison.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
print(json.dumps(result, indent=2, sort_keys=True))
