# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import unittest
import json
from pathlib import Path
from . import bounded_skin_roundtrip as report


class BoundedSkinRoundtripTests(unittest.TestCase):
    def fixture(self):
        # Explicit first-party identities; this unit fixture is not runtime proof.
        key = dict(package_sha256='a'*64, prefab_sha256='b'*64,
                   root_context_id='root-0', occurrence_id='occurrence-0',
                   prefab_guid='1'*32, renderer_file_id='-101', owner_file_id='102',
                   realization_id='mesh-0', model_guid='2'*32, fbx_sha256='c'*64,
                   mesh_local_id='-201', bone_ids=['bone-0','bone-1'], root_bone_id='bone-0')
        evidence = {name: dict(subject={field: copy.deepcopy(key[field]) for field in fields},
                              checks={field:'EXACT' for field in report.CHECKS[name]})
                    for name, fields in report.SUBJECTS.items()}
        evidence['skin']['report'] = dict(overall_supported_transport='PASS',identity='EXACT',
            influence_retention='EXACT',unity_representation='BITWISE_EXACT',
            raw_numeric='RAW_NUMERIC_DIFFERENCE',source_renderer_owner='UNMEASURED',
            deformation=dict(status='MEASURED_NONZERO'),reason='NONE',total_influences=4,
            unexplained_influences=0)
        return key,evidence

    def test_independent_pass_is_not_a_join(self):
        key,evidence=self.fixture()
        for row in evidence.values(): row.pop('subject')
        self.assertEqual(report.accept(key,evidence)['reason'],'CROSS_EVIDENCE_IDENTITY_UNPROVEN')

    def test_joined_pass_retains_independent_numeric_owner_and_boundaries(self):
        key,evidence=self.fixture(); before=copy.deepcopy(evidence)
        result=report.accept(key,evidence)
        self.assertEqual(result['supported_bounded_skin_roundtrip'],'PASS')
        self.assertEqual(result['renderer_owner'],'EXACT')
        self.assertEqual(result['skin']['source_renderer_owner'],'UNMEASURED')
        self.assertEqual(result['skin']['deformation']['status'],'MEASURED_NONZERO')
        self.assertEqual(evidence,before)

    def test_ten_cross_evidence_controls(self):
        mutations=[('hierarchy','package_sha256','d'*64),('hierarchy','occurrence_id','other-instance'),
            ('geometry','realization_id','other-mesh'),('skin','fbx_sha256','d'*64),
            ('hierarchy','owner_file_id','999'),('hierarchy','root_bone_id','bone-1'),
            ('geometry','fbx_sha256','e'*64),('material','renderer_file_id','998'),
            ('shape','mesh_local_id','997'),('finalizer','occurrence_id','repeated-instance')]
        for domain,field,value in mutations:
            with self.subTest(domain=domain,field=field):
                key,evidence=self.fixture(); evidence[domain]['subject'][field]=value
                self.assertEqual(report.accept(key,evidence)['supported_bounded_skin_roundtrip'],'RED')

    def test_missing_checks_and_unsupported_skin_cannot_pass(self):
        key,evidence=self.fixture();evidence['hierarchy']['checks'].pop('ordered_bones')
        self.assertEqual(report.accept(key,evidence)['supported_bounded_skin_roundtrip'],'UNSUPPORTED')
        key,evidence=self.fixture();evidence['skin']['report']['overall_supported_transport']='UNSUPPORTED'
        self.assertEqual(report.accept(key,evidence)['supported_bounded_skin_roundtrip'],'UNSUPPORTED')

    def test_ordered_bones_and_mandatory_failure_are_red(self):
        key,evidence=self.fixture();evidence['hierarchy']['subject']['bone_ids'].reverse()
        self.assertEqual(report.accept(key,evidence)['supported_bounded_skin_roundtrip'],'RED')
        key,evidence=self.fixture();evidence['finalizer']['checks']['repeated_apply']='RED'
        self.assertEqual(report.accept(key,evidence)['supported_bounded_skin_roundtrip'],'RED')

    def test_actual_summary_does_not_promote_unmeasured_stage_or_private_join(self):
        data=json.loads((Path(__file__).parent/'bounded_skin_roundtrip_measurements.json').read_text())
        self.assertEqual(data['public']['skin']['staging'],'UNMEASURED')
        self.assertEqual(data['public']['verdict'],'PASS')
        self.assertEqual(data['public']['skin']['source_renderer_owner'],'UNMEASURED')
        self.assertEqual(data['real']['verdict'],'UNSUPPORTED')
        self.assertEqual(data['real']['authoritative_joins'],0)
