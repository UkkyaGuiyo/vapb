"""Build an optional revision-bound model identity sidecar from a Unity probe.

Run inside Blender background mode so its official FBX parser is available.
The source FBX and importer meta are read from the exact UnityPackage input.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.fbx_receipt import RawFbxSemanticIndex, source_sha256
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelAssetRevision, build_model_witness_from_probe,
)
from unitypackage_blender_importer.unity.package_reader import UnityPackageReader


def build(package: Path, probe_path: Path, report_path: Path) -> dict:
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    guid = probe.get("model_guid")
    if not isinstance(guid, str):
        raise ValueError("Probe model GUID missing")
    reader = UnityPackageReader(package)
    index = reader.build_index()
    record = index.records.get(guid.lower())
    if record is None or not record.unity_path.lower().endswith(".fbx"):
        raise ValueError("Probe model is absent from the source UnityPackage")
    with tempfile.TemporaryDirectory(prefix="vapb_witness_") as temp:
        extracted = reader.extract_selective(Path(temp), index, {guid})
        if extracted.errors or len(extracted.assets) != 1:
            raise ValueError("Source model could not be extracted uniquely")
        asset = extracted.assets[0]
        if asset.meta_path is None or not asset.meta_path.is_file():
            raise ValueError("Source importer meta is missing")
        revision = ModelAssetRevision(
            source_sha256(asset.extracted_path), source_sha256(asset.meta_path),
            RawFbxSemanticIndex.from_file(asset.extracted_path),
        )
        return build_model_witness_from_probe(
            probe, report, source_sha256(package), {guid.lower(): revision},
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        document = build(args.package, args.probe, args.report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"WITNESS_REJECTED: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("WITNESS_VALIDATED")
    return 0


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    result = main(arguments)
    if result:
        raise RuntimeError("Model identity witness generation failed")
