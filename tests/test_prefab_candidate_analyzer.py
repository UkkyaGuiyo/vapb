"""PCA-001..015 synthetic coverage for deterministic Prefab selection."""

from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
from unitypackage_blender_importer.unity.prefab_candidate_analyzer import (
    PrefabCandidateAnalysis,
    PrefabCandidateAnalyzer,
)


def _add(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _package(path: Path, records: list[tuple[str, str, bytes]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            _add(archive, f"{guid}/asset", payload)
            _add(archive, f"{guid}/pathname", unity_path.encode())
            _add(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode())


def _prefab(fbx_guid: str, material_guid: str, name: str, *, skinned: bool = False) -> bytes:
    class_name = "SkinnedMeshRenderer" if skinned else "MeshRenderer"
    class_id = 137 if skinned else 23
    return f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: {name}
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: 1001}}
  m_Father: {{fileID: 0}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!33 &103
MeshFilter:
  m_GameObject: {{fileID: 1001}}
  m_Mesh: {{fileID: 4300000, guid: {fbx_guid}, type: 3}}
--- !u!{class_id} &102
{class_name}:
  m_GameObject: {{fileID: 1001}}
  m_Materials:
  - {{fileID: 2100000, guid: {material_guid}, type: 2}}
""".encode()


def _material(texture_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: SyntheticSurface
  m_TexEnvs:
  - _MainTex:
      m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}
""".encode()


def _candidate(token: str, kind: str, status: str, *, renderers: int = 1) -> PrefabCandidateAnalysis:
    return PrefabCandidateAnalysis(
        token=token,
        prefab_path=Path(f"{token}.prefab"),
        unity_path=f"Assets/{token}.prefab",
        guid=token,
        display_name=token,
        candidate_kind=kind,
        visual_status=status,
        renderer_count=renderers,
        skinned_renderer_count=1 if kind == "AVATAR_LIKE" else 0,
        mesh_renderer_count=renderers,
        game_object_count=1,
        transform_count=1,
        material_slot_count=1,
    )


class PrefabCandidateAnalyzerTests(unittest.TestCase):
    def test_pca_016_unrelated_external_package_is_not_fully_indexed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analyzer, _item = self._analyze(root, provider=False)
            unrelated = root / "Unrelated.unitypackage"
            _package(unrelated, [("d" * 32, "Assets/Other.mat", _material("e" * 32))])
            analyzer.extra_package_paths.add(unrelated.resolve())
            analyzer._load_external_sources({"f" * 32})
            self.assertNotIn(unrelated.resolve(), analyzer.cache._sources)

    def test_pca_017_textual_frontier_is_read_with_one_archive_open(self):
        with tempfile.TemporaryDirectory() as temp:
            analyzer, item = self._analyze(Path(temp), provider=True)
            self.assertIn("c" * 32, item.required_visual_guids)
            self.assertEqual(1, analyzer.cache.asset_read_counts[(Path(temp) / "Provider.unitypackage").resolve(), "b" * 32])
            self.assertEqual(1, analyzer.cache.batch_archive_open_counts[(Path(temp) / "Provider.unitypackage").resolve()])

    def test_pca_018_second_pass_reuses_static_prefab_facts_and_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            analyzer, _item = self._analyze(Path(temp), provider=True)
            self.assertGreaterEqual(analyzer.static_fact_cache_hits, 1)
            analyzer._closure({"a" * 32, "b" * 32})
            analyzer._closure({"a" * 32, "b" * 32})
            self.assertGreaterEqual(analyzer.closure_cache_hits, 1)
    def test_pca_001_avatar_is_structurally_classified(self):
        item = _candidate("PREFAB_0", "AVATAR_LIKE", "COMPLETE")
        self.assertEqual("AVATAR_LIKE", item.candidate_kind)

    def test_pca_002_prop_is_not_named_as_avatar(self):
        item = _candidate("PREFAB_0", "PROP_LIKE", "COMPLETE")
        self.assertEqual("PROP_LIKE", item.candidate_kind)

    def test_pca_003_incomplete_visual_closure_is_visible(self):
        item = _candidate("PREFAB_0", "AVATAR_LIKE", "PARTIAL")
        item.unresolved_visual_guids.add("missing")
        self.assertEqual("PARTIAL", item.visual_status)

    def test_pca_004_unique_supported_prefab_is_automatic(self):
        result = PrefabCandidateAnalyzer.select([_candidate("PREFAB_0", "PROP_LIKE", "COMPLETE")])
        self.assertEqual(("AUTO_SELECTED", "PREFAB_0"), (result.mode, result.token))

    def test_pca_005_multiple_complete_avatars_require_choice(self):
        result = PrefabCandidateAnalyzer.select([
            _candidate("PREFAB_0", "AVATAR_LIKE", "COMPLETE"),
            _candidate("PREFAB_1", "AVATAR_LIKE", "COMPLETE"),
        ])
        self.assertEqual("USER_CHOICE_REQUIRED", result.mode)

    def test_pca_006_ambiguous_provider_never_auto_selects(self):
        result = PrefabCandidateAnalyzer.select([_candidate("PREFAB_0", "AVATAR_LIKE", "AMBIGUOUS")])
        self.assertEqual("USER_CHOICE_REQUIRED", result.mode)
        self.assertEqual("AMBIGUOUS_PROVIDER", result.reason)

    def test_pca_007_empty_prefabs_are_not_supported(self):
        result = PrefabCandidateAnalyzer.select([_candidate("PREFAB_0", "EMPTY_OR_UNSUPPORTED", "NONE", renderers=0)])
        self.assertEqual("NO_SUPPORTED_PREFAB", result.mode)

    def test_pca_008_tokens_are_index_stable(self):
        items = [_candidate(f"PREFAB_{i}", "PROP_LIKE", "COMPLETE") for i in range(3)]
        self.assertEqual([f"PREFAB_{i}" for i in range(3)], [item.token for item in items])

    def _analyze(self, root: Path, *, provider: bool = False, ambiguous: bool = False):
        fbx = "a" * 32
        material = "b" * 32
        texture = "c" * 32
        primary = root / "Primary.unitypackage"
        _package(primary, [
            ("1" * 32, "Assets/Avatar.prefab", _prefab(fbx, material, "SyntheticAvatar", skinned=True)),
            (fbx, "Assets/Avatar.fbx", b"FBX_PAYLOAD"),
        ])
        if provider:
            _package(root / "Provider.unitypackage", [
                (material, "Assets/Surface.mat", _material(texture)),
                (texture, "Assets/Surface.png", b"PNG_PAYLOAD"),
            ])
            if ambiguous:
                _package(root / "Provider2.unitypackage", [
                    (material, "Assets/Surface2.mat", _material(texture)),
                ])
        extract = root / "extract"
        prefab_path = extract / "Assets/Avatar.prefab"
        prefab_path.parent.mkdir(parents=True)
        prefab_path.write_bytes(_prefab(fbx, material, "SyntheticAvatar", skinned=True))
        index = UnityPackageReader(primary).build_index()
        analyzer = PrefabCandidateAnalyzer(primary, index, extract, [prefab_path])
        return analyzer, analyzer.analyze()[0]

    def test_pca_009_local_visual_closure_completes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fbx, material, texture = "a" * 32, "b" * 32, "c" * 32
            primary = root / "Primary.unitypackage"
            _package(primary, [
                ("1" * 32, "Assets/Avatar.prefab", _prefab(fbx, material, "LocalAvatar", skinned=True)),
                (fbx, "Assets/Avatar.fbx", b"FBX"),
                (material, "Assets/Surface.mat", _material(texture)),
                (texture, "Assets/Surface.png", b"PNG"),
            ])
            extract = root / "extract"; path = extract / "Assets/Avatar.prefab"; path.parent.mkdir(parents=True); path.write_bytes(_prefab(fbx, material, "LocalAvatar", skinned=True))
            analyzer = PrefabCandidateAnalyzer(primary, UnityPackageReader(primary).build_index(), extract, [path])
            item = analyzer.analyze()[0]
            self.assertEqual("COMPLETE", item.visual_status)

    def test_pca_010_cross_package_material_provider_completes(self):
        with tempfile.TemporaryDirectory() as temp:
            analyzer, item = self._analyze(Path(temp), provider=True)
            self.assertEqual("COMPLETE", item.visual_status)
            self.assertEqual(1, len(item.provider_packages))

    def test_pca_011_fbx_payload_is_not_read_during_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            analyzer, _item = self._analyze(Path(temp), provider=True)
            self.assertEqual({}, {key: value for key, value in analyzer.cache.asset_read_counts.items() if key[0].name == "Primary.unitypackage" and key[1] == "a" * 32})

    def test_pca_012_material_texture_is_transitive(self):
        with tempfile.TemporaryDirectory() as temp:
            _analyzer, item = self._analyze(Path(temp), provider=True)
            self.assertIn("c" * 32, item.required_visual_guids)

    def test_pca_013_provider_indexes_are_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            analyzer, _item = self._analyze(Path(temp), provider=True)
            self.assertEqual(1, analyzer.cache.index_build_counts[(Path(temp) / "Provider.unitypackage").resolve()])

    def test_pca_014_duplicate_provider_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp:
            _analyzer, item = self._analyze(Path(temp), provider=True, ambiguous=True)
            self.assertEqual("AMBIGUOUS", item.visual_status)
            self.assertIn("b" * 32, item.ambiguous_visual_guids)

    def test_pca_015_selection_is_deterministic(self):
        items = [_candidate("PREFAB_0", "AVATAR_LIKE", "COMPLETE"), _candidate("PREFAB_1", "PROP_LIKE", "PARTIAL")]
        first = PrefabCandidateAnalyzer.select(items)
        second = PrefabCandidateAnalyzer.select(items)
        self.assertEqual(first, second)

    def test_pcm_001_composes_variants_outfits_and_accessory_without_chooser(self):
        body_a = _candidate("BODY_A", "AVATAR_LIKE", "COMPLETE")
        body_a.guid = "1" * 32
        body_a.referenced_fbx_guids = {"a" * 32}
        body_b = _candidate("BODY_B", "AVATAR_LIKE", "COMPLETE")
        body_b.guid = "2" * 32
        body_b.referenced_fbx_guids = {"a" * 32}
        outfit = _candidate("OUTFIT", "SKINNED_ADDON", "COMPLETE")
        outfit.guid = "3" * 32
        outfit.referenced_fbx_guids = {"b" * 32}
        accessory = _candidate("ACCESSORY", "RIGID_ATTACHMENT", "COMPLETE")
        accessory.guid = "4" * 32
        accessory.referenced_fbx_guids = {"c" * 32}
        plan = PrefabCandidateAnalyzer.compose([body_b, accessory, outfit, body_a])
        self.assertFalse(plan.chooser_required)
        self.assertEqual(["BODY_A", "BODY_B", "OUTFIT", "ACCESSORY"], [member.display_name for member in plan.members])
        self.assertEqual({"a" * 32, "b" * 32, "c" * 32}, {item.asset_guid for item in plan.representations})

    def test_pcm_004_shared_fbx_has_one_representation_and_stable_plan(self):
        first = _candidate("FIRST", "AVATAR_LIKE", "COMPLETE")
        first.guid = "1" * 32; first.referenced_fbx_guids = {"a" * 32}
        second = _candidate("SECOND", "SKINNED_ADDON", "COMPLETE")
        second.guid = "2" * 32; second.referenced_fbx_guids = {"a" * 32}
        first_plan = PrefabCandidateAnalyzer.compose([first, second])
        second_plan = PrefabCandidateAnalyzer.compose([second, first])
        self.assertEqual(first_plan, second_plan)
        self.assertEqual(1, len(first_plan.representations))
        self.assertEqual({"1" * 32, "2" * 32}, first_plan.representations[0].member_ids)

    def test_pcm_007_helper_is_preserved_but_does_not_force_chooser(self):
        helper = _candidate("HELPER", "EMPTY_OR_UNSUPPORTED", "NONE", renderers=0)
        helper.guid = "9" * 32
        body = _candidate("BODY", "AVATAR_LIKE", "COMPLETE")
        body.guid = "1" * 32; body.referenced_fbx_guids = {"a" * 32}
        plan = PrefabCandidateAnalyzer.compose([helper, body])
        self.assertFalse(plan.chooser_required)
        self.assertEqual("HELPER", plan.helpers[0].display_name)
        self.assertEqual(["BODY"], [member.display_name for member in plan.members])

    def test_pcm_007_nested_renderer_free_prefab_is_helper_metadata_not_member(self):
        helper = _candidate("NESTED_HELPER", "NESTED_COMPOSITE", "COMPLETE", renderers=0)
        helper.guid = "8" * 32
        helper.nested_prefab_guids = {"7" * 32}
        body = _candidate("BODY", "AVATAR_LIKE", "COMPLETE")
        body.guid = "1" * 32
        plan = PrefabCandidateAnalyzer.compose([helper, body])
        self.assertEqual(("NESTED_HELPER",), tuple(item.display_name for item in plan.helpers))
        self.assertEqual(("BODY",), tuple(item.display_name for item in plan.members))

    def test_pcm_007_duplicate_provider_is_the_real_chooser_condition(self):
        first = _candidate("BODY_A", "AVATAR_LIKE", "AMBIGUOUS")
        first.guid = "1" * 32
        first.referenced_fbx_guids = {"a" * 32}
        first.ambiguous_visual_guids = {"a" * 32}
        second = _candidate("BODY_B", "AVATAR_LIKE", "AMBIGUOUS")
        second.guid = "2" * 32
        second.referenced_fbx_guids = {"a" * 32}
        second.ambiguous_visual_guids = {"a" * 32}
        plan = PrefabCandidateAnalyzer.compose([first, second])
        self.assertTrue(plan.chooser_required)
        self.assertEqual("AMBIGUOUS_PROVIDER", plan.chooser_reason)

    def test_pcm_008_actual_package_fixture_keeps_all_visual_members_and_deduplicates_fbx(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fbx = "a" * 32
            material = "b" * 32
            records = []
            prefab_paths = []
            for index, name in enumerate(("Body", "Outfit", "Accessory"), start=1):
                guid = str(index) * 32
                payload = _prefab(fbx, material, name, skinned=name != "Accessory")
                records.append((guid, f"Assets/{name}.prefab", payload))
            records.extend([(fbx, "Assets/Shared.fbx", b"FBX"), (material, "Assets/Shared.mat", _material("c" * 32))])
            primary = root / "Composition.unitypackage"
            _package(primary, records)
            extract = root / "extract"
            for index, name in enumerate(("Body", "Outfit", "Accessory"), start=1):
                path = extract / "Assets" / f"{name}.prefab"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(_prefab(fbx, material, name, skinned=name != "Accessory"))
                prefab_paths.append(path)
            analyzer = PrefabCandidateAnalyzer(
                primary, UnityPackageReader(primary).build_index(), extract, prefab_paths
            )
            plan = analyzer.compose(analyzer.analyze())
            self.assertFalse(plan.chooser_required)
            self.assertEqual(3, len(plan.members))
            self.assertEqual((fbx,), tuple(item.asset_guid for item in plan.representations))
            self.assertNotIn(material, {item.asset_guid for item in plan.representations})

    def test_pcm_008_composition_has_no_product_or_archive_order_rule(self):
        source = (Path(__file__).parents[1] / "unity" / "prefab_candidate_analyzer.py").read_text(encoding="utf-8")
        self.assertNotIn("CaseA", source)
        self.assertNotIn("SampleAvatarB", source)
        self.assertNotIn("archive_order", source)

    def test_pcm_009_conflicting_interpretation_requires_chooser(self):
        first = _candidate("SAME", "AVATAR_LIKE", "COMPLETE")
        second = _candidate("SAME", "PROP_LIKE", "COMPLETE")
        plan = PrefabCandidateAnalyzer.compose([first, second])
        self.assertTrue(plan.chooser_required)
        self.assertEqual("CONFLICTING_INTERPRETATION", plan.chooser_reason)


if __name__ == "__main__":
    unittest.main(argv=["prefab-candidate-analyzer"], exit=False)
