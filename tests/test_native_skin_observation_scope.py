# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import unittest
from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observation_records
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity


def record(renderer):
    row = dict(renderer_class_id=137, root_context_id='public-root', root_package_id='sha256:'+'1'*64,
               root_member_id='public-member', root_asset_guid='a'*32, instance_edge_path=[],
               source_package_id='sha256:'+'1'*64,
               source_key=dict(source_asset_guid='a'*32, renderer_file_id=renderer))
    row['occurrence_id'] = occurrence_identity(row)
    return row


class NativeSkinObservationScopeTests(unittest.TestCase):
    def setUp(self):
        self.selected, self.other = record('11'), record('22')
        self.projection = dict(records=[self.selected, self.other], issues=[])

    def test_scoped_other_verified_issue_is_retained_without_blocking_selected(self):
        self.projection['issues'] = [dict(code='CHANNEL_IDENTITY_UNPROVEN', occurrence_id=self.other['occurrence_id'])]
        before = copy.deepcopy(self.projection)
        self.assertEqual(observation_records(self.projection, self.selected['occurrence_id']), [self.selected])
        self.assertEqual(self.projection, before)
        with self.assertRaisesRegex(ValueError, 'PERSISTED_PROJECTION_HAS_ISSUES'):
            observation_records(self.projection)

    def test_selected_and_global_issues_reject(self):
        for issue in (dict(code='CHANNEL_IDENTITY_UNPROVEN', occurrence_id=self.selected['occurrence_id']),
                      dict(code='GLOBAL_ISSUE'), dict(code='GLOBAL_ISSUE', occurrence_id=None)):
            self.projection['issues'] = [issue]
            with self.assertRaisesRegex(ValueError, 'PERSISTED_PROJECTION_HAS_ISSUES'):
                observation_records(self.projection, self.selected['occurrence_id'])

    def test_unknown_or_unverified_issue_occurrence_rejects(self):
        self.projection['issues'] = [dict(code='ISSUE', occurrence_id='unknown')]
        with self.assertRaisesRegex(ValueError, 'ISSUE_OCCURRENCE_UNPROVEN'):
            observation_records(self.projection, self.selected['occurrence_id'])
        self.projection['issues'][0]['occurrence_id'] = self.other['occurrence_id']
        self.other['root_context_id'] = 'mutated'
        with self.assertRaisesRegex(ValueError, 'ISSUE_OCCURRENCE_UNPROVEN'):
            observation_records(self.projection, self.selected['occurrence_id'])

    def test_missing_or_duplicate_selected_record_rejects(self):
        with self.assertRaisesRegex(ValueError, 'SELECTED_OCCURRENCE_NOT_UNIQUE'):
            observation_records(self.projection, 'missing')
        self.projection['records'].append(self.selected)
        with self.assertRaisesRegex(ValueError, 'SELECTED_OCCURRENCE_NOT_UNIQUE'):
            observation_records(self.projection, self.selected['occurrence_id'])

    def test_default_unscoped_records_are_unchanged(self):
        self.assertEqual(observation_records(self.projection), self.projection['records'])


if __name__ == '__main__':
    unittest.main()
