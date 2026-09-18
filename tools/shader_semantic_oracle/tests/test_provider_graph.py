import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.shader_semantic_oracle.provider_graph import (
    build_provider_graph,
    classify_unity_validation,
)


def _package(root: Path, entries: dict[str, bytes]) -> Path:
    path = root / f"{len(list(root.iterdir()))}.unitypackage"
    with tarfile.open(path, "w:gz") as tar:
        for guid, pathname, asset in entries.values():
            for name, data in (
                (f"{guid}/pathname", pathname.encode()),
                (f"{guid}/asset", asset),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return path


class ProviderGraphTests(unittest.TestCase):
    def test_cross_package_provider_is_found_without_payload_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shader_guid = "a" * 32
            material_guid = "b" * 32
            consumer = _package(root, {"m": (material_guid, "Assets/M.mat", f"m_Shader: {{fileID: 4800000, guid: {shader_guid}}}".encode())})
            provider = _package(root, {"s": (shader_guid, "Assets/Provider.shader", b"Shader \"Private\" {}")})
            graph = build_provider_graph([consumer, provider])
            material = graph["materials"][0]
            self.assertEqual(material["classification"], "CORPUS_PROVIDER_FOUND")
            self.assertEqual(material["provider_candidates"][0]["asset_type"], "shader")
            self.assertNotIn("Private", str(graph))

    def test_missing_and_builtin_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = "c" * 32
            package = _package(root, {
                "m1": ("d" * 32, "Assets/Missing.mat", f"m_Shader: {{fileID: 1, guid: {missing}}}".encode()),
                "m2": ("e" * 32, "Assets/Builtin.mat", b"m_Shader: {fileID: 1, guid: 0000000000000000f000000000000000}"),
            })
            classes = {item["classification"] for item in build_provider_graph([package])["materials"]}
            self.assertEqual(classes, {"EXTERNAL_PROVIDER_MISSING", "BUILTIN_SHADER"})

    def test_local_provider_has_precedence_over_cross_package_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shader_guid = "f" * 32
            local = _package(root, {
                "m": ("1" * 32, "Assets/Local.mat", f"m_Shader: {{fileID: 1, guid: {shader_guid}}}".encode()),
                "s": (shader_guid, "Assets/Local.shader", b"local"),
            })
            external = _package(root, {"s": (shader_guid, "Assets/External.shader", b"external")})
            graph = build_provider_graph([local, external])
            self.assertEqual(graph["materials"][0]["classification"], "LOCAL_PROVIDER_FOUND")
            self.assertEqual(graph["materials"][0]["provider_candidates"][0]["package"], "PACKAGE_01")

    def test_ambiguous_and_missing_shader_reference_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shader_guid = "a" * 32
            consumer = _package(root, {
                "m1": ("1" * 32, "Assets/A.mat", f"m_Shader: {{fileID: 1, guid: {shader_guid}}}".encode()),
                "m2": ("2" * 32, "Assets/B.mat", b"m_Name: B"),
            })
            first = _package(root, {"s": (shader_guid, "Assets/A.shader", b"a")})
            second = _package(root, {"s": (shader_guid, "Assets/B.shader", b"b")})
            classes = {item["classification"] for item in build_provider_graph([consumer, first, second])["materials"]}
            self.assertEqual(classes, {"SHADER_REFERENCE_AMBIGUOUS", "SHADER_REFERENCE_MISSING"})

    def test_unity_validation_categories_do_not_equate_error_shader_with_missing(self):
        self.assertEqual(classify_unity_validation(shader_loaded=False, shader_name=None), "DEPENDENCY_BLOCKED")
        self.assertEqual(classify_unity_validation(shader_loaded=True, shader_name="Hidden/InternalErrorShader"), "DEPENDENCY_BLOCKED")
        self.assertEqual(classify_unity_validation(shader_loaded=True, shader_name="Custom/Unsupported", supported=False), "DEPENDENCY_BLOCKED")
        self.assertEqual(classify_unity_validation(shader_loaded=True, shader_name="Custom/Valid"), "VALID_SHADER")
        self.assertEqual(classify_unity_validation(shader_loaded=True, shader_name="Custom/Bad", compile_error=True), "PROVIDER_PRESENT_COMPILE_FAILED")


if __name__ == "__main__":
    unittest.main()
