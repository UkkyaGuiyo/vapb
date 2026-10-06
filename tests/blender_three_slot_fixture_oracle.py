"""Independent raw Unitypackage oracle for the public ThreeSlotSource fixture."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tarfile

EXPECTED_PACKAGE_SHA256 = "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c"
EXPECTED_MATERIAL_REFS = [
    {"guid": "eb805efb35118044db5e74adc652673a", "file_id": "2100000"},
    {"guid": "0318f358e4c29034aa90cc8c50b58a93", "file_id": "2100000"},
    {"guid": "64f92a1bd9b35a040bf9e2c6d200b34c", "file_id": "2100000"},
]

_ROW = re.compile(
    rb"^\s*-\s*\{\s*fileID:\s*(-?\d+)\s*,\s*guid:\s*([0-9a-fA-F]{32})\s*,\s*type:\s*\d+\s*\}\s*$"
)


def package_sha256(package_path: Path) -> str:
    return hashlib.sha256(package_path.read_bytes()).hexdigest()


def raw_prefab_material_refs(package_path: Path) -> list[dict[str, str]]:
    if package_sha256(package_path) != EXPECTED_PACKAGE_SHA256:
        raise AssertionError("fixed public fixture SHA-256 mismatch")
    with tarfile.open(package_path, "r:*") as archive:
        prefabs = []
        for member in archive.getmembers():
            parts = member.name.split("/")
            if len(parts) != 2 or parts[1] != "pathname" or not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise AssertionError("cannot read Unitypackage pathname member")
            if stream.read().decode("utf-8", errors="replace").lower().endswith(".prefab"):
                payload_member = archive.extractfile(parts[0] + "/asset")
                if payload_member is None:
                    raise AssertionError("fixture Prefab has no asset payload")
                prefabs.append(payload_member.read())
    if len(prefabs) != 1:
        raise AssertionError("fixed fixture must contain exactly one Prefab")

    refs = []
    payload = prefabs[0]
    documents = re.split(rb"(?m)^---\s*!u!\d+\s+&[^\r\n]*\r?\n", payload)
    headers = re.findall(rb"(?m)^---\s*!u!(\d+)\s+&[^\r\n]*\r?\n", payload)
    for class_id, body in zip(headers, documents[1:]):
        if class_id != b"137":
            continue
        lines = body.splitlines()
        in_materials = False
        key_indent = -1
        for line in lines:
            indent = len(line) - len(line.lstrip(b" \t"))
            stripped = line.strip()
            if not in_materials:
                if re.fullmatch(rb"m_Materials\s*:", stripped):
                    in_materials = True
                    key_indent = indent
                continue
            if not stripped:
                continue
            if stripped.startswith(b"-"):
                match = _ROW.fullmatch(stripped)
                if match is None:
                    raise AssertionError("unsupported raw Prefab Material reference")
                refs.append({"file_id": match.group(1).decode("ascii"),
                             "guid": match.group(2).decode("ascii").lower()})
                continue
            if indent <= key_indent:
                break
    if refs != EXPECTED_MATERIAL_REFS:
        raise AssertionError("raw Prefab Material refs differ from the fixed fixture oracle")
    return refs
