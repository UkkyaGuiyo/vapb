"""Extract the useful GameObject/Transform/Renderer subset from Unity YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Optional

from .yaml_parser import UnityYAMLDocument, parse_unity_yaml
from ..blender.performance import diagnostic_add


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


@dataclass(frozen=True)
class PrefabModification:
    """Lossless semantic subset of one Unity PrefabInstance modification."""
    target_file_id: int
    target_guid: str
    target_type: int | None
    property_path: str
    value: Any = None
    object_reference: dict[str, Any] | None = None
    raw: str = ""


@dataclass
class PrefabData:
    path: Path
    documents: list[UnityYAMLDocument]
    game_objects: dict[int, PrefabGameObject]
    transforms: dict[int, PrefabTransform]
    asset_guid: str = ""

    @property
    def display_name(self) -> str:
        roots = self.root_game_objects()
        if len(roots) == 1:
            return roots[0].name
        return self.path.stem

    @property
    def asset_identity(self) -> str:
        """Return the owning Prefab asset identity when its meta is available."""
        return self.asset_guid.lower() or str(self.path).replace("\\", "/")

    def root_game_objects(self) -> list[PrefabGameObject]:
        root_ids = {
            transform.game_object_id
            for transform in self.transforms.values()
            if transform.game_object_id is not None and transform.parent_id in (None, 0)
        }
        return [self.game_objects[item] for item in root_ids if item in self.game_objects]

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
        names = {
            str(item.target_file_id): str(item.value)
            for item in self.modifications()
            if item.property_path == "m_Name" and item.value is not None
        }
        result = []
        for item in self.modifications():
            match = re.fullmatch(r"m_Materials\.Array\.data\[(\d+)\]", item.property_path)
            if not match or not item.object_reference:
                continue
            result.append({
                "target_file_id": str(item.target_file_id),
                "target_source_guid": item.target_guid,
                "slot_index": int(match.group(1)),
                "material_guid": ref_guid(item.object_reference),
                "object_name": names.get(str(item.target_file_id), ""),
            })
        return result

    def modifications(self) -> list[PrefabModification]:
        result: list[PrefabModification] = []
        for document in self.documents:
            if document.class_id != 1001:
                continue
            chunks = re.split(r"\n\s*- target:\s*", document.raw)
            for chunk in chunks[1:]:
                target = re.search(
                    r"\{\s*fileID:\s*(-?\d+).*?guid:\s*([0-9a-fA-F]{32}).*?(?:type:\s*(-?\d+))?\s*\}",
                    chunk, re.DOTALL,
                )
                prop = re.search(r"propertyPath:\s*([^\n]+)", chunk)
                if not target or not prop:
                    continue
                value_match = re.search(r"\n\s*value:\s*(.*?)(?=\n\s*objectReference:|\n\s*- target:|\Z)", chunk, re.DOTALL)
                ref_match = re.search(
                    r"objectReference:\s*\{\s*fileID:\s*(-?\d+).*?guid:\s*([0-9a-fA-F]{32}).*?(?:type:\s*(-?\d+))?\s*\}",
                    chunk, re.DOTALL,
                )
                reference = None
                if ref_match:
                    reference = {"fileID": int(ref_match.group(1)), "guid": ref_match.group(2).lower()}
                    if ref_match.group(3) is not None:
                        reference["type"] = int(ref_match.group(3))
                result.append(PrefabModification(
                    int(target.group(1)), target.group(2).lower(), int(target.group(3)) if target.group(3) else None,
                    prop.group(1).strip(), (value_match.group(1).strip() if value_match else None), reference, chunk,
                ))
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
        # Variant visual state is serialized as modifications on the source
        # renderer, not as direct renderer documents in the variant file.
        for modification in self.modifications():
            if modification.property_path.startswith("m_Materials.Array.data["):
                guids.add(modification.target_guid.lower())
            if modification.object_reference and modification.property_path.startswith("m_Materials.Array.data["):
                guids.discard(ref_guid(modification.object_reference) or "")
        return guids

    def referenced_nested_prefab_guids(self) -> set[str]:
        guids: set[str] = set()
        for document in self.documents:
            if document.class_id != 1001:
                continue
            for guid in re.findall(r"m_SourcePrefab:.*?guid:\s*([0-9a-fA-F]{32})", document.raw, re.DOTALL):
                guids.add(guid.lower())
        return guids

    def effective_material_bindings(self) -> dict[tuple[str, int, int], str]:
        """Return effective material bindings keyed by source renderer identity.

        This is intentionally a derived view.  ``modifications()`` remains the
        preserved raw source record and is never mutated.
        """
        result: dict[tuple[str, int, int], str] = {}
        for document in self.renderer_documents():
            source_guid = None
            mesh = document.data.get("m_Mesh")
            if isinstance(mesh, dict):
                source_guid = ref_guid(mesh)
            if not source_guid:
                continue
            # A direct renderer document belongs to this Prefab asset even
            # when its geometry comes from an external Model asset.  When a
            # .meta file is unavailable (for example a minimal fixture), the
            # mesh GUID remains an explicitly unscoped compatibility
            # fallback, never the authoritative renderer identity.
            renderer_guid = self.asset_guid or source_guid
            values = document.data.get("m_Materials")
            if values is None:
                values = [document.data.get("m_Material")]
            if not isinstance(values, list):
                values = [values]
            for slot, value in enumerate(values):
                material_guid = ref_guid(value)
                if material_guid:
                    result[(renderer_guid.lower(), document.file_id, slot)] = material_guid.lower()
        for modification in self.modifications():
            match = re.fullmatch(r"m_Materials\.Array\.data\[(\d+)\]", modification.property_path)
            material_guid = ref_guid(modification.object_reference) if modification.object_reference else None
            if match and material_guid:
                result[(modification.target_guid, modification.target_file_id, int(match.group(1)))] = material_guid.lower()
        return result


def parse_prefab(path: Path) -> PrefabData:
    diagnostic_add("prefab_parse_calls")
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
    asset_guid = ""
    meta_path = Path(path).with_name(Path(path).name + ".meta")
    try:
        meta_text = meta_path.read_text(encoding="utf-8-sig", errors="replace")
        match = re.search(r"(?m)^guid:\s*([0-9a-fA-F]{32})\s*$", meta_text)
        if match:
            asset_guid = match.group(1).lower()
    except OSError:
        pass
    return PrefabData(Path(path), documents, game_objects, transforms, asset_guid)
