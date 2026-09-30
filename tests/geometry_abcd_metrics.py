# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit-marker metrics; geometric distance never establishes identity."""
from collections import Counter, defaultdict
import math

POSITION_TOLERANCE = 3e-5  # Existing source-geometry diagnostic threshold.


def triangle_multiset(triangles):
    return Counter(tuple(sorted(triangle)) for triangle in triangles)


def oriented_triangles(triangles, handedness_reversed=False):
    result=[]
    for triangle in triangles:
        a,b,c=triangle
        if handedness_reversed:b,c=c,b
        result.append(min((a,b,c),(b,c,a),(c,a,b)))
    return Counter(result)


def point_map(labels, positions):
    if len(labels) != len(positions) or any(p is None for p in labels):
        raise ValueError('POINT_IDENTITY_UNPROVEN')
    result = defaultdict(list)
    for label, position in zip(labels, positions):
        if not isinstance(label, int) or label < 0 or len(position) != 3 or not all(map(math.isfinite, position)):
            raise ValueError('POINT_IDENTITY_UNPROVEN')
        result[label].append(position)
    return result


def position_metric(a_labels, a_positions, b_labels, b_positions):
    a, b = point_map(a_labels, a_positions), point_map(b_labels, b_positions)
    if set(a) != set(b):
        return dict(status='POINT_COVERAGE_MISMATCH', missing=len(set(a)-set(b)), added=len(set(b)-set(a)))
    # Identity is already explicit. Include all split vertices, not nearest-match repair.
    maximum = max(math.dist(x,y) for key in a for x in a[key] for y in b[key])
    return dict(status='EXACT' if maximum <= POSITION_TOLERANCE else 'POSITION_MISMATCH',
                maximum_distance=maximum, tolerance=POSITION_TOLERANCE)


def weight_value_sets(labels, weights):
    result = defaultdict(set)
    for label, row in zip(labels, weights):
        result[label].add(tuple(sorted(round(value,6) for value in row if value > 0)))
    return dict(result)


def corner_values_by_point(triangles, values, digits=6):
    if len(values) != 3*len(triangles):
        raise ValueError('CORNER_ATTRIBUTE_COVERAGE_MISMATCH')
    result = defaultdict(set)
    for labels, row in zip(triangles, [values[i:i+3] for i in range(0,len(values),3)]):
        for label, value in zip(labels, row):
            result[label].add(tuple(round(x,digits) for x in value))
    return dict(result)


def attribute_set_distance(a_triangles,a_values,b_triangles,b_values):
    """Attribute distance after CP identity; no new acceptance tolerance."""
    a=corner_values_by_point(a_triangles,a_values,12)
    b=corner_values_by_point(b_triangles,b_values,12)
    if set(a)!=set(b):
        return dict(status='ATTRIBUTE_POINT_COVERAGE_MISMATCH')
    forward=max(min(math.dist(x,y) for y in b[cp]) for cp in a for x in a[cp])
    backward=max(min(math.dist(y,x) for x in a[cp]) for cp in b for y in b[cp])
    return dict(status='DISTANCE_OBSERVED',maximum_distance=max(forward,backward),
                limitation='CP_VALUE_SETS_NOT_TRIANGLE_CORNER_BIJECTION_NO_ACCEPTANCE_THRESHOLD')


def material_label_partitions(point_triangles, slots, labels):
    """Effective Material identity partitions, independent of submesh numbering."""
    from collections import Counter
    if len(point_triangles) != len(slots):
        raise ValueError('MATERIAL_PARTITION_LENGTH_MISMATCH')
    result = Counter()
    for triangle, slot in zip(point_triangles, slots):
        if not 0 <= slot < len(labels) or not labels[slot] or not labels[slot].startswith('VAPB-EXP-MAT-'):
            raise ValueError('MATERIAL_EXPORT_LABEL_UNPROVEN')
        result[labels[slot],tuple(sorted(triangle))] += 1
    return result
