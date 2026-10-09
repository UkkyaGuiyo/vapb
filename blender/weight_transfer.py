"""Small, Blender independent numerical policies for manual weight transfer."""

from __future__ import annotations


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


DECLARED_PLANE_EPSILON = 1e-5


def crosses_declared_plane(target_local_x, source_local_x, epsilon=DECLARED_PLANE_EPSILON):
    """True only for unambiguous opposite sides of a user-declared local X=0 plane."""
    return (abs(target_local_x) > epsilon and abs(source_local_x) > epsilon
            and target_local_x * source_local_x < 0)


def closest_triangle_weights(point, a, b, c):
    """Barycentric coordinates of the nearest point on triangle abc.

    Uses the triangle's edges and vertices when the projection falls outside.
    Degenerate triangles fall back to the closest vertex.
    """
    ab, ac, ap = _sub(b, a), _sub(c, a), _sub(point, a)
    area_squared = _dot(ab, ab) * _dot(ac, ac) - _dot(ab, ac) ** 2
    if area_squared <= 1e-20:
        vertices = (a, b, c)
        best = None
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = _sub(vertices[j], vertices[i])
            length_squared = _dot(edge, edge)
            if length_squared <= 1e-20:
                continue
            t = max(0.0, min(1.0, _dot(_sub(point, vertices[i]), edge) / length_squared))
            near = tuple(vertices[i][k] + t * edge[k] for k in range(3))
            distance_squared = _dot(_sub(point, near), _sub(point, near))
            if best is None or distance_squared < best[0]:
                weights = [0.0, 0.0, 0.0]
                weights[i], weights[j] = 1.0 - t, t
                best = (distance_squared, tuple(weights))
        return best[1] if best is not None else (1.0, 0.0, 0.0)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return (1.0, 0.0, 0.0)
    bp = _sub(point, b)
    d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return (0.0, 1.0, 0.0)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return (1.0 - v, v, 0.0)
    cp = _sub(point, c)
    d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return (0.0, 0.0, 1.0)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return (1.0 - w, 0.0, w)
    va = d3 * d6 - d5 * d4
    if va <= 0 and d4 - d3 >= 0 and d5 - d6 >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (0.0, 1.0 - w, w)
    denom = va + vb + vc
    v, w = vb / denom, vc / denom
    return (1.0 - v - w, v, w)


def combine_weight(existing, sampled, mode, blend):
    """REPLACE interpolates, MERGE retains the larger value, FILL only adds absent weights."""
    if mode == 'REPLACE':
        proposed = sampled
    elif mode == 'MERGE':
        proposed = max(existing, sampled)
    elif mode == 'FILL_MISSING':
        proposed = sampled if existing == 0.0 else existing
    else:
        raise ValueError('Unknown weight transfer mode')
    return max(0.0, min(1.0, existing + (proposed - existing) * blend))
