"""Material reference resolution independent of Blender's data API."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Optional

from .asset_database import AssetDatabase, AssetEntry


_MATERIAL_SUFFIX_RE = re.compile(r"\.\d{3,}$")
_GUID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_INT64_MIN = -(1 << 63)
_INT64_MAX = (1 << 63) - 1


@dataclass(frozen=True)
class ExternalObjectRow:
    """Lossless-enough, ordered representation of one Unity externalObjects row.

    Raw values are serialized scalar tokens (with surrounding YAML quotes retained).
    Parsed identity fields are populated only after strict validation.
    """

    row_index: int
    row_identity: str
    raw_row: str
    raw_first_type: Optional[str]
    raw_first_assembly: Optional[str]
    raw_first_name: Optional[str]
    raw_second_file_id: Optional[str]
    raw_second_guid: Optional[str]
    raw_second_type: Optional[str]
    canonical_name: Optional[str]
    canonical_first_type: Optional[str]
    canonical_guid: Optional[str]
    canonical_file_id: Optional[int]
    canonical_second_type: Optional[int]
    row_status: str
    validation_status: str
    ambiguous: bool = False


def _inline_fields(value: str) -> tuple[dict[str, str], bool]:
    """Parse a flat inline mapping without treating quoted text as syntax."""
    body = value.strip()
    if not (body.startswith("{") and body.endswith("}")):
        return {}, True
    body = body[1:-1]
    parts: list[str] = []
    start = 0
    quote: Optional[str] = None
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = None
            escaped = False
        elif char in {"'", '"'}:
            quote = char
        elif char == ",":
            parts.append(body[start:index])
            start = index + 1
    if quote:
        return {}, True
    parts.append(body[start:])
    fields: dict[str, str] = {}
    duplicate = False
    for part in parts:
        if not part.strip():
            continue
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", part, re.S)
        if not match:
            return fields, True
        key, scalar = match.groups()
        if key in fields:
            duplicate = True
        fields[key] = scalar
    return fields, duplicate


def _block_fields(lines: list[tuple[int, str]], parent_indent: int) -> tuple[dict[str, str], bool]:
    fields: dict[str, str] = {}
    malformed = False
    direct_indent: Optional[int] = None
    for indent, content in lines:
        if not content.strip() or content.lstrip().startswith("#"):
            continue
        if indent <= parent_indent:
            continue
        if direct_indent is None:
            direct_indent = indent
        if indent != direct_indent:
            malformed = True
            continue
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", content, re.S)
        if not match:
            malformed = True
            continue
        key, scalar = match.groups()
        if key in fields:
            malformed = True
        fields[key] = scalar
    return fields, malformed


def _mapping_fields(value: str, child_lines: list[tuple[int, str]], parent_indent: int) -> tuple[dict[str, str], bool]:
    if value.strip().startswith("{"):
        fields, malformed = _inline_fields(value)
        if child_lines:
            malformed = True
        return fields, malformed
    if value.strip():
        # A scalar where the contract requires a mapping is invalid.
        return {}, True
    return _block_fields(child_lines, parent_indent)


def _yaml_text(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    value = raw.strip()
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1].replace("''", "'")
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        # JSON string decoding handles escaped quotes and backslashes.
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, str) else None
        except (ValueError, TypeError):
            return None
    return value


def _strict_int64(raw: Optional[str]) -> Optional[int]:
    if raw is None or raw[:1] in {"'", '"'}:
        return None
    value = raw.strip()
    if value is None or not _INT_RE.fullmatch(value):
        return None
    number = int(value)
    return number if _INT64_MIN <= number <= _INT64_MAX else None


def parse_external_object_rows(meta_text: str) -> list[ExternalObjectRow]:
    """Parse ordered externalObjects rows while retaining raw serialized identity.

    This intentionally handles Unity's common block and inline mapping forms
    without treating arbitrary YAML elsewhere in the .meta file as a mapping.
    """
    lines = meta_text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"^\s*externalObjects\s*:\s*(?:#.*)?$", line)), None)
    if start is None:
        return []
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() and not line.lstrip().startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                end = i
                break
    region = lines[start + 1:end]
    starts = [i for i, line in enumerate(region)
              if re.match(r"^\s*-\s*first\s*:", line)]
    rows: list[ExternalObjectRow] = []
    for index, row_start in enumerate(starts):
        head_indent = len(region[row_start]) - len(region[row_start].lstrip())
        row_end = len(region)
        for cursor in range(row_start + 1, len(region)):
            line = region[cursor]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= head_indent or (indent == head_indent and line.lstrip().startswith("-")):
                row_end = cursor
                break
        raw_lines = region[row_start:row_end]
        raw_row = "\n".join(raw_lines).rstrip()
        first_line = raw_lines[0]
        first_value = re.sub(r"^\s*-\s*first\s*:\s*", "", first_line).rstrip()
        child_pairs: list[tuple[int, str]] = []
        for line in raw_lines[1:]:
            if not line.strip() or line.lstrip().startswith("#"):
                child_pairs.append((head_indent + 1, line))
            else:
                child_pairs.append((len(line) - len(line.lstrip()), line.lstrip()))
        direct_indent = head_indent + 2
        second_entries: list[tuple[int, str, str]] = []
        first_mapping_count = 1  # The list header itself is the first mapping.
        first_children: list[tuple[int, str]] = []
        second_children: list[tuple[int, str]] = []
        current_mapping: Optional[str] = "first" if not first_value else None
        for indent, content in child_pairs:
            if indent == direct_indent:
                match = re.match(r"(first|second)\s*:\s*(.*?)\s*$", content, re.S)
                if match:
                    mapping_name, value = match.groups()
                    if mapping_name == "first":
                        first_mapping_count += 1
                        first_value = value
                        current_mapping = "first" if not value else None
                    else:
                        second_entries.append((indent, mapping_name, value))
                        current_mapping = "second" if not value else None
                    continue
            if current_mapping == "first":
                first_children.append((indent, content))
            elif current_mapping == "second":
                second_children.append((indent, content))
        first_fields, first_bad = _mapping_fields(first_value, first_children, direct_indent)
        second_value = second_entries[0][2] if second_entries else ""
        second_fields, second_bad = _mapping_fields(second_value, second_children, direct_indent)
        duplicate_mappings = sum(1 for _, name, _ in second_entries if name == "second") > 1
        duplicate_mappings = duplicate_mappings or first_mapping_count > 1
        malformed_mapping = first_bad or second_bad or duplicate_mappings or not second_entries
        first_type_raw = first_fields.get("type")
        first_name_raw = first_fields.get("name")
        first_assembly_raw = first_fields.get("assembly")
        second_file_raw = second_fields.get("fileID")
        second_guid_raw = second_fields.get("guid")
        second_type_raw = second_fields.get("type")
        name = _yaml_text(first_name_raw)
        first_type = _yaml_text(first_type_raw)
        guid_text = second_guid_raw.strip() if second_guid_raw is not None else None
        guid = guid_text.lower() if guid_text and _GUID_RE.fullmatch(guid_text) else None
        file_id = _strict_int64(second_file_raw)
        second_type_value = _strict_int64(second_type_raw)
        is_material = first_type is not None and (
            first_type in {"23", "UnityEngine:Material", "UnityEngine.Material"}
        )
        raw_identity = json.dumps(
            {"schema": "external-object-row-v1", "index": len(rows), "raw": raw_row},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        identity = "external-object-row-v1:" + hashlib.sha256(raw_identity).hexdigest()
        explicit_null = (
            file_id == 0
            and second_file_raw is not None
            and bool(_INT_RE.fullmatch(second_file_raw.strip()))
            and second_guid_raw is not None
            and second_guid_raw.strip().lower() in {"null", "~", "0" * 32}
            and second_type_raw is not None
            and second_type_value is not None
        )
        required_present = first_name_raw is not None and first_type_raw is not None and second_file_raw is not None
        if malformed_mapping:
            status = "malformed"
            validation = "malformed_mapping"
        elif explicit_null and required_present and is_material:
            status = "explicit_null"
            validation = "valid_explicit_null"
        elif required_present and is_material and guid is not None and file_id is not None and file_id != 0 and second_type_value is not None:
            status = "valid"
            validation = "valid_reference"
        else:
            status = "malformed"
            validation = "wrong_first_type" if first_type is not None and not is_material else "malformed_reference"
        rows.append(ExternalObjectRow(
            row_index=len(rows), row_identity=identity, raw_row=raw_row,
            raw_first_type=first_type_raw, raw_first_assembly=first_assembly_raw,
            raw_first_name=first_name_raw, raw_second_file_id=second_file_raw,
            raw_second_guid=second_guid_raw, raw_second_type=second_type_raw,
            canonical_name=name if name else None,
            canonical_first_type=first_type if is_material else None,
            canonical_guid=guid if status == "valid" else None,
            canonical_file_id=file_id if status in {"valid", "explicit_null"} else None,
            canonical_second_type=second_type_value if status == "valid" else None,
            row_status=status, validation_status=validation,
        ))
    counts: dict[str, int] = {}
    for row in rows:
        if row.canonical_name:
            counts[row.canonical_name] = counts.get(row.canonical_name, 0) + 1
    return [
        ExternalObjectRow(**{**row.__dict__, "ambiguous": bool(row.canonical_name and counts[row.canonical_name] > 1)})
        for row in rows
    ]


def strip_material_suffix(name: str) -> str:
    """Remove Blender/Unity duplicate suffixes such as ``.001``."""
    return _MATERIAL_SUFFIX_RE.sub("", str(name)).strip()


def parse_external_objects(meta_text: str) -> dict[str, str]:
    """Extract ModelImporter external material name -> asset GUID mappings."""
    mappings: dict[str, str] = {}
    for row in parse_external_object_rows(meta_text):
        if row.row_status == "valid" and row.canonical_name and row.canonical_guid:
            mappings[row.canonical_name] = row.canonical_guid
    return mappings


def _material_entries(asset_db: AssetDatabase) -> list[AssetEntry]:
    return sorted(
        (entry for entry in asset_db.by_guid.values() if entry.path.suffix.lower() == ".mat"),
        key=lambda entry: entry.unity_path.casefold(),
    )


def find_material_entry_by_name(
    material_name: str,
    asset_db: AssetDatabase,
) -> Optional[AssetEntry]:
    """Find a material by name only as a deterministic fallback."""
    target = strip_material_suffix(material_name).casefold()
    candidates = []
    for entry in _material_entries(asset_db):
        names = {strip_material_suffix(Path(entry.unity_path).stem).casefold()}
        try:
            text = entry.path.read_text(encoding="utf-8-sig", errors="replace")
            match = re.search(r"(?m)^\s*m_Name:\s*(.*?)\s*$", text)
            if match:
                names.add(strip_material_suffix(match.group(1).strip().strip('"\'')).casefold())
        except OSError:
            pass
        if target in names:
            candidates.append(entry)
    if len(candidates) != 1:
        return None
    return candidates[0]


def external_object_guid_for_name(
    external_objects: dict[str, str], material_name: str
) -> tuple[bool, Optional[str]]:
    """Return whether a slot is explicitly mapped and its target GUID."""
    for name in (material_name, strip_material_suffix(material_name)):
        if name in external_objects:
            return True, external_objects[name]
    return False, None


def resolve_material_entry(
    model_meta_text: str,
    material_name: str,
    asset_db: AssetDatabase,
) -> Optional[AssetEntry]:
    """Resolve a model slot using externalObjects before name matching.

    An explicit externalObjects mapping is authoritative even when its
    provider is absent or is not a Material. Name fallback is only safe when
    the model metadata did not declare an external mapping for this slot.
    """
    rows = parse_external_object_rows(model_meta_text)
    names = (material_name, strip_material_suffix(material_name))
    explicit_rows: list[ExternalObjectRow] = []
    for candidate_name in names:
        explicit_rows = [row for row in rows if row.canonical_name == candidate_name]
        if explicit_rows:
            break
    if explicit_rows:
        if len(explicit_rows) != 1:
            return None
        row = explicit_rows[0]
        if row.ambiguous or row.row_status != "valid" or not row.canonical_guid:
            return None
        entry = asset_db.find_guid(row.canonical_guid)
        if entry and entry.path.suffix.lower() == ".mat":
            return entry
        return None
    return find_material_entry_by_name(material_name, asset_db)
