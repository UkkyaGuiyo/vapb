from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from unitypackage_blender_importer.blender.roundtrip_manifest import (
    MANIFEST_TYPE,
    SCHEMA_VERSION,
    build_material_manifest,
    sidecar_path,
    write_material_manifest,
)


class FakeMaterial(dict):
    def __init__(self, name: str, **props):
        super().__init__(props)
        self.name = name


class FakeData:
    def __init__(self, *materials):
        self.materials = list(materials)


class FakeModifier:
    def __init__(self, kind: str):
        self.type = kind


class FakeObject:
    def __init__(self, name: str, data=None, parent=None, modifiers=()):
        self.name = name
        self.data = data
        self.parent = parent
        self.modifiers = list(modifiers)
        self.type = "MESH" if data is not None else "EMPTY"


class RoundTripManifestTests(unittest.TestCase):
    def test_object_material_slots_override_shared_mesh_and_preserve_empty_slot(self):
        shared = FakeMaterial("Shared", unity_material_guid="a" * 32)
        override = FakeMaterial("Occurrence", unity_material_guid="b" * 32)
        data = FakeData(shared, shared)
        first, second = FakeObject("First", data), FakeObject("Second", data)
        first.material_slots = [SimpleNamespace(material=override), SimpleNamespace(material=None)]
        second.material_slots = [SimpleNamespace(material=shared), SimpleNamespace(material=shared)]
        manifest = build_material_manifest([first, second], Path("Instances.fbx"))
        self.assertEqual("unity-guid:" + "b" * 32, manifest["bindings"][0]["material_key"])
        self.assertEqual("empty_slot", manifest["bindings"][1]["status"])
        self.assertEqual("unity-guid:" + "a" * 32, manifest["bindings"][2]["material_key"])
        self.assertEqual([shared, shared], data.materials)

    def test_schema_duplicate_guid_and_multiple_slots(self):
        body = FakeMaterial(
            "Body",
            unity_material_guid="a" * 32,
            unity_material_path="Assets/Body.mat",
            unity_material_name="Body",
            unity_shader_guid="shader-guid",
            unity_shader_name="lilToon/lts",
        )
        duplicate_name = FakeMaterial(
            "Body.001",
            unity_material_guid="b" * 32,
            unity_material_path="Assets/Other/Body.mat",
            unity_material_name="Body",
            unity_shader_guid="shader-guid-2",
            unity_shader_name="Poiyomi/Toon",
        )
        root = FakeObject("Avatar")
        mesh_a = FakeObject("Body", FakeData(body, body, duplicate_name), root, [FakeModifier("ARMATURE")])
        mesh_b = FakeObject("Clothing", FakeData(duplicate_name), root)
        manifest = build_material_manifest([root, mesh_a, mesh_b], Path("Avatar.fbx"))

        self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
        self.assertEqual(manifest["manifest_type"], MANIFEST_TYPE)
        self.assertEqual(len(manifest["materials"]), 2)
        self.assertEqual(len(manifest["bindings"]), 4)
        self.assertEqual(manifest["bindings"][0]["renderer_type"], "SkinnedMeshRenderer")
        self.assertEqual(manifest["bindings"][0]["material_key"], manifest["bindings"][1]["material_key"])
        self.assertNotEqual(manifest["materials"][0]["material_key"], manifest["materials"][1]["material_key"])
        self.assertEqual(manifest["materials"][0]["unity_material_guid"], "a" * 32)
        self.assertEqual(manifest["materials"][1]["unity_material_guid"], "b" * 32)
        self.assertEqual(manifest["bindings"][3]["object_path"], "Avatar/Clothing")

    def test_metadata_missing_material_is_explicit(self):
        material = FakeMaterial("EditedMaterial")
        mesh = FakeObject("Mesh", FakeData(material))
        manifest = build_material_manifest([mesh], Path("Edited.fbx"))
        self.assertEqual(manifest["bindings"][0]["status"], "metadata_missing")
        self.assertTrue(manifest["warnings"])

    def test_sidecar_write_is_versioned_json(self):
        with tempfile.TemporaryDirectory(prefix="roundtrip_manifest_test_") as temp:
            fbx_path = Path(temp) / "private-package-root.fbx"
            fbx_path.write_bytes(b"FBX")
            output = write_material_manifest([], fbx_path)
            self.assertEqual(output, sidecar_path(fbx_path))
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["fbx_file"], "private-package-root.fbx")
