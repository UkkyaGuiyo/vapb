# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail-closed correspondence and float32 weight comparisons for the ladder."""
import math
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def source_weights(source):
    if source['cp_count'] != len(source['ladder'])*3:
        raise ValueError('SOURCE_CP_SCOPE')
    raw = {}
    labels = set()
    for cluster in source['clusters']:
        label = cluster['bone_label']
        if label in labels: raise ValueError('SOURCE_BONE_AMBIGUOUS')
        labels.add(label)
        for row in cluster['weights']:
            key=(row['cp'], label)
            if key in raw or not 0 <= row['cp'] < source['cp_count']:
                raise ValueError('SOURCE_CP_MAPPING')
            raw[key]=row['weight']
    if labels != {'WEIGHT-BONE-0','WEIGHT-BONE-1'}: raise ValueError('SOURCE_BONE_SCOPE')
    for cp in range(source['cp_count']):
        low=source['ladder'][cp//3]
        for label,expected in [('WEIGHT-BONE-0',f32(low)),('WEIGHT-BONE-1',f32(1-low))]:
            if raw.get((cp,label),0) != expected: raise ValueError('SOURCE_WEIGHT_CHANGED')
    return raw


def compare(source, capture):
    raw=source_weights(source)
    if capture['hash'] != source['fbx_sha256']: raise ValueError('STALE_FBX_HASH')
    if capture['mesh_label'] != source['mesh_label']: raise ValueError('WRONG_MESH_ASSET')
    if set(capture['bones']) != {'WEIGHT-BONE-0','WEIGHT-BONE-1'} or len(capture['bones'])!=2:
        raise ValueError('BONE_MAPPING')
    seen=set(); rows=[]
    for v in capture['vertices']:
        cp=v['cp']
        if cp in seen or not 0<=cp<source['cp_count']:raise ValueError('CP_MAPPING')
        seen.add(cp); actual={}
        for w in v['influences']:
            if (not 0<=w['bone']<2 or capture['bones'][w['bone']]!=w['label']
                    or w['label'] in actual): raise ValueError('BONE_INDEX_MAPPING')
            actual[w['label']]=w['weight']
        exact=all(f32(actual.get(label,0))==raw.get((cp,label),0) for label in capture['bones'])
        distance=math.dist([v['baked'][k] for k in ['x','y','z']], [v['raw_cpu'][k] for k in ['x','y','z']])
        rows.append(dict(cp=cp,exact=exact,small_retained=actual.get('WEIGHT-BONE-0',0)>0,
                         sum=sum(actual.values()),deformation_distance=distance))
    if seen != set(range(source['cp_count'])):raise ValueError('CP_COVERAGE')
    return rows
