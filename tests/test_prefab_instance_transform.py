"""Unity-authored PrefabInstance Transform defaults and scoped overrides."""

import copy
import json
from pathlib import Path
import re
import unittest

from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
from unitypackage_blender_importer.unity.prefab_instance_transform import (
    has_complete_transform, resolve_instance_transform,
)


ASSETS = Path(__file__).with_name("unity_alias_oracle") / "Assets" / "Oracle"
EXPECTED = ASSETS.parents[1] / "transform_expected.json"


def fixture():
    return (parse_prefab(ASSETS / "Transform_TwoInstances.prefab"),
            parse_prefab(ASSETS / "Transform_Source.prefab"))


def instance_ids(container):
    rows = {}
    for item in container.modifications():
        if item.property_path == "m_LocalPosition.x":
            rows[float(item.value)] = item.prefab_instance_file_id
    return rows


class PrefabInstanceTransformTests(unittest.TestCase):
    def test_parent_chain_requires_complete_serialized_trs(self):
        container, _ = fixture()
        parent_id = next(transform.file_id for transform in container.transforms.values()
                         if transform.parent_id == 0)
        self.assertTrue(has_complete_transform(container, parent_id))
        incomplete = copy.deepcopy(container)
        parent_doc = next(doc for doc in incomplete.documents if doc.file_id == parent_id)
        del parent_doc.data["m_LocalRotation"]["w"]
        self.assertFalse(has_complete_transform(incomplete, parent_id))
        child = copy.deepcopy(container)
        child_transform = copy.deepcopy(child.transforms[parent_id])
        child_transform.file_id = 999
        child_transform.parent_id = parent_id
        child.transforms[999] = child_transform
        child_doc = copy.deepcopy(next(doc for doc in child.documents if doc.file_id == parent_id))
        child_doc.file_id = 999
        child.documents.append(child_doc)
        self.assertTrue(has_complete_transform(child, 999))
        child_parent_doc = next(doc for doc in child.documents if doc.file_id == parent_id)
        del child_parent_doc.data["m_LocalRotation"]["w"]
        self.assertFalse(has_complete_transform(child, 999))

    def test_unity_authored_source_default_and_two_distinct_overrides(self):
        observed = json.loads(EXPECTED.read_text(encoding="utf-8"))
        container, source = fixture()
        self.assertEqual("2022.3.22f1", observed["unityVersion"])
        self.assertEqual((container.asset_guid, source.asset_guid),
                         (observed["pairGuid"], observed["sourceGuid"]))
        ids = instance_ids(container)
        self.assertEqual({10.0, 0.25}, set(ids))
        a = resolve_instance_transform(container, ids[10.0], source)
        b = resolve_instance_transform(container, ids[0.25], source)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual({"x": 10.0, "y": -0.5, "z": 0.75}, a.position)
        self.assertEqual({"x": 0.25, "y": -0.5, "z": 0.75}, b.position)
        self.assertEqual({"x": 1.2, "y": 0.8, "z": -1.1}, a.scale)
        self.assertEqual({"x": 1.2, "y": 1.4, "z": -1.1}, b.scale)
        self.assertNotEqual(a.rotation, b.rotation)
        self.assertEqual(source.root_game_objects()[0].file_id,
                         source.transforms[a.source_transform_id].game_object_id)

    def test_missing_source_default_or_ambiguous_root_is_unknown(self):
        container, source = fixture()
        instance_id = instance_ids(container)[10.0]
        ambiguous = copy.deepcopy(source)
        root = next(iter(ambiguous.transforms.values()))
        ambiguous.transforms[999] = copy.deepcopy(root)
        self.assertIsNone(resolve_instance_transform(container, instance_id, ambiguous))
        incomplete = copy.deepcopy(source)
        root_doc = next(doc for doc in incomplete.documents
                        if doc.class_id == 4 and doc.file_id == root.file_id)
        del root_doc.data["m_LocalScale"]["z"]
        self.assertIsNone(resolve_instance_transform(container, instance_id, incomplete))
        incomplete_rotation = copy.deepcopy(source)
        root_doc = next(doc for doc in incomplete_rotation.documents
                        if doc.class_id == 4 and doc.file_id == root.file_id)
        del root_doc.data["m_LocalRotation"]["w"]
        self.assertIsNone(resolve_instance_transform(container, instance_id, incomplete_rotation))

    def test_wrong_guid_malformed_value_and_descendant_target_fail_closed(self):
        container, source = fixture()
        instance_id = instance_ids(container)[10.0]
        root_id = next(iter(source.transforms))
        instance = next(doc for doc in container.documents if doc.file_id == instance_id)
        wrong_guid = copy.deepcopy(container)
        changed = next(doc for doc in wrong_guid.documents if doc.file_id == instance_id)
        changed.raw = changed.raw.replace(
            f"fileID: {root_id}, guid: {source.asset_guid}",
            f"fileID: {root_id}, guid: {'f' * 32}")
        self.assertIsNone(resolve_instance_transform(wrong_guid, instance_id, source))
        malformed = copy.deepcopy(container)
        changed = next(doc for doc in malformed.documents if doc.file_id == instance_id)
        changed.raw = changed.raw.replace("propertyPath: m_LocalPosition.x\n      value: 10",
                                          "propertyPath: m_LocalPosition.x\n      value: invalid")
        self.assertIsNone(resolve_instance_transform(malformed, instance_id, source))
        descendant = copy.deepcopy(container)
        changed = next(doc for doc in descendant.documents if doc.file_id == instance_id)
        changed.raw = changed.raw.replace(f"fileID: {root_id}, guid: {source.asset_guid}",
                                          f"fileID: {root_id + 1}, guid: {source.asset_guid}")
        self.assertEqual(source.transforms[root_id].position,
                         resolve_instance_transform(descendant, instance_id, source).position)
        self.assertIsNotNone(instance)

    def test_partial_property_overlay_uses_source_axes_and_instance_scope(self):
        container, source = fixture()
        ids = instance_ids(container)
        one_axis = copy.deepcopy(container)
        doc = next(item for item in one_axis.documents if item.file_id == ids[10.0])
        chunks = re.split(r"(?=\n    - target:)", doc.raw)
        doc.raw = "".join(chunk for chunk in chunks
                          if "propertyPath: m_Local" not in chunk
                          or "propertyPath: m_LocalPosition.x" in chunk)
        a = resolve_instance_transform(one_axis, ids[10.0], source)
        b = resolve_instance_transform(one_axis, ids[0.25], source)
        self.assertEqual({"x": 10.0, "y": -0.5, "z": 0.75}, a.position)
        self.assertEqual(next(iter(source.transforms.values())).rotation, a.rotation)
        self.assertEqual(next(iter(source.transforms.values())).scale, a.scale)
        self.assertEqual(1.4, b.scale["y"])
        self.assertIsNone(resolve_instance_transform(container, -1, source))
        hint_only = copy.deepcopy(container)
        doc = next(item for item in hint_only.documents if item.file_id == ids[10.0])
        doc.raw = doc.raw.replace("propertyPath: m_LocalEulerAnglesHint.x\n      value: 0",
                                  "propertyPath: m_LocalEulerAnglesHint.x\n      value: 170")
        self.assertEqual(resolve_instance_transform(container, ids[10.0], source).rotation,
                         resolve_instance_transform(hint_only, ids[10.0], source).rotation)


if __name__ == "__main__":
    unittest.main()
