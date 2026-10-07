from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(data: bytes):
    pattern = re.compile(rb"(?i)[A-Z]:\\")
    path_lengths = []
    sanitized = bytearray(data)

    def replacement(match):
        start = match.start()
        if start < 5 or data[start - 5] != ord("S"):
            raise ValueError("absolute path is not an FBX string property")
        length = struct.unpack("<I", data[start - 4:start])[0]
        end = start + length
        if not length or end > len(data):
            raise ValueError("invalid FBX string length")
        value = data[start:end]
        if b"\x00" in value or not value.lower().endswith((b".blend", b".mat")):
            raise ValueError("unexpected absolute FBX string property")
        path_lengths.append(length)
        label = b"VAPB_REDACTED_PATH_"
        if len(label) > length:
            raise ValueError("path string is shorter than neutral label")
        sanitized[start:end] = label + b"X" * (length - len(label))

    for match in list(pattern.finditer(data)):
        replacement(match)
    return bytes(sanitized), path_lengths


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise SystemExit("input_fbx output_fbx report_json")
    src, dst, report_path = map(Path, args)
    original = src.read_bytes()
    sanitized, path_lengths = redact(original)
    if not path_lengths:
        raise AssertionError("no absolute path strings found to redact")
    if sanitized == original:
        raise AssertionError("redaction did not change the artifact")
    with dst.open("xb") as stream:
        stream.write(sanitized)
    report = {
        "status": "PASS",
        "artifact_kind": "same-length FBX path-redacted copy; not the original exporter bytes",
        "original_sha256": sha(original),
        "sanitized_copy_sha256": sha(sanitized),
        "absolute_path_strings_redacted": len(path_lengths),
        "redacted_string_lengths_bytes": path_lengths,
        "file_length_unchanged": len(original) == len(sanitized),
        "only_matched_fbx_string_property_payload_bytes_changed": len(original) == len(sanitized) and
            redact(original)[0] == sanitized,
    }
    if not report["only_matched_fbx_string_property_payload_bytes_changed"]:
        raise AssertionError("non-path bytes changed")
    with report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(report, sort_keys=True))


main()
