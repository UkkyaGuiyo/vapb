"""Stage 1A public synthetic isolation of Effective Renderer projection.

These fixtures deliberately model semantic GUID/fileID relations only.  They
do not copy any commercial asset structure and do not use names as identity.
"""

from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.effective_prefab import (
    EffectivePrefabResolver,
    ModelSourceRecord,
    ModelSourceSemanticIndex,
)
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
from unitypackage_blender_importer.unity.provenance_model import (
    OccurrenceKey,
    OccurrenceStep,
    SourceComponentKey,
)


MODEL = "1" * 32
BASE = "2" * 32
VARIANT = "3" * 32
MESH = "4" * 32
MATERIAL_A = "5" * 32
MATERIAL_B = "6" * 32


def _model_records():
    return [
        ModelSourceRecord(MODEL, 100 + index, 137, 200 + index, MESH, 4300000 + index)
        for index in range(3)
    ]


def _variant_text(source_guid=MODEL, overrides=(100,), material_guid=MATERIAL_A):
    modifications = "".join(
        f"""    - target: {{fileID: {file_id}, guid: {source_guid}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 2100000, guid: {material_guid}, type: 2}}
"""
        for file_id in overrides
    )
    modification_text = modifications or "    []\n"
    return f"""%YAML 1.1
--- !u!1001 &500
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {source_guid}, type: 3}}
  m_Modification:
    m_Modifications:
{modification_text}"""


def _direct_base_text():
    documents = ["%YAML 1.1"]
    for index in range(3):
        game_object = 300 + index
        renderer = 400 + index
        documents.append(f"""--- !u!1 &{game_object}
GameObject:
  m_Name: SyntheticChild{index}
--- !u!137 &{renderer}
SkinnedMeshRenderer:
  m_GameObject: {{fileID: {game_object}}}
  m_Mesh: {{fileID: {4300000 + index}, guid: {MESH}, type: 3}}
""")
    return "".join(documents)


class Stage1ASyntheticProjectionTests(unittest.TestCase):
    def _write(self, root, name, text, guid):
        path = root / name
        path.write_text(text, encoding="utf-8")
        path.with_name(path.name + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {guid}\n", encoding="utf-8"
        )
        return parse_prefab(path)

    def test_model_child_baseline_is_not_expanded_from_model_index(self):
        """A model has three source renderers, but no prefab occurrence is emitted."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model_reference_without_overrides = self._write(
                root, "Root.prefab", _variant_text(MODEL, overrides=()), BASE
            )
            effective = EffectivePrefabResolver(
                model_source_index=ModelSourceSemanticIndex(_model_records())
            ).resolve(model_reference_without_overrides)
        self.assertEqual(3, len(_model_records()))
        self.assertEqual(0, len(effective.renderers))

    def test_model_child_projection_is_materialized_only_when_each_source_is_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            all_touched = self._write(
                root, "AllTouched.prefab", _variant_text(overrides=(100, 101, 102)), VARIANT
            )
            one_touched = self._write(
                root, "OneTouched.prefab", _variant_text(overrides=(100,)), VARIANT
            )
            resolver = EffectivePrefabResolver(
                model_source_index=ModelSourceSemanticIndex(_model_records())
            )
            all_effective = resolver.resolve(all_touched)
            one_effective = resolver.resolve(one_touched)
        self.assertEqual(3, len(all_effective.renderers))
        self.assertEqual(1, len(one_effective.renderers))
        self.assertEqual({100}, {file_id for _, file_id in one_effective.renderers})

    def test_variant_and_nested_chain_boundary_is_visible_when_source_is_serialized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = self._write(root, "Base.prefab", _direct_base_text(), BASE)
            variant = self._write(root, "Variant.prefab", _variant_text(BASE, (400,)), VARIANT)
            nested = self._write(root, "Nested.prefab", _variant_text(VARIANT, ()), "7" * 32)
            nested_override = self._write(
                root, "NestedOverride.prefab", _variant_text(VARIANT, (400,)), "8" * 32
            )
            parsed = {BASE: base, VARIANT: variant}
            resolver = EffectivePrefabResolver(lambda guid: parsed.get(guid))
            direct = resolver.resolve(base)
            inherited = resolver.resolve(variant)
            nested_effective = resolver.resolve(nested)
            nested_override_effective = resolver.resolve(nested_override)
        self.assertEqual(3, len(direct.renderers))
        self.assertEqual(3, len(inherited.renderers))
        self.assertEqual(3, len(nested_effective.renderers))
        # The override is addressed with the immediate variant GUID, while
        # inherited states still retain the serialized base GUID.  The extra
        # state is evidence of an identity-scope boundary, not a name lookup.
        self.assertEqual(4, len(nested_override_effective.renderers))

    def test_material_override_is_a_count_neutral_control(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self._write(root, "First.prefab", _variant_text(overrides=(100,), material_guid=MATERIAL_A), VARIANT)
            second = self._write(root, "Second.prefab", _variant_text(overrides=(100,), material_guid=MATERIAL_B), "7" * 32)
            index = ModelSourceSemanticIndex(_model_records())
            left = EffectivePrefabResolver(model_source_index=index).resolve(first)
            right = EffectivePrefabResolver(model_source_index=index).resolve(second)
        self.assertEqual(len(left.renderers), len(right.renderers))
        self.assertEqual(left.renderer(MODEL, 100).material_slots[0]["guid"], MATERIAL_A)
        self.assertEqual(right.renderer(MODEL, 100).material_slots[0]["guid"], MATERIAL_B)

    def test_same_source_under_two_roots_requires_occurrence_context_outside_effective_prefab(self):
        source = SourceComponentKey("MODEL", MODEL, 100)
        first = OccurrenceKey("root-A", (OccurrenceStep("container", 10, VARIANT),), source)
        second = OccurrenceKey("root-B", (OccurrenceStep("container", 11, VARIANT),), source)
        self.assertNotEqual(first, second)
        # EffectivePrefabResolver has no root-context argument; this test
        # records that occurrence-aware identity must be supplied by the
        # projection/bridge layer rather than inferred from object names.
        self.assertEqual(first.source_key, second.source_key)


if __name__ == "__main__":
    unittest.main()
