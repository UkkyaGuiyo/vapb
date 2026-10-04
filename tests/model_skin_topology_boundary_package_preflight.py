"""Validate an ordinary model-skin unitypackage before importing into TargetProject."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile


ROOT_MARKER = ".vapb-stage3-owned-test-root"
TARGET_MARKER = ".vapb-disposable-unity-test-project"
ROOT_VALUE = "VAPB_STAGE3_OWNED_TEST_ROOT_V1"
APPROVED_PACKAGE_SHA256 = "157eee6379cc435ad9829db2011c1dabeb6f44259d97c385d6e47e3c2db8da73"
EXPECTED_PACKAGE_PATHS = {
    "Assets/VAPBExport/manifest.json",
    "Assets/VAPBExport/EditedSkin_defd390bf9c2aaf30f387716c927c40a.fbx",
    "Assets/VAPBExport/VapbRealizationMarker.cs",
    "Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs",
    "Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs",
    "Assets/VAPBExport/Editor/VapbSkinWeightImporter.cs",
    "Assets/VAPBExport/SkinWeightPolicy_defd390bf9c2aaf30f387716c927c40a.json",
    "Assets/VAPBExport/Witness_defd390bf9c2aaf30f387716c927c40a_Noop.bytes",
    "Assets/VAPBExport/Witness_defd390bf9c2aaf30f387716c927c40a_Source.bytes",
    "Assets/VapbSkinRoundtrip/Avatar.prefab",
    "Assets/VapbSkinRoundtrip/Input.fbx",
    "Assets/VapbSkinRoundtrip/Original.mat",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def no_reparse(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise ValueError(f"REPARSE_PATH:{current}")
        if current.exists() and getattr(current.stat(), "st_file_attributes", 0) & 0x400:
            raise ValueError(f"REPARSE_PATH:{current}")


def _unitypackage_assets(package: Path) -> list[dict]:
    grouped: dict[str, dict[str, bytes]] = {}
    with tarfile.open(package, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            bits = PurePosixPath(member.name).parts
            if len(bits) != 2:
                raise ValueError(f"PACKAGE_MEMBER_SHAPE_INVALID:{member.name}")
            guid, leaf = bits
            if not re.fullmatch(r"[0-9a-fA-F]{32}", guid) or leaf not in {"pathname", "asset", "asset.meta", "preview.png"}:
                raise ValueError(f"PACKAGE_MEMBER_INVALID:{member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"PACKAGE_MEMBER_UNREADABLE:{member.name}")
            members = grouped.setdefault(guid.lower(), {})
            if leaf in members:
                raise ValueError(f"PACKAGE_MEMBER_DUPLICATE:{member.name}")
            members[leaf] = stream.read()
    rows, paths = [], set()
    for guid, members in grouped.items():
        if not {"pathname", "asset", "asset.meta"}.issubset(members):
            raise ValueError(f"PACKAGE_ASSET_INCOMPLETE:{guid}")
        raw = members["pathname"].decode("utf-8-sig").strip()
        path = PurePosixPath(raw)
        if (not raw.startswith("Assets/") or "\\" in raw or ":" in raw or
                any(piece in {"", ".", ".."} for piece in raw.split("/"))):
            raise ValueError(f"PACKAGE_PATH_INVALID:{raw}")
        key = raw.casefold()
        if key in paths:
            raise ValueError(f"PACKAGE_PATH_COLLISION:{raw}")
        paths.add(key)
        meta = members["asset.meta"].decode("utf-8-sig", errors="strict")
        match = re.search(r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", meta)
        if not match or match.group(1).lower() != guid:
            raise ValueError(f"PACKAGE_GUID_META_MISMATCH:{raw}")
        rows.append({"guid": guid, "path": raw, "asset_sha256": sha(members["asset"]),
                     "meta_sha256": sha(members["asset.meta"]), "asset": members["asset"]})
    return rows


def run(root: Path) -> dict:
    requested_root = Path(os.path.abspath(root))
    no_reparse(requested_root)
    root = requested_root.resolve(strict=True)
    target = root / "TargetProject"
    package = root / "ModelSkinEvidence" / "Output.unitypackage"
    source_evidence = root / "ModelSkinEvidence" / "TopologyBoundaryEvidence.json"
    output = root / "OutputPackageInventory.json"
    for path in (root, target, package, source_evidence, root / ROOT_MARKER,
                 target / TARGET_MARKER, output):
        no_reparse(path)
    if (not (root / ROOT_MARKER).is_file() or
            (root / ROOT_MARKER).read_text(encoding="utf-8").strip() != ROOT_VALUE or
            not (target / TARGET_MARKER).is_file() or
            (target / TARGET_MARKER).read_text(encoding="utf-8").strip() != "" or
            "m_EditorVersion: 2022.3.22f1" not in
            (target / "ProjectSettings/ProjectVersion.txt").read_text(encoding="utf-8")):
        raise ValueError("OWNERSHIP_OR_UNITY_VERSION_INVALID")
    package_hash = sha(package.read_bytes())
    if package_hash != APPROVED_PACKAGE_SHA256:
        raise ValueError("PACKAGE_HASH_NOT_APPROVED_FOR_THIS_FIXTURE")
    rows = _unitypackage_assets(package)
    by_path = {row["path"]: row for row in rows}
    actual_paths = set(by_path)
    if actual_paths != EXPECTED_PACKAGE_PATHS:
        raise ValueError("PACKAGE_PATH_SET_MISMATCH:" + json.dumps({
            "missing": sorted(EXPECTED_PACKAGE_PATHS - actual_paths),
            "extra": sorted(actual_paths - EXPECTED_PACKAGE_PATHS),
        }, sort_keys=True))
    helpers = {
        "Assets/VAPBExport/VapbRealizationMarker.cs": "VapbRealizationMarker.cs",
        "Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs": "Editor/VapbReferenceFinalizer.cs",
        "Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs": "Editor/VapbModelSkinFinalizer.cs",
        "Assets/VAPBExport/Editor/VapbSkinWeightImporter.cs": "Editor/VapbSkinWeightImporter.cs",
    }
    repo = Path(__file__).resolve().parents[1]
    for asset_path, source_relative in helpers.items():
        if by_path[asset_path]["asset_sha256"] != sha((repo / "unity_editor" / source_relative).read_bytes()):
            raise ValueError(f"PRODUCT_HELPER_PAYLOAD_MISMATCH:{asset_path}")
    for row in rows:
        destination = target.joinpath(*PurePosixPath(row["path"]).parts)
        if destination.exists() or destination.is_symlink() or Path(str(destination) + ".meta").exists():
            raise ValueError(f"TARGET_PATH_COLLISION:{row['path']}")
    existing_guids = {}
    assets_root = target / "Assets"
    no_reparse(assets_root)
    for current, directories, filenames in os.walk(assets_root, followlinks=False):
        current_path = Path(current)
        kept = []
        for name in directories:
            child = current_path / name
            no_reparse(child)
            if not child.is_symlink():
                kept.append(name)
        directories[:] = kept
        for name in filenames:
            if not name.endswith(".meta"):
                continue
            meta_path = current_path / name
            no_reparse(meta_path)
            try:
                match = re.search(r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$",
                                 meta_path.read_text(encoding="utf-8-sig", errors="strict"))
            except UnicodeError:
                continue
            if match:
                existing_guids[match.group(1).lower()] = str(meta_path)
    for row in rows:
        if row["guid"] in existing_guids:
            raise ValueError(f"TARGET_GUID_COLLISION:{row['guid']}:{existing_guids[row['guid']]}")
    manifest = json.loads(by_path["Assets/VAPBExport/manifest.json"]["asset"].decode("utf-8-sig"))
    tasks = manifest.get("reference_rebind_tasks")
    if not isinstance(tasks, list) or len(tasks) != 1 or tasks[0].get("kind") != "RESTORE_MODEL_SKIN_VARIANT_V1":
        raise ValueError("NORMAL_MODEL_SKIN_TASK_REQUIRED")
    evidence = json.loads(source_evidence.read_text(encoding="utf-8-sig"))
    report = {
        "pass": True, "package_sha256": package_hash, "asset_count": len(rows),
        "task_kind": tasks[0]["kind"], "task_count": len(tasks),
        "fixture_contract": evidence, "assets": [
            {key: value for key, value in row.items() if key != "asset"} for row in rows],
    }
    with output.open("xb") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True).encode("utf-8"))
    return report


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if len(arguments) != 1:
        raise SystemExit("usage: model_skin_topology_boundary_package_preflight.py -- <run-root>")
    result = run(Path(arguments[0]))
    print("MODEL_SKIN_TOPOLOGY_PACKAGE_PREFLIGHT_PASS " + json.dumps({
        "package_sha256": result["package_sha256"], "asset_count": result["asset_count"],
        "task_kind": result["task_kind"], "task_count": result["task_count"],
    }, sort_keys=True))
