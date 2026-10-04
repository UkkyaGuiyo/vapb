"""Exact public synthetic contract for a UV-seam Skin vertex-layout split.

Two source triangles share an edge. The final mesh duplicates both endpoints
for the second face, retaining two triangles and six indices. Duplicate
positions and Bone weights match their source vertices; a UV seam preserves
the split through model import.
"""

SOURCE_VERTICES = (
    (-1.0, -1.0, 0.0), (1.0, -1.0, 0.0),
    (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0),
)
SOURCE_FACES = ((0, 1, 2), (0, 2, 3))
SOURCE_FACE_UVS = (
    ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)),
    ((0.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
)
SOURCE_BONE_WEIGHTS = (
    (("Root", 1.0),), (("Root", 1.0),),
    (("Child", 1.0),), (("Child", 1.0),),
)
DUPLICATE_SOURCE_VERTICES = (0, 2)
DUPLICATE_FACE = 1


def make_vertex_split_contract(vertices=SOURCE_VERTICES, faces=SOURCE_FACES,
                               bone_weights=SOURCE_BONE_WEIGHTS,
                               face_uvs=SOURCE_FACE_UVS):
    """Return source/final rows for one deterministic shared-edge split."""
    vertices = tuple(tuple(float(c) for c in row) for row in vertices)
    faces = tuple(tuple(int(i) for i in face) for face in faces)
    bone_weights = tuple(tuple((str(name), float(weight)) for name, weight in row)
                         for row in bone_weights)
    face_uvs = tuple(tuple(tuple(float(axis) for axis in uv) for uv in face)
                     for face in face_uvs)
    if (len(vertices) != 4 or len(faces) != 2 or
            any(len(face) != 3 for face in faces) or len(bone_weights) != 4 or
            len(face_uvs) != 2 or any(len(face) != 3 for face in face_uvs)):
        raise ValueError("FIXTURE_SOURCE_LAYOUT_UNEXPECTED")
    if any(i < 0 or i >= len(vertices) for face in faces for i in face):
        raise ValueError("FIXTURE_SOURCE_INDEX_INVALID")
    shared = set(faces[0]).intersection(faces[1])
    if set(DUPLICATE_SOURCE_VERTICES) != shared:
        raise ValueError("FIXTURE_SHARED_EDGE_UNEXPECTED")

    duplicate_first = len(vertices)
    duplicate_second = duplicate_first + 1
    remap = dict(zip(DUPLICATE_SOURCE_VERTICES, (duplicate_first, duplicate_second)))
    final_vertices = vertices + tuple(vertices[index] for index in DUPLICATE_SOURCE_VERTICES)
    final_faces = list(faces)
    final_faces[DUPLICATE_FACE] = tuple(
        remap.get(index, index) for index in final_faces[DUPLICATE_FACE]
    )
    final_weights = bone_weights + tuple(
        bone_weights[index] for index in DUPLICATE_SOURCE_VERTICES
    )
    final_uvs = [tuple(face) for face in face_uvs]
    source_face_uvs = face_uvs[DUPLICATE_FACE]
    final_uvs[DUPLICATE_FACE] = tuple(
        (uv[0] + 0.25, uv[1]) if vertex in remap else uv
        for vertex, uv in zip(faces[DUPLICATE_FACE], source_face_uvs)
    )
    return {
        "source_vertices": vertices,
        "source_faces": faces,
        "source_bone_weights": bone_weights,
        "source_face_uvs": face_uvs,
        "final_vertices": final_vertices,
        "final_faces": tuple(final_faces),
        "final_bone_weights": final_weights,
        "final_face_uvs": tuple(final_uvs),
        "duplicate_source_vertices": DUPLICATE_SOURCE_VERTICES,
        "duplicate_final_vertices": (duplicate_first, duplicate_second),
        "duplicate_face": DUPLICATE_FACE,
    }


def validate_vertex_split_contract(contract):
    """Prove counts, face geometry, UV split, and copied Bone weights."""
    source_faces = contract["source_faces"]
    final_faces = contract["final_faces"]
    if (len(contract["source_vertices"]) != 4 or
            len(contract["final_vertices"]) != 6 or
            len(source_faces) != 2 or len(final_faces) != 2 or
            sum(map(len, source_faces)) != 6 or sum(map(len, final_faces)) != 6):
        raise ValueError("FIXTURE_COUNTS_UNEXPECTED")

    def triangles(vertices, faces):
        return tuple(sorted(tuple(sorted(vertices[i] for i in face)) for face in faces))

    if triangles(contract["source_vertices"], source_faces) != \
            triangles(contract["final_vertices"], final_faces):
        raise ValueError("FIXTURE_FACE_GEOMETRY_CHANGED")
    if (contract["final_bone_weights"][:4] != contract["source_bone_weights"] or
            contract["final_bone_weights"][4:] != tuple(
                contract["source_bone_weights"][index]
                for index in DUPLICATE_SOURCE_VERTICES)):
        raise ValueError("FIXTURE_BONE_WEIGHTS_CHANGED")
    if contract["final_faces"] != ((0, 1, 2), (4, 5, 3)):
        raise ValueError("FIXTURE_INDEX_REMAP_UNEXPECTED")
    expected_uvs = [tuple(face) for face in contract["source_face_uvs"]]
    expected_uvs[DUPLICATE_FACE] = tuple(
        (uv[0] + 0.25, uv[1]) if vertex in DUPLICATE_SOURCE_VERTICES else uv
        for vertex, uv in zip(source_faces[DUPLICATE_FACE], expected_uvs[DUPLICATE_FACE])
    )
    if contract["final_face_uvs"] != tuple(expected_uvs):
        raise ValueError("FIXTURE_UV_SEAM_UNEXPECTED")
    return True
