"""T0-C closure gate for the pinned public three-slot fixture."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import unicodedata

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
if any(name == "strict_source_import" or name.startswith("strict_source_import.")
       for name in sys.modules):
    raise ImportError("refusing cached strict_source_import helper")
import strict_source_import as _strict_source_import
_expected_helper = Path(__file__).resolve().parent / "strict_source_import.py"
if Path(_strict_source_import.__file__).resolve() != _expected_helper.resolve():
    raise ImportError("strict_source_import helper did not come from selected tests directory")
_strict_source_import.load_source_package(ROOT)
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository

SOURCE_PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
OUTPUT_PACKAGE_SHA256 = "b8f3901ef5dd386ecf1a51d266ff3f6b866c6ae7c3409f66e87be335f292c16d"
SOURCE_FBX_SHA256 = "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5"
SOURCE_FBXMETA_SHA256 = "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d"
MATERIAL_ROW = re.compile(
    rb"(?m)^\s*-\s*\{\s*fileID:\s*(-?\d+)\s*,\s*guid:\s*([0-9a-fA-F]{32})\s*,\s*type:\s*(\d+)\s*\}"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def independent_tar_assets(package_path: Path) -> dict[str, dict[str, bytes]]:
    """Strict independent tarfile pass: reject duplicate/case-variant member keys."""
    groups: dict[str, dict[str, bytes]] = {}
    spellings: dict[str, str] = {}
    with tarfile.open(package_path, "r:*") as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name.replace("\\", "/")).parts
            if len(parts) == 1 and member.isdir():
                continue
            if len(parts) != 2:
                raise ValueError(f"unsupported archive member path: {member.name}")
            guid, kind = parts
            if not re.fullmatch(r"[0-9a-fA-F]{32}", guid) or kind not in {
                "asset", "asset.meta", "pathname", "preview.png"
            }:
                raise ValueError(f"unsupported archive member: {member.name}")
            if not member.isfile():
                raise ValueError(f"archive member is not a regular file: {member.name}")
            canonical = guid.lower()
            old_spelling = spellings.setdefault(canonical, guid)
            if old_spelling != guid:
                raise ValueError(f"case-variant GUID directory collision: {old_spelling} / {guid}")
            payloads = groups.setdefault(canonical, {})
            if kind in payloads:
                raise ValueError(f"duplicate GUID/kind member: {canonical}/{kind}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"missing archive payload: {member.name}")
            payloads[kind] = stream.read()
    path_owners: dict[str, str] = {}
    for guid, row in groups.items():
        raw_path = row.get("pathname")
        if raw_path is None:
            continue
        value = unicodedata.normalize("NFC", raw_path.decode("utf-8-sig").strip().replace("\\", "/"))
        pure = PurePosixPath(value)
        if (not value or "\x00" in value or pure.is_absolute()
                or re.match(r"^[A-Za-z]:", value)
                or any(part in ("", ".", "..") for part in pure.parts)):
            raise ValueError(f"unsafe Unity pathname for {guid}: {value!r}")
        key = "/".join(pure.parts).casefold()
        previous = path_owners.setdefault(key, guid)
        if previous != guid:
            raise ValueError(f"casefold/NFC Unity pathname collision: {previous} and {guid} at {value}")
    return groups


def prefab_material_refs(raw: bytes) -> list[dict[str, str]]:
    docs = re.split(rb"(?m)^---\s*!u!\d+\s+&[^\r\n]*\r?\n", raw)
    headers = re.findall(rb"(?m)^---\s*!u!(\d+)\s+&[^\r\n]*\r?\n", raw)
    refs = []
    for class_id, body in zip(headers, docs[1:]):
        if class_id != b"137":
            continue
        lines = body.splitlines()
        inside = False
        key_indent = -1
        for line in lines:
            indent = len(line) - len(line.lstrip(b" \t"))
            stripped = line.strip()
            if not inside:
                if re.fullmatch(rb"m_Materials\s*:", stripped):
                    inside, key_indent = True, indent
                continue
            if not stripped:
                continue
            if stripped.startswith(b"-"):
                match = MATERIAL_ROW.fullmatch(stripped)
                if not match:
                    raise ValueError("unsupported source Prefab Material row")
                refs.append({"file_id": match.group(1).decode(),
                             "guid": match.group(2).decode().lower(),
                             "type": match.group(3).decode()})
            elif indent <= key_indent:
                break
    if len(refs) != 3:
        raise ValueError(f"expected three raw Prefab Material refs, got {len(refs)}")
    return refs


def load_production_assets(path: Path) -> dict[str, object]:
    assets = RawAssetRepository(path).read_all()
    return {asset.guid.lower(): asset for asset in assets}


def checked_assets(path: Path) -> dict[str, dict[str, bytes]]:
    production_assets = load_production_assets(path)
    raw_assets = independent_tar_assets(path)
    if set(production_assets) != set(raw_assets):
        raise ValueError("production reader and independent tar inventory GUIDs differ")
    for guid, asset in production_assets.items():
        raw = raw_assets[guid]
        if asset.pathname.encode("utf-8") != raw["pathname"].decode("utf-8-sig").strip().encode("utf-8"):
            raise ValueError(f"production/raw pathname differs for {guid}")
        if asset.asset_bytes != raw.get("asset", b"") or asset.meta_bytes != raw["asset.meta"]:
            raise ValueError(f"production/raw bytes differ for {guid}")
    return raw_assets


def manifest_asset(assets: dict[str, dict[str, bytes]]) -> tuple[str, dict, dict[str, bytes]]:
    matches = [(guid, row) for guid, row in assets.items()
               if row.get("pathname", b"").decode("utf-8-sig").strip().lower().endswith("/manifest.json")]
    if len(matches) != 1:
        raise ValueError(f"expected one generated manifest asset, got {len(matches)}")
    guid, row = matches[0]
    return guid, json.loads(row["asset"].decode("utf-8")), row


def assert_closure(source_assets: dict[str, dict[str, bytes]],
                   output_assets: dict[str, dict[str, bytes]],
                   expected_refs: list[dict[str, str]]) -> dict:
    for ref in expected_refs:
        guid = ref["guid"]
        if guid not in output_assets:
            raise ValueError(f"missing expected Material GUID {guid}")
        if guid not in source_assets:
            raise ValueError(f"source fixture lacks expected Material GUID {guid}")
        src, out = source_assets[guid], output_assets[guid]
        if not src["pathname"].decode("utf-8-sig").strip().lower().endswith(".mat"):
            raise ValueError(f"expected source GUID is not a Material: {guid}")
        for kind in ("asset", "asset.meta", "pathname"):
            if src.get(kind) != out.get(kind):
                raise ValueError(f"preserved Material {guid} {kind} bytes/path differ")
        meta_guid = re.search(rb"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", out["asset.meta"])
        if not meta_guid or meta_guid.group(1).decode().lower() != guid:
            raise ValueError(f"Material meta GUID mismatch: {guid}")
        file_id = re.search(rb"(?m)^---\s*!u!21\s+&(-?\d+)\b", out["asset"])
        if not file_id or file_id.group(1).decode() != ref["file_id"]:
            raise ValueError(f"Material payload fileID mismatch: {guid}")

    manifest_guid, manifest, manifest_row = manifest_asset(output_assets)
    if manifest.get("schema_version") != "vapb-export-manifest-1" or manifest.get("errors"):
        raise ValueError("manifest schema or errors are invalid")
    source_identities = {(row.get("source_guid", "").lower(), row.get("source_path"), row.get("source_sha256"))
                         for row in manifest.get("source_assets", [])}
    for ref in expected_refs:
        src = source_assets[ref["guid"]]
        expected = (ref["guid"], src["pathname"].decode("utf-8-sig").strip(), sha256(src["asset"]))
        if expected not in source_identities:
            raise ValueError(f"manifest source identity/payload hash missing for {ref['guid']}")

    task_rows = [task for task in manifest.get("reference_rebind_tasks", [])
                 if isinstance(task, dict) and task.get("kind") == "RESTORE_DIRECT_SKIN_VARIANT_V1"]
    if len(task_rows) != 1:
        raise ValueError(f"expected one direct-skin task with Material bindings, got {len(task_rows)}")
    bindings = task_rows[0].get("material_bindings", [])
    actual_refs = [{"guid": str(row.get("guid", "")).lower(),
                    "file_id": str(row.get("file_id", ""))} for row in bindings]
    fixed_refs = [{"guid": row["guid"], "file_id": row["file_id"]} for row in expected_refs]
    if actual_refs != fixed_refs or any(not row.get("transport_id") for row in bindings):
        raise ValueError("manifest Material binding order/transport IDs differ from raw Prefab refs")
    material_mappings = manifest.get("material_mappings")
    if not isinstance(material_mappings, list):
        raise ValueError("manifest material_mappings is missing or malformed")
    # This unchanged-import route creates no new Material asset mappings. The source
    # Material slot identities are represented in the direct-skin rebind task above.
    if material_mappings:
        raise ValueError("unexpected generated Material mappings in unchanged-import closure")

    generated = [row for row in manifest.get("export_assets", [])
                 if row.get("operation") == "CREATE" and
                 str(row.get("desired_export_path", "")).lower().endswith(".fbx")]
    if len(generated) != 1:
        raise ValueError(f"expected one generated FBX in manifest, got {len(generated)}")
    generated_guid = str(generated[0].get("export_identity", {}).get("export_guid", "")).lower()
    generated_path = str(generated[0].get("desired_export_path", ""))
    if generated_guid not in output_assets:
        raise ValueError("manifest generated FBX GUID is absent from package")
    matches = [(guid, row) for guid, row in output_assets.items()
               if row.get("pathname", b"").decode("utf-8-sig").strip() == generated_path]
    if len(matches) != 1 or matches[0][0] != generated_guid:
        raise ValueError("generated FBX path/GUID does not match manifest")
    generated_row = matches[0][1]
    if not generated_row.get("asset") or not generated_row.get("asset.meta"):
        raise ValueError("generated FBX payload or meta is absent")
    generated_meta_guid = re.search(rb"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", generated_row["asset.meta"])
    if not generated_meta_guid or generated_meta_guid.group(1).decode().lower() != generated_guid:
        raise ValueError("generated FBX meta GUID differs from manifest")
    if task_rows[0].get("model_guid", "").lower() != generated_guid:
        raise ValueError("direct-skin task model GUID differs from generated FBX GUID")
    if task_rows[0].get("model_sha256", "").lower() != sha256(generated_row["asset"]):
        raise ValueError("direct-skin task model SHA differs from generated FBX payload")
    return {"manifest_guid": manifest_guid, "material_refs": fixed_refs,
            "path_inventory_collision_free": True,
            "manifest_material_mappings": material_mappings,
            "material_transport_ids": [row["transport_id"] for row in bindings],
            "generated_fbx_guid": generated_guid, "generated_fbx_path": generated_path,
            "generated_fbx_sha256": sha256(generated_row["asset"]),
            "generated_fbx_bytes": generated_row["asset"]}


def write_negative_missing_material(package_path: Path, target: Path, missing_guid: str) -> None:
    """Create a disposable archive copy omitting one GUID; never modify the input."""
    with tarfile.open(package_path, "r:*") as source, target.open("xb") as raw_output:
        with tarfile.open(fileobj=raw_output, mode="w:gz") as output:
            for member in source.getmembers():
                if member.name.lower().startswith(missing_guid.lower() + "/"):
                    continue
                stream = source.extractfile(member) if member.isfile() else None
                output.addfile(member, stream)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) not in (5, 6):
        raise SystemExit("usage: -- <source.unitypackage> <output.unitypackage> <run-dir> <t0a-result.json> <result.json> [expected-output-sha256]")
    source_path, output_path, run_dir, t0a_path, result_path = map(Path, args[:5])
    expected_output_sha = args[5].lower() if len(args) == 6 else OUTPUT_PACKAGE_SHA256
    source_path, output_path, run_dir, t0a_path, result_path = map(
        lambda value: value.resolve(), (source_path, output_path, run_dir, t0a_path, result_path))
    expected = {"source": source_path, "output": output_path, "T0-A report": t0a_path}
    outputs = {"T0-C report": result_path, "generated FBX": run_dir / "generated.fbx",
               "negative package": run_dir / "negative-missing-material.unitypackage"}
    from strict_run_paths import validate_run_paths, write_json_exclusive
    validate_run_paths(expected, outputs)
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {"stage": "T0-C-OUTPUT-CLOSURE", "status": "FAIL"}
    try:
        if sha256(source_path.read_bytes()) != SOURCE_PACKAGE_SHA256:
            raise ValueError("fixed source package SHA mismatch")
        output_sha = sha256(output_path.read_bytes())
        if output_sha != expected_output_sha:
            raise ValueError("output package SHA differs from its pinned run result")
        t0a = json.loads(t0a_path.read_text(encoding="utf-8"))
        if t0a.get("status") != "PASS" or t0a.get("source_package_sha256") != SOURCE_PACKAGE_SHA256:
            raise ValueError("T0-A report is not the pinned PASS")
        source_assets = checked_assets(source_path)
        output_assets = checked_assets(output_path)
        source_fbxs = [(guid, row) for guid, row in source_assets.items()
                       if row.get("pathname", b"").decode("utf-8-sig").strip().lower().endswith(".fbx")]
        source_prefabs = [(guid, row) for guid, row in source_assets.items()
                          if row.get("pathname", b"").decode("utf-8-sig").strip().lower().endswith(".prefab")]
        if len(source_fbxs) != 1 or len(source_prefabs) != 1:
            raise ValueError("source fixture must have exactly one FBX and one Prefab")
        if sha256(source_fbxs[0][1]["asset"]) != SOURCE_FBX_SHA256 or sha256(source_fbxs[0][1]["asset.meta"]) != SOURCE_FBXMETA_SHA256:
            raise ValueError("fixed source FBX or meta SHA mismatch")
        refs = prefab_material_refs(source_prefabs[0][1]["asset"])
        if [{"guid": row["guid"], "file_id": row["file_id"]} for row in refs] != t0a.get("expected_material_refs"):
            raise ValueError("source raw Prefab refs differ from pinned T0-A expected identities")
        closure = assert_closure(source_assets, output_assets, refs)
        generated_path = run_dir / "generated.fbx"
        generated_path.write_bytes(closure.pop("generated_fbx_bytes"))

        negative_path = run_dir / "negative-missing-material.unitypackage"
        missing_guid = refs[0]["guid"]
        write_negative_missing_material(output_path, negative_path, missing_guid)
        try:
            negative_assets = checked_assets(negative_path)
            assert_closure(source_assets, negative_assets, refs)
        except ValueError as error:
            if f"missing expected Material GUID {missing_guid}" not in str(error):
                raise ValueError("negative control failed for an unexpected reason: " + str(error))
            negative_control = {"status": "PASS", "expected_missing_guid": missing_guid,
                                "failure": str(error), "negative_package_sha256": sha256(negative_path.read_bytes())}
        else:
            raise AssertionError("negative control unexpectedly passed without required Material")
        report.update({"status": "PASS", "source_package_sha256": SOURCE_PACKAGE_SHA256,
                       "output_package_sha256": output_sha, "source_fbx_sha256": SOURCE_FBX_SHA256,
                       "source_fbx_meta_sha256": SOURCE_FBXMETA_SHA256,
                       "raw_prefab_material_refs": refs, "closure": closure,
                       "negative_control": negative_control,
                       "generated_fbx_path": str(generated_path),
                       "generated_fbx_path_sha256": closure["generated_fbx_sha256"]})
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_exclusive(result_path, json.dumps(report, indent=2, sort_keys=True))
    print("T0_C_PACKAGE_CLOSURE_" + report["status"] + " " + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS":
        raise RuntimeError(report.get("error", "T0-C closure failed"))


if __name__ == "__main__":
    main()
