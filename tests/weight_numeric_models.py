# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact hypotheses, not tolerance-based acceptance rules."""
import struct
import math


def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def ulp(a,b):return abs(bits(a)-bits(b))  # nonnegative finite Skin weights only


def sum32(values):
    total=0.
    for value in values:total=f32(total+f32(value))
    return total


def models(values):
    q=[f32(v) for v in values]
    s64=sum(values);s32=sum32(values);qs64=sum(q)
    sorted32=sum32(sorted(q,reverse=True))
    predictions = {
        'M0_float32':q,
        'M1_double_normalize':[f32(v/s64) for v in values],
        'M2_float_divide':[f32(v/s32) for v in q],
        'M3_quantize_double_normalize':[f32(v/qs64) for v in q],
        'M4_sorted_float_divide':[f32(v/sorted32) for v in q],
        'M4_sorted_float_reciprocal':[f32(v*f32(1/sorted32)) for v in q],
    }
    first=predictions['M4_sorted_float_divide']
    second_sum=sum32(sorted(first,reverse=True))
    predictions['M5_divide_then_reciprocal']=[f32(v*f32(1/second_sum)) for v in first]
    return predictions


def representation_compare(authored, staged, raw, actual, *, unity_version):
    """Bounded diagnostic contract; never rewrites the legacy raw Skin verdict."""
    if unity_version!='2022.3.22f1' or not 1<=len(raw)<=4:
        raise ValueError('UNPROVEN_NUMERIC_SCOPE')
    keys=list(raw)
    if any(set(row)!=set(raw) for row in [authored,staged,actual]):
        raise ValueError('BONE_ID_SET_CHANGED')
    if any(not math.isfinite(v) or v<=0 or f32(v)!=v for row in [authored,staged,raw,actual] for v in row.values()):
        raise ValueError('UNPROVEN_WEIGHT_REPRESENTATION')
    predicted=models([raw[k] for k in keys])['M5_divide_then_reciprocal']
    rows=[dict(bone=k,AUTHORED=authored[k],STAGED=staged[k],FBX_CANONICAL=raw[k],
               UNITY_EXPECTED=p,UNITY_ACTUAL=actual[k],expected_bits=bits(p),actual_bits=bits(actual[k]),
               expected_actual_ULP=ulp(p,actual[k])) for k,p in zip(keys,predicted)]
    return dict(staging='EXACT' if authored==staged else 'STAGING_MISMATCH',
                authored_fbx='EXACT' if staged==raw else 'AUTHORED_FBX_CHANGED',
                raw_unity='EXACT' if raw==actual else 'RAW_VALUES_CHANGED',
                unity_representation='EXACT' if all(r['expected_actual_ULP']==0 for r in rows) else 'NUMERIC_MISMATCH',rows=rows)
