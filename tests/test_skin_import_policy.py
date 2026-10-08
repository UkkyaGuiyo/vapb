# SPDX-License-Identifier: GPL-3.0-or-later
import json
import unittest
from unitypackage_blender_importer.export.skin_import_policy import skin_weight_policy_assets


class SkinImportPolicyTests(unittest.TestCase):
    def test_only_edited_skin_exact_revision_is_opted_in(self):
        task=dict(kind='REBIND_SKINNED_RENDERER_V1',model_guid='a'*32,model_sha256='b'*64)
        asset,=skin_weight_policy_assets([task,dict(kind='OTHER')])
        value=json.loads(asset.asset_bytes)
        self.assertEqual(value,dict(version=1,model_guid='a'*32,model_sha256='b'*64))
        self.assertIn('a'*32,asset.pathname)
        source_task = dict(task, kind='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1')
        self.assertEqual(skin_weight_policy_assets([source_task]), (asset,))
        self.assertEqual(skin_weight_policy_assets([task,task]),(asset,))

    def test_missing_revision_or_conflicting_revision_rejects(self):
        task=dict(kind='RESTORE_MODEL_SKIN_VARIANT_V1',model_guid='a'*32,model_sha256='b'*64)
        for bad in [dict(task,model_guid='no'),dict(task,model_sha256=''),dict(kind=task['kind'])]:
            with self.assertRaises(ValueError):skin_weight_policy_assets([bad])
        with self.assertRaises(ValueError):skin_weight_policy_assets([task,dict(task,model_sha256='c'*64)])
