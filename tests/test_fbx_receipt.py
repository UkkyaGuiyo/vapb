import hashlib
import tempfile
import unittest
from pathlib import Path

from unitypackage_blender_importer.blender.fbx_receipt import (
    FbxModelLink,
    RawFbxSemanticIndex,
    make_receipt,
    persist_receipt,
    validate_receipt_continuity,
    copy_with_receipt,
    make_bone_receipt,
    persist_bone_receipt,
)


class FbxReceiptTests(unittest.TestCase):
    def _native_object(self):
        class Data(dict):
            session_uid = 22

        class Obj(dict):
            session_uid = 11

            def copy(self):
                result = Obj(self)
                result.session_uid = self.session_uid + 1
                result.data = self.data
                return result

        obj = Obj()
        obj.data = Data()
        persist_receipt(obj, make_receipt(-10, 20, "a" * 32, "b" * 64))
        return obj

    def test_explicit_copy_carries_source_receipt_and_distinct_realization(self):
        source = self._native_object()
        member = copy_with_receipt(source)
        self.assertTrue(validate_receipt_continuity(member))
        self.assertIs(member.data, source.data)
        self.assertEqual(source['_vapb_fbx_object_receipt_id'], member['_vapb_fbx_object_receipt_id'])
        self.assertNotEqual(source['_vapb_fbx_realization_id'], member['_vapb_fbx_realization_id'])
        self.assertEqual(source['_vapb_fbx_realization_id'], member['_vapb_fbx_source_realization_id'])
        self.assertNotIn('_vapb_renderer_bindings', member)

    def test_unobserved_copy_cannot_launder_a_receipt(self):
        source = self._native_object()
        copied = source.copy()
        member = copy_with_receipt(copied)
        self.assertFalse(validate_receipt_continuity(member))
        self.assertNotIn('_vapb_fbx_object_receipt_id', member)
        self.assertNotIn('_vapb_fbx_realization_id', member)

    def test_copy_does_not_modify_source_or_mesh_metadata(self):
        source = self._native_object()
        source['_vapb_renderer_bindings'] = 'source occurrence only'
        before, mesh_before = dict(source), dict(source.data)
        member = copy_with_receipt(source)
        self.assertEqual(before, dict(source))
        self.assertEqual(mesh_before, dict(source.data))
        self.assertNotIn('_vapb_renderer_bindings', member)

    def test_model_geometry_link_is_exact_only_when_unique(self):
        index = RawFbxSemanticIndex([FbxModelLink(10, 20), FbxModelLink(11, 21)])
        self.assertEqual(20, index.geometry_for_model(10))
        self.assertIsNone(RawFbxSemanticIndex([FbxModelLink(10, 20), FbxModelLink(10, 22)]).geometry_for_model(10))
        self.assertTrue(RawFbxSemanticIndex([], [10]).unique_source_model(10))
        self.assertFalse(RawFbxSemanticIndex([], [10, 10]).unique_source_model(10))
        self.assertFalse(RawFbxSemanticIndex([], []).unique_source_model(10))

    def test_receipt_is_hash_bound_and_signed_uids_are_strings_when_persisted(self):
        receipt = make_receipt(-10, 20, "A" * 32, "b" * 64)

        class Data(dict):
            pass

        class Obj(dict):
            data = Data()

        obj = Obj()
        persist_receipt(obj, receipt)
        self.assertEqual("-10", obj["_vapb_fbx_model_uid"])
        self.assertEqual("20", obj.data["_vapb_fbx_geometry_uid"])
        self.assertEqual("b" * 64, obj["_vapb_fbx_source_asset_sha256"])

    def test_copied_receipt_fails_session_continuity(self):
        class Data(dict):
            session_uid = 22

        class Obj(dict):
            session_uid = 11
            data = Data()

        obj = Obj()
        persist_receipt(obj, make_receipt(1, 2, "g", "b" * 64))
        self.assertTrue(validate_receipt_continuity(obj))
        obj.session_uid = 12
        self.assertFalse(validate_receipt_continuity(obj))

    def test_source_hash_is_sha256_of_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.fbx"
            payload = b"source-revision"
            path.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(expected, make_receipt(1, 2, "g", expected).source_asset_sha256)

    def test_bone_receipts_keep_source_uid_and_distinct_realizations(self):
        first = make_bone_receipt(-10, "A" * 32, "b" * 64)
        second = make_bone_receipt(-11, "A" * 32, "b" * 64)
        self.assertNotEqual(first.blender_bone_receipt_id, second.blender_bone_receipt_id)
        self.assertNotEqual(first.blender_bone_receipt_id,
                            make_bone_receipt(-10, "c" * 32, "b" * 64).blender_bone_receipt_id)
        bone_a, bone_b = {}, {}
        persist_bone_receipt(bone_a, first)
        persist_bone_receipt(bone_b, second)
        self.assertEqual("-10", bone_a["_vapb_fbx_model_uid"])
        self.assertEqual("-11", bone_b["_vapb_fbx_model_uid"])
        self.assertNotEqual(bone_a["_vapb_fbx_bone_realization_id"], bone_b["_vapb_fbx_bone_realization_id"])
        self.assertEqual("a" * 32, bone_a["_vapb_fbx_source_asset_guid"])
        self.assertEqual("b" * 64, bone_a["_vapb_fbx_source_asset_sha256"])


if __name__ == "__main__":
    unittest.main()
