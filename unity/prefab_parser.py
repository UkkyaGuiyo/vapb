"""Extract the useful GameObject/Transform/Renderer subset from Unity YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Optional

from .yaml_parser import UnityYAMLDocument, parse_unity_yaml


GAME_OBJECT = 1
TRANSFORM = 4
MESH_RENDERER = 23
MESH_FILTER = 33
SKINNED_MESH_RENDERER = 137


def ref_file_id(value: Any) -> Optional[int]:
    if isinstance(value, dict) and "fileID" in value:
        try:
            return int(value["fileID"])
        except (TypeError, ValueError):
            return None
    return None


def ref_guid(value: Any) -> Optional[str]:
    return str(value["guid"]) if isinstance(value, dict) and value.get("guid") else None


@dataclass
class PrefabGameObject:
    file_id: int
    name: str
    component_ids: list[int] = field(default_factory=list)


@dataclass
class PrefabTransform:
    file_id: int
    game_object_id: Optional[int]
    parent_id: Optional[int]
    position: dict[str, float]
    rotation: dict[str, float]
    scale: dict[str, float]


@dataclass
class PrefabData:
    path: Path
    documents: list[UnityYAMLDocument]
    game_objects: dict[int, PrefabGameObject]
    transforms: dict[int, PrefabTransform]

    @property
    def display_name(self) -> str:
        return next(iter(self.game_objects.values())).name if self.game_objects else self.path.stem

    def renderer_documents(self) -> list[UnityYAMLDocument]:
        return [d for d in self.documents if d.class_id in {MESH_RENDERER, SKINNED_MESH_RENDERER}]

    def mesh_filter_documents(self) -> list[UnityYAMLDocument]:
        return [d for d in self.documents if d.class_id == MESH_FILTER]

    def modification_materials(self) -> list[dict[str, Any]]:
        """Read PrefabInstance material overrides with wrapped Unity refs.

        Unity commonly wraps the ``guid`` and ``type`` fields over multiple
        lines.  The generic YAML subset parser intentionally does not attempt
        to model this editor serialization, so use a narrow parser for the
        exact override records we need and refuse incomplete records.
        """
        result: list[dict[str, Any]] = []
        for document in self.documents:
            if document.class_id != 1001:
                continue
            chunks = re.split(r"\n\s*- target:\s*", document.raw)
            names: dict[str, str] = {}
            material_chunks: list[tuple[str, str]] = []
            for chunk in chunks[1:]:
                target = re.match(r"\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]{32})", chunk)
                if not target:
                    continue
                target_file_id, target_guid = target.groups()
                name_value = re.search(r"propertyPath:\s*m_Name\s*\n\s*value:\s*(.+)", chunk)
                if name_value:
                    names[target_file_id] = name_value.group(1).strip()
                material = re.search(
                    r"propertyPath:\s*m_Materials\.Array\.data\[(\d+)\].*?"
                    r"objectReference:\s*\{fileID:\s*-?\d+,\s*guid:\s*([0-9a-fA-F]{32})",
                    chunk,
                    re.DOTALL,
                )
                if material:
                    material_chunks.append((target_file_id, target_guid, material.group(1), material.group(2)))
            for target_file_id, target_guid, slot_index, material_guid in material_chunks:
                result.append({
                    "target_file_id": target_file_id,
                    "target_source_guid": target_guid.lower(),
                    "slot_index": int(slot_index),
                    "material_guid": material_guid.lower(),
                    "object_name": names.get(target_file_id, ""),
                })
        return result

    def referenced_fbx_guids(self) -> set[str]:
        guids: set[str] = set()
        for doc in self.renderer_documents() + self.mesh_filter_documents():
            for key in ("m_Mesh", "m_Materials", "m_Material"):
                value = doc.data.get(key)
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, dict):
                        guid = ref_guid(item) or ref_guid(item.get("material"))
                        if guid:
                            guids.add(guid.lower())
        return guids

    def referenced_nested_prefab_guids(self) -> set[str]:
        guids: set[str] = set()
        for document in self.documents:
            if document.class_id != 1001:
                continue
            for guid in re.findall(r"m_SourcePrefab:.*?guid:\s*([0-9a-fA-F]{32})", document.raw, re.DOTALL):
                guids.add(guid.lower())
        return guids


def parse_prefab(path: Path) -> PrefabData:
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    documents = parse_unity_yaml(text)
    game_objects: dict[int, PrefabGameObject] = {}
    transforms: dict[int, PrefabTransform] = {}
    for document in documents:
        if document.class_id == GAME_OBJECT:
            component_ids: list[int] = []
            components = document.data.get("m_Component") or []
            for component in components if isinstance(components, list) else []:
                if isinstance(component, dict):
                    component_id = ref_file_id(component.get("component"))
                    if component_id is not None:
                        component_ids.append(component_id)
            game_objects[document.file_id] = PrefabGameObject(
                document.file_id,
                str(document.data.get("m_Name") or f"GameObject_{document.file_id}"),
                component_ids,
            )
        elif document.class_id == TRANSFORM:
            position = document.data.get("m_LocalPosition") or {}
            rotation = document.data.get("m_LocalRotation") or {}
            scale = document.data.get("m_LocalScale") or {}
            transforms[document.file_id] = PrefabTransform(
                document.file_id,
                ref_file_id(document.data.get("m_GameObject")),
                ref_file_id(document.data.get("m_Father")),
                {axis: float(position.get(axis, 0.0)) for axis in ("x", "y", "z")},
                {axis: float(rotation.get(axis, 0.0)) for axis in ("x", "y", "z", "w")},
                {axis: float(scale.get(axis, 1.0)) for axis in ("x", "y", "z")},
            )
    return PrefabData(Path(path), documents, game_objects, transforms)
