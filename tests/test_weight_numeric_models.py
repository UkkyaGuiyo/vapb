# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from .weight_numeric_models import models,representation_compare,f32,bits


class WeightNumericModelsTests(unittest.TestCase):
    def test_division_and_two_pass_counterexamples_are_distinct(self):
        values=[f32(v) for v in [.08581870049238205,.0663706362247467]]
        predicted=models(values)
        self.assertNotEqual(predicted['M4_sorted_float_divide'],predicted['M5_divide_then_reciprocal'])
        # Actual captured Unity values are checked by the public measurement test.

    def test_bitwise_comparator_rejects_one_ulp_and_wrong_identity(self):
        raw=dict(a=f32(.2),b=f32(.3));expected=dict(zip(raw,models(list(raw.values()))['M5_divide_then_reciprocal']))
        result=representation_compare(raw,raw,raw,expected,unity_version='2022.3.22f1')
        self.assertEqual(result['unity_representation'],'EXACT')
        self.assertEqual(result['raw_unity'],'RAW_VALUES_CHANGED')
        import struct
        changed=dict(expected);changed['a']=struct.unpack('<f',struct.pack('<I',bits(changed['a'])+1))[0]
        self.assertEqual(representation_compare(raw,raw,raw,changed,unity_version='2022.3.22f1')['unity_representation'],'NUMERIC_MISMATCH')
        with self.assertRaises(ValueError):representation_compare(raw,raw,raw,dict(expected,c=expected['a']),unity_version='2022.3.22f1')

    def test_unknown_context_rejects_and_staging_change_stays_visible(self):
        raw=dict(a=.5,b=.5)
        with self.assertRaises(ValueError):representation_compare(raw,raw,raw,raw,unity_version='6000.0')
        changed=dict(raw,a=.25)
        result=representation_compare(raw,changed,raw,raw,unity_version='2022.3.22f1')
        self.assertEqual(result['staging'],'STAGING_MISMATCH')
        with self.assertRaises(ValueError):representation_compare(dict(a=.1),dict(a=.1),dict(a=.1),dict(a=.1),unity_version='2022.3.22f1')

    def test_public_captured_values_are_bitwise_exact(self):
        import json
        from pathlib import Path
        report=json.loads((Path(__file__).parent/'unity_small_weight_probe/numeric_measurements.json').read_text())
        for case in report['controls']:
            labels=[w['bone'] for w in case['B0']['weights']]
            a={w['bone']:w['value'] for w in case['B0']['weights']}
            staged={w['bone']:w['value'] for w in case['B1']['weights']}
            raw={w['bone']:w['value'] for w in case['F']}
            actual={w['label']:w['value'] for w in case['U']['weights']}
            for w in case['U']['weights']:self.assertEqual(bits(w['value']),w['bits'])
            result=representation_compare(a,staged,raw,actual,unity_version=report['unity_version'])
            self.assertEqual(result['unity_representation'],'EXACT',case['label'])
            self.assertEqual(result['staging'],'EXACT')
            self.assertEqual(result['authored_fbx'],'EXACT')
        source=report['source_capture'];unity=report['unity_capture']
        raw_by_cp={}
        for cluster in source['clusters']:
            for weight in cluster['weights']:
                raw_by_cp.setdefault(weight['cp'],{})[cluster['bone_label']]=weight['weight']
        checked=0
        for first,repeated in zip(unity['first']['vertices'],unity['repeated']['vertices']):
            self.assertEqual(first['weights'],repeated['weights'])
            cp=first['cp']
            authored={w['bone']:w['value'] for w in source['B0'][cp]['weights']}
            staged={w['bone']:w['value'] for w in source['B1'][cp]['weights']}
            actual={w['label']:w['value'] for w in first['weights']}
            for w in first['weights']:self.assertEqual(bits(w['value']),w['bits'])
            result=representation_compare(authored,staged,raw_by_cp[cp],actual,unity_version=unity['version'])
            self.assertEqual(result['staging'],'EXACT')
            self.assertEqual(result['authored_fbx'],'EXACT')
            self.assertEqual(result['unity_representation'],'EXACT')
            checked+=len(actual)
        self.assertEqual(checked,183)
