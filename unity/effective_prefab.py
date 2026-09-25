"""Derived effective Prefab state, independent of Unity YAML serialization shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .prefab_parser import PrefabData, PrefabModification, ref_file_id


@dataclass(frozen=True)
class PrefabOccurrenceIdentity:
    asset_guid: str
    asset_path: str


@dataclass(frozen=True)
class RendererSemanticID:
    asset_guid: str
    file_id: int


@dataclass(frozen=True)
class MeshSemanticID:
    asset_guid: str
    file_id: int | None


@dataclass(frozen=True)
class ModelSourceRecord:
    """Semantic relation for one source-model Renderer component.

    The three local IDs are deliberately independent.  Unity model assets
    commonly use different file IDs for Renderer, owner GameObject, and Mesh.
    """

    source_guid: str
    renderer_file_id: int
    renderer_type: int
    owner_game_object_id: int
    mesh_guid: str
    mesh_file_id: int | None
    transform_id: int | None = None
    evidence: str = "EXACT"


@dataclass(frozen=True)
class ModelSourceLookup:
    record: ModelSourceRecord | None
    evidence: str


class ModelSourceSemanticIndex:
    """Fail-closed index for explicit model Renderer provenance.

    This index accepts only serialized semantic relations.  It never falls
    back to names, order, or a first matching object.  Duplicate keys remain
    ambiguous so callers cannot accidentally bind a wrong occurrence.
    """

    def __init__(self, records: Iterable[ModelSourceRecord] = ()):
        self._records: dict[tuple[str, int], list[ModelSourceRecord]] = {}
        for record in records:
            self.add(record)

    def add(self, record: ModelSourceRecord) -> None:
        key = (str(record.source_guid).lower(), int(record.renderer_file_id))
        self._records.setdefault(key, []).append(record)

    def lookup(self, source_guid: str, renderer_file_id: int) -> ModelSourceLookup:
        candidates = self._records.get((str(source_guid).lower(), int(renderer_file_id)), [])
        if not candidates:
            return ModelSourceLookup(None, "UNKNOWN")
        if len(candidates) != 1:
            return ModelSourceLookup(None, "AMBIGUOUS")
        record = candidates[0]
        return ModelSourceLookup(record, str(record.evidence or "EXACT"))

    @classmethod
    def from_prefabs(cls, prefabs: Iterable[PrefabData]) -> "ModelSourceSemanticIndex":
        """Build relations from parsed YAML model-like sources when present.

        Binary FBX files do not expose Unity's generated local IDs to this
        parser.  They therefore produce no synthetic relation here; callers
        must provide an explicit source relation instead of guessing.
        """
        index = cls()
        for prefab in prefabs:
            if not prefab.asset_guid:
                continue
            mesh_by_owner = {
                ref_file_id(document.data.get("m_GameObject")): document.data.get("m_Mesh")
                for document in prefab.mesh_filter_documents()
                if ref_file_id(document.data.get("m_GameObject")) is not None
                and isinstance(document.data.get("m_Mesh"), dict)
                and document.data["m_Mesh"].get("guid")
            }
            transform_by_owner = {
                transform.game_object_id: transform.file_id
                for transform in prefab.transforms.values()
                if transform.game_object_id is not None
            }
            for document in prefab.renderer_documents():
                owner_id = ref_file_id(document.data.get("m_GameObject"))
                mesh = document.data.get("m_Mesh") or mesh_by_owner.get(owner_id)
                if owner_id is None or not isinstance(mesh, dict) or not mesh.get("guid"):
                    continue
                index.add(ModelSourceRecord(
                    prefab.asset_guid,
                    document.file_id,
                    document.class_id,
                    owner_id,
                    str(mesh["guid"]).lower(),
                    ref_file_id(mesh),
                    transform_by_owner.get(owner_id),
                    "EXACT",
                ))
        return index


@dataclass
class EffectiveRenderer:
    source_guid: str
    file_id: int
    renderer_guid: str = ""
    renderer_type: int = 0
    owner_game_object_id: int | None = None
    mesh_guid: str = ""
    mesh_file_id: int | None = None
    source_kind: str = "MODEL_SOURCE"
    evidence: str = ""
    material_slots: dict[int, dict] = field(default_factory=dict)
    properties: dict[str, object] = field(default_factory=dict)
    provenance: list[str] = field(default_factory=list)

    @property
    def semantic_id(self) -> RendererSemanticID:
        return RendererSemanticID(str(self.renderer_guid or self.source_guid).lower(), int(self.file_id))

    @property
    def mesh_identity(self) -> MeshSemanticID | None:
        if not self.mesh_guid:
            return None
        return MeshSemanticID(self.mesh_guid.lower(), self.mesh_file_id)


@dataclass
class EffectiveComponentGraph:
    occurrence: PrefabOccurrenceIdentity
    renderers: dict[RendererSemanticID, EffectiveRenderer]

    @classmethod
    def from_effective_prefab(cls, prefab: "EffectivePrefab") -> "EffectiveComponentGraph":
        return cls(
            PrefabOccurrenceIdentity(prefab.prefab.asset_guid.lower(), str(prefab.prefab.path).replace("\\", "/")),
            {state.semantic_id: state for state in prefab.renderers.values()},
        )


@dataclass
class EffectivePrefab:
    prefab: PrefabData
    renderers: dict[tuple[str, int], EffectiveRenderer]
    source_chain: tuple[str, ...] = ()
    cycle_detected: bool = False

    @property
    def component_graph(self) -> EffectiveComponentGraph:
        return EffectiveComponentGraph.from_effective_prefab(self)

    @property
    def referenced_source_guids(self) -> set[str]:
        return {
            (state.mesh_guid or state.source_guid).lower()
            for state in self.renderers.values()
            if state.mesh_guid or state.source_guid
        }

    def renderer(self, source_guid: str, file_id: int) -> EffectiveRenderer | None:
        return self.renderers.get((str(source_guid).lower(), int(file_id)))

    def effective_material_bindings(self) -> dict[tuple[str, int, int], str]:
        """Return material bindings keyed by mesh/resource representation.

        Renderer identity remains available on each ``EffectiveRenderer``;
        this view is only for deciding whether a shared imported representation
        needs member-specific object material slots.
        """
        result: dict[tuple[str, int, int], str] = {}
        for state in self.renderers.values():
            representation_guid = state.mesh_guid or state.source_guid
            for slot, reference in state.material_slots.items():
                material_guid = reference.get("guid") if isinstance(reference, dict) else None
                if material_guid:
                    result[(representation_guid.lower(), state.file_id, slot)] = str(material_guid).lower()
        return result


class EffectivePrefabResolver:
    """Resolve inherited renderer state with deterministic last-write-wins rules.

    ``source_loader`` is deliberately injected so package readers can resolve
    source chains without this semantic layer knowing archive or filesystem
    details.  The resolver never uses object names as identity.
    """

    def __init__(
        self,
        source_loader: Callable[[str], PrefabData | None] | None = None,
        model_source_index: ModelSourceSemanticIndex | None = None,
    ):
        self.source_loader = source_loader
        self.model_source_index = model_source_index or ModelSourceSemanticIndex()
        self._memo: dict[tuple[str, tuple[str, ...]], EffectivePrefab] = {}

    def resolve(self, prefab: PrefabData) -> EffectivePrefab:
        return self._resolve(prefab, ())

    def _resolve(self, prefab: PrefabData, chain: tuple[str, ...]) -> EffectivePrefab:
        key = (str(prefab.path).replace("\\", "/"), chain)
        if key in self._memo:
            return self._memo[key]
        identity = str(prefab.path).replace("\\", "/")
        if identity in chain:
            result = EffectivePrefab(prefab, {}, chain, True)
            self._memo[key] = result
            return result

        renderers: dict[tuple[str, int], EffectiveRenderer] = {}
        source_chain = chain + (identity,)
        mesh_guid_by_game_object = {
            ref_file_id(document.data.get("m_GameObject")): str(document.data["m_Mesh"].get("guid", "")).lower()
            for document in prefab.mesh_filter_documents()
            if isinstance(document.data.get("m_Mesh"), dict)
            and ref_file_id(document.data.get("m_GameObject")) is not None
            and document.data["m_Mesh"].get("guid")
        }
        for document in prefab.renderer_documents():
            mesh = document.data.get("m_Mesh")
            mesh_guid = str(mesh.get("guid", "")).lower() if isinstance(mesh, dict) else ""
            mesh_file_id = ref_file_id(mesh) if isinstance(mesh, dict) else None
            direct_mesh = isinstance(mesh, dict) and bool(mesh.get("guid"))
            if not mesh_guid:
                game_object_id = ref_file_id(document.data.get("m_GameObject"))
                mesh_guid = mesh_guid_by_game_object.get(game_object_id, "")
                if not mesh_guid:
                    # A renderer without a mesh and without an owning
                    # MeshFilter is only a placeholder; source modifications
                    # may still establish its effective component identity.
                    continue
            # A renderer document serialized directly in a Prefab belongs to
            # that Prefab occurrence even when its mesh is supplied through a
            # sibling MeshFilter reference.  The mesh GUID is a resource
            # identity, never the renderer declaration identity.
            renderer_guid = prefab.asset_guid if prefab.asset_guid else mesh_guid
            key = (renderer_guid.lower(), document.file_id)
            state = renderers.setdefault(
                key,
                EffectiveRenderer(
                    renderer_guid,
                    document.file_id,
                    renderer_guid=renderer_guid,
                    renderer_type=document.class_id,
                    owner_game_object_id=ref_file_id(document.data.get("m_GameObject")),
                    mesh_guid=mesh_guid,
                    mesh_file_id=mesh_file_id,
                    source_kind="PREFAB_LOCAL" if prefab.asset_guid else "MODEL_SOURCE",
                    evidence="DIRECT_RENDERER_DOCUMENT",
                    provenance=[identity],
                ),
            )
            values = document.data.get("m_Materials")
            if values is None:
                values = [document.data.get("m_Material")]
            if not isinstance(values, list):
                values = [values]
            for slot, reference in enumerate(values):
                if isinstance(reference, dict) and reference.get("guid"):
                    state.material_slots[slot] = dict(reference)

        # Apply inherited/source state first when a loader can provide it.
        for source_guid in prefab.referenced_nested_prefab_guids():
            source = self.source_loader(source_guid) if self.source_loader else None
            if source is not None:
                inherited = self._resolve(source, source_chain)
                for key_tuple, state in inherited.renderers.items():
                    renderers[key_tuple] = EffectiveRenderer(
                        state.source_guid, state.file_id,
                        state.renderer_guid, state.renderer_type,
                        state.owner_game_object_id, state.mesh_guid,
                        state.mesh_file_id, state.source_kind, state.evidence,
                        dict(state.material_slots), dict(state.properties),
                        list(state.provenance),
                    )

        for modification in prefab.modifications():
            # PrefabInstance modifications cover every serialized component
            # (Transform, GameObject, Renderer, etc.).  Without source
            # component metadata, only material-array overrides are positive
            # evidence of a renderer declaration.  Treating every target as
            # a renderer manufactured phantom states for AABB, bones,
            # transforms, and activation flags.
            if not modification.property_path.startswith("m_Materials.Array.data["):
                continue
            lookup = self.model_source_index.lookup(
                modification.target_guid, modification.target_file_id
            )
            source_record = lookup.record
            if source_record is not None:
                state = renderers.setdefault(
                    (modification.target_guid, modification.target_file_id),
                    EffectiveRenderer(
                        modification.target_guid,
                        modification.target_file_id,
                        renderer_guid=modification.target_guid,
                        renderer_type=source_record.renderer_type,
                        owner_game_object_id=source_record.owner_game_object_id,
                        mesh_guid=source_record.mesh_guid,
                        mesh_file_id=source_record.mesh_file_id,
                        source_kind="MODEL_PREFAB_SOURCE_COMPONENT",
                        evidence=source_record.evidence,
                    ),
                )
            else:
                state = renderers.setdefault(
                    (modification.target_guid, modification.target_file_id),
                    EffectiveRenderer(
                        modification.target_guid,
                        modification.target_file_id,
                        renderer_guid=modification.target_guid,
                        source_kind="MODEL_SOURCE",
                        evidence=(
                            "AMBIGUOUS_MODEL_SOURCE_INDEX"
                            if lookup.evidence == "AMBIGUOUS"
                            else "UNKNOWN_MODEL_SOURCE"
                        ),
                    ),
                )
            state.provenance.append(identity)
            if modification.property_path.startswith("m_Materials.Array.data["):
                slot_text = modification.property_path.rsplit("[", 1)[-1].rstrip("]")
                try:
                    slot = int(slot_text)
                except ValueError:
                    continue
                if modification.object_reference is not None:
                    state.material_slots[slot] = dict(modification.object_reference)
            else:
                state.properties[modification.property_path] = modification.value

        result = EffectivePrefab(prefab, renderers, source_chain)
        self._memo[key] = result
        return result


def resolve_effective_prefab(prefab: PrefabData, source_loader=None) -> EffectivePrefab:
    return EffectivePrefabResolver(source_loader).resolve(prefab)
