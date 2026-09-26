"""Pure-Python material binding manifest generation for Blender export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .renderer_binding import BindingError, validate_existing_binding


SCHEMA_VERSION = 1
MANIFEST_TYPE = "unitypackage_blender_material_map"


def sidecar_path(fbx_path: Path) -> Path:
    fbx_path = Path(fbx_path)
    return fbx_path.with_name(f"{fbx_path.stem}.materialmap.json")


def _prop(material: Any, key: str, default: str = "") -> str:
    try:
        value = material.get(key, default)
    except AttributeError:
        value = default
    return "" if value is None else str(value)


def _object_path(obj: Any) -> str:
    names: list[str] = []
    current = obj
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        names.append(str(getattr(current, "name", "Object")))
        current = getattr(current, "parent", None)
    return "/".join(reversed(names))


def _renderer_type(obj: Any) -> str:
    for modifier in getattr(obj, "modifiers", ()) or ():
        if getattr(modifier, "type", "") == "ARMATURE":
            return "SkinnedMeshRenderer"
    return "MeshRenderer"


def _material_identity(material: Any) -> int:
    try:
        pointer = material.as_pointer()
        if pointer:
            return int(pointer)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        pass
    return id(material)


def _new_material_record(material: Any, material_key: str) -> dict[str, Any]:
    name = str(getattr(material, "name", "Material"))
    return {
        "material_key": material_key,
        "exported_material_identifier": name,
        "blender_material_name": name,
        "unity_material_guid": _prop(material, "unity_material_guid"),
        "unity_material_path": _prop(material, "unity_material_path"),
        "unity_material_name": _prop(material, "unity_material_name"),
        "unity_shader_guid": _prop(material, "unity_shader_guid"),
        "unity_shader_name": _prop(material, "unity_shader_name"),
    }


def build_material_manifest(objects: Iterable[Any], fbx_path: Path, *, reference_objects=None) -> dict[str, Any]:
    """Build a versioned manifest from Blender mesh objects and material slots."""
    materials: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    material_keys: dict[int, str] = {}
    used_keys: set[str] = set()
    warnings: list[str] = []
    objects = tuple(objects)
    reference_objects = tuple(reference_objects) if reference_objects is not None else objects
    renderer_bindings = []

    for obj in objects:
        raw = _prop(obj, '_vapb_renderer_binding')
        if not raw:
            continue
        try:
            binding = json.loads(raw)
            roots = [root for root in reference_objects
                     if _prop(root, '_vapb_root_context_id') == binding.get('root_context_id')
                     and _prop(root, '_vapb_renderer_occurrences')]
            if len(roots) != 1:
                raise BindingError('Renderer binding root is missing or ambiguous')
            renderer_bindings.append(validate_existing_binding(binding, roots[0], obj, reference_objects))
        except (TypeError, AttributeError, ValueError) as exc:
            raise ValueError('Confirmed Renderer binding is no longer valid; resolve it before export') from exc

    for obj in objects:
        data = getattr(obj, "data", None)
        slots = getattr(data, "materials", None) if data is not None else None
        if slots is None:
            continue
        object_slots = getattr(obj, "material_slots", None)
        if object_slots is not None:
            slots = [slot.material for slot in object_slots]
        object_path = _object_path(obj)
        renderer_type = _renderer_type(obj)
        for slot_index, material in enumerate(slots):
            if material is None:
                bindings.append(
                    {
                        "object_name": str(getattr(obj, "name", "Object")),
                        "object_path": object_path,
                        "renderer_type": renderer_type,
                        "material_slot_index": slot_index,
                        "material_key": "",
                        "exported_material_identifier": "",
                        "status": "empty_slot",
                    }
                )
                continue

            identity = _material_identity(material)
            material_key = material_keys.get(identity)
            if material_key is None:
                guid = _prop(material, "unity_material_guid").lower()
                if guid:
                    base_key = f"unity-guid:{guid}"
                else:
                    base_key = f"blender-material:{len(materials):04d}:{getattr(material, 'name', 'Material')}"
                material_key = base_key
                duplicate_index = 2
                while material_key in used_keys:
                    material_key = f"{base_key}:{duplicate_index}"
                    duplicate_index += 1
                material_keys[identity] = material_key
                used_keys.add(material_key)
                materials.append(_new_material_record(material, material_key))
                if not guid:
                    warnings.append(f"Material has no Unity GUID: {getattr(material, 'name', 'Material')}")

            material_record = next(item for item in materials if item["material_key"] == material_key)
            bindings.append(
                {
                    "object_name": str(getattr(obj, "name", "Object")),
                    "object_path": object_path,
                    "renderer_type": renderer_type,
                    "material_slot_index": slot_index,
                    "material_key": material_key,
                    "exported_material_identifier": material_record["exported_material_identifier"],
                    "status": "mapped" if material_record["unity_material_guid"] else "metadata_missing",
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_type": MANIFEST_TYPE,
        "fbx_file": Path(fbx_path).name,
        "materials": materials,
        "bindings": bindings,
        "renderer_bindings": renderer_bindings,
        "warnings": warnings,
    }


def write_material_manifest(objects: Iterable[Any], fbx_path: Path, manifest: dict[str, Any] | None = None) -> Path:
    output = sidecar_path(fbx_path)
    manifest = manifest or build_material_manifest(objects, fbx_path)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
