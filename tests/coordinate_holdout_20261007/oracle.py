"""Pure arithmetic oracle for the frozen coordinate candidate."""
from __future__ import annotations
import math

from contract import CWORLD, TOLERANCE, validate_contract

EXPECTED_U_TAGS = tuple(100.0 + 8.0 * face + corner for face in range(6) for corner in range(3))


def validate_u_tags(observed_tags):
    """Validate exact authored U identities; V is retained as a diagnostic."""
    values = [float(value) for value in observed_tags]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("CORNER_TAG_NONFINITE")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("CORNER_TAG_NONFINITE")
    if len(values) != len(set(values)):
        raise ValueError("CORNER_TAG_DUPLICATE")
    if len(values) != len(EXPECTED_U_TAGS) or set(values) != set(EXPECTED_U_TAGS):
        raise ValueError("CORNER_TAG_SET_MISMATCH")


def matrix4(value):
    if len(value) != 4 or any(len(row) != 4 for row in value):
        raise ValueError("MATRIX_SHAPE_INVALID")
    result = tuple(tuple(float(x) for x in row) for row in value)
    if not all(math.isfinite(x) for row in result for x in row):
        raise ValueError("MATRIX_NONFINITE")
    return result


def multiply(a, b):
    a, b = matrix4(a), matrix4(b)
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)) for r in range(4))


def point(m, v):
    m = matrix4(m)
    if len(v) != 3 or not all(math.isfinite(float(x)) for x in v):
        raise ValueError("POINT_INVALID")
    q = [sum(m[r][c] * (float(v[c]) if c < 3 else 1.0) for c in range(4)) for r in range(4)]
    if not all(math.isfinite(x) for x in q):
        raise ValueError("TRANSFORM_NONFINITE")
    if abs(q[3]) < 1.e-12:
        raise ValueError("POINT_W_ZERO")
    return tuple(x / q[3] for x in q[:3])


def local_matrix(unit_ratio):
    s = float(unit_ratio)
    if not math.isfinite(s) or s <= 0:
        raise ValueError("UNIT_RATIO_INVALID")
    return ((-s, 0., 0., 0.), (0., s, 0., 0.), (0., 0., s, 0.), (0., 0., 0., 1.))


def residuals(vb, vu, wb, wu, unit_ratio):
    d = local_matrix(unit_ratio)
    converted = point(d, vb)
    candidate_world = point(CWORLD, point(wb, vb))
    actual_world = point(wu, vu)
    chain_world = point(wu, converted)
    mat_a, mat_b = multiply(wu, d), multiply(CWORLD, wb)
    return {
        "local": tuple(vu[i] - converted[i] for i in range(3)),
        "world_matrix": tuple(tuple(mat_a[r][c] - mat_b[r][c] for c in range(4)) for r in range(4)),
        "world_matrix_chain_point": tuple(chain_world[i] - candidate_world[i] for i in range(3)),
        "world_point": tuple(actual_world[i] - candidate_world[i] for i in range(3)),
    }


def maxima_for_case(blender_points, unity_points, blender_world, unity_world, unit_ratio):
    errors = validate_contract()
    if errors:
        raise ValueError("CONTRACT_INVALID:" + ",".join(errors))
    validate_u_tags(blender_points.keys())
    validate_u_tags(unity_points.keys())
    if set(blender_points) != set(unity_points):
        raise ValueError("CORNER_TAG_SET_MISMATCH")
    values = {key: 0.0 for key in ("local", "world_matrix", "world_matrix_chain_point", "world_point")}
    for tag in sorted(blender_points):
        r = residuals(blender_points[tag], unity_points[tag], blender_world, unity_world, unit_ratio)
        for key in values:
            flat = (x for row in r[key] for x in row) if key == "world_matrix" else iter(r[key])
            values[key] = max(values[key], *(abs(x) for x in flat))
    return values


def verdict(maxima, tolerance=TOLERANCE):
    if not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("TOLERANCE_INVALID")
    accepted = ("local", "world_matrix", "world_point")
    diagnostic = ("world_matrix_chain_point",)
    required = accepted + diagnostic
    if set(maxima) != set(required) or any(not math.isfinite(float(maxima[k])) for k in required):
        raise ValueError("RESIDUAL_SET_OR_FINITE_INVALID")
    if any(float(maxima[k]) < 0.0 for k in required):
        raise ValueError("RESIDUAL_NEGATIVE")
    return "PASS" if all(float(maxima[k]) <= tolerance for k in accepted) else "FAIL"


def authored_trs(location, rotation_degrees, scale):
    """Build T * Rz * Ry * Rx * S from authored XYZ Euler values, no Blender dependency."""
    x, y, z = (math.radians(float(v)) for v in rotation_degrees)
    sx, sy, sz = (math.sin(v) for v in (x, y, z))
    cx, cy, cz = (math.cos(v) for v in (x, y, z))
    rx = ((1.,0.,0.,0.), (0.,cx,-sx,0.), (0.,sx,cx,0.), (0.,0.,0.,1.))
    ry = ((cy,0.,sy,0.), (0.,1.,0.,0.), (-sy,0.,cy,0.), (0.,0.,0.,1.))
    rz = ((cz,-sz,0.,0.), (sz,cz,0.,0.), (0.,0.,1.,0.), (0.,0.,0.,1.))
    sm = ((float(scale[0]),0.,0.,0.), (0.,float(scale[1]),0.,0.), (0.,0.,float(scale[2]),0.), (0.,0.,0.,1.))
    tm = ((1.,0.,0.,float(location[0])), (0.,1.,0.,float(location[1])),
          (0.,0.,1.,float(location[2])), (0.,0.,0.,1.))
    return multiply(multiply(multiply(multiply(tm, rz), ry), rx), sm)


def expected_unity_world(blender_world, unit_ratio):
    """Solve the frozen equation W_U D = C W_B for W_U using diagonal D."""
    d = local_matrix(unit_ratio)
    rhs = multiply(CWORLD, blender_world)
    diagonal = (-float(unit_ratio), float(unit_ratio), float(unit_ratio), 1.)
    return tuple(tuple(rhs[r][c] / diagonal[c] for c in range(4)) for r in range(4))


def scale_authored_world(matrix, unit_ratio):
    """Apply authored unit ratio to the Blender world affine rows, preserving homogeneous row."""
    s = float(unit_ratio)
    if not math.isfinite(s) or s <= 0.0:
        raise ValueError("UNIT_RATIO_INVALID")
    m = matrix4(matrix)
    return tuple(tuple(m[r][c] * s if r < 3 else m[r][c] for c in range(4)) for r in range(4))
