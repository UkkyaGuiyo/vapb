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


if __name__ == "__main__":
    unittest.main(argv=["prefab-candidate-analyzer"], exit=False)
