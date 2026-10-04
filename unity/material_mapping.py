"""Material reference resolution independent of Blender's data API."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from .asset_database import AssetDatabase, AssetEntry


_MATERIAL_SUFFIX_RE = re.compile(r"\.\d{3,}$")


def strip_material_suffix(name: str) -> str:
    """Remove Blender/Unity duplicate suffixes such as ``.001``."""
    return _MATERIAL_SUFFIX_RE.sub("", str(name)).strip()


def parse_external_objects(meta_text: str) -> dict[str, str]:
    """Extract ModelImporter external material name -> asset GUID mappings."""
    mappings: dict[str, str] = {}
    chunks = re.split(r"(?m)^\s*-\s*first:\s*", meta_text)
    for chunk in chunks[1:]:
        name_match = re.search(r"(?m)^\s*name:\s*(.*?)\s*$", chunk)
        # Unity writes the reference as an inline mapping in current
        # ModelImporter metadata: ``second: {fileID: ..., guid: ..., type: 2}``.
        # Older exports may put ``guid`` on its own line, so accept both forms.
        guid_match = re.search(r"\bguid:\s*([0-9a-fA-F]+)", chunk)
        if not name_match or not guid_match:
            continue
        name = name_match.group(1).strip().strip('"\'')
        if name:
            mappings[name] = guid_match.group(1).lower()
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
    external = parse_external_objects(model_meta_text)
    mapped, guid = external_object_guid_for_name(external, material_name)
    if mapped:
        entry = asset_db.find_guid(guid)
        if entry and entry.path.suffix.lower() == ".mat":
            return entry
        return None
    return find_material_entry_by_name(material_name, asset_db)
