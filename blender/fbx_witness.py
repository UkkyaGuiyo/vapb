"""Prepare source-preserving FBX witnesses for deferred Unity identity checks.

Uses installed Blender FBX APIs. A witness is not identity evidence until the
Unity importer verifies original/noop/witness/restored state for that source.
"""
import array
import hashlib
import math
from pathlib import Path
import struct


PROPERTY = b'_vapb_source_fbx_model_uid'
METHODS = {
    ord('B'): 'add_bool', ord('C'): 'add_char', ord('Z'): 'add_int8',
    ord('Y'): 'add_int16', ord('I'): 'add_int32', ord('L'): 'add_int64',
    ord('F'): 'add_float32', ord('D'): 'add_float64', ord('R'): 'add_bytes',
    ord('S'): 'add_string', ord('i'): 'add_int32_array', ord('l'): 'add_int64_array',
    ord('f'): 'add_float32_array', ord('d'): 'add_float64_array',
    ord('b'): 'add_bool_array', ord('c'): 'add_byte_array',
}


def source_shape_channel_uids(source, geometry_uid):
    """Exact OO graph for single-frame/100-percent channels; no label matching."""
    from io_scene_fbx import parse_fbx
    root, _ = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(n for n in root.elems if n.id == b'Objects')
    nodes = {n.props[0]: n for n in objects.elems}
    if len(nodes) != len(objects.elems):
        raise ValueError('DUPLICATE_FBX_UID')
    edges = {}
    for row in next(n for n in root.elems if n.id == b'Connections').elems:
        if row.id == b'C' and len(row.props) == 3 and row.props[0] == b'OO':
            edges.setdefault(row.props[2], []).append(row.props[1])

    def kind(uid, element, subtype):
        n = nodes.get(uid)
        return n is not None and n.id == element and len(n.props) > 2 and n.props[2] == subtype

    geometry_uid = int(geometry_uid)
    if not kind(geometry_uid, b'Geometry', b'Mesh'):
        raise ValueError('SHAPE_GEOMETRY_MISSING')
    result = {}
    for blend in edges.get(geometry_uid, []):
        if not kind(blend, b'Deformer', b'BlendShape'):
            continue
        for channel in edges.get(blend, []):
            if not kind(channel, b'Deformer', b'BlendShapeChannel'):
                raise ValueError('SHAPE_CHANNEL_GRAPH_UNPROVEN')
            shapes = [uid for uid in edges.get(channel, []) if kind(uid, b'Geometry', b'Shape')]
            full = [n.props[0] for n in nodes[channel].elems if n.id == b'FullWeights']
            if (len(shapes) != 1 or len(full) != 1 or not len(full[0])
                    or any(value != 100.0 for value in full[0]) or channel in result):
                raise ValueError('SHAPE_FRAME_UNSUPPORTED')
            result[channel] = shapes[0]
    return result


def source_export_scale_options(source, scene_unit_scale):
    """Keep the two verified FBX unit conventions without guessing other units."""
    from io_scene_fbx import parse_fbx
    if not math.isclose(scene_unit_scale, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError('Skin export requires the verified scene unit scale of 1')
    decoded, _ = parse_fbx.parse(str(source), use_namedtuple=True)
    settings = [node for node in decoded.elems if node.id == b'GlobalSettings']
    if len(settings) != 1:
        raise ValueError('Source FBX unit settings are missing or duplicated')
    containers = [node for node in settings[0].elems if node.id == b'Properties70']
    if len(containers) != 1:
        raise ValueError('Source FBX unit properties are missing or duplicated')
    properties = [node for node in containers[0].elems
                  if node.id == b'P' and node.props and node.props[0] == b'UnitScaleFactor']
    if len(properties) != 1 or len(properties[0].props) != 5:
        raise ValueError('Source FBX unit scale is missing or duplicated')
    value = properties[0].props[-1]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Source FBX unit scale is invalid')
    if math.isclose(value, 1.0, rel_tol=0.0, abs_tol=1e-9):
        return 'FBX_SCALE_NONE'
    if math.isclose(value, 100.0, rel_tol=0.0, abs_tol=1e-9):
        return 'FBX_SCALE_ALL'
    raise ValueError('Source FBX unit convention is not yet supported for skin restoration')


def unity_skin_expected_bits(values, unity_version):
    """Existing M5 representation, only in its proven positive float32 scope."""
    values = tuple(values)
    if (unity_version != '2022.3.22f1' or not 1 <= len(values) <= 4 or
            any(type(v) is not float or not math.isfinite(v) or v < 2**-126 for v in values)):
        raise ValueError('UNPROVEN_SKIN_NUMERIC_SCOPE')
    f32 = lambda value: struct.unpack('<f', struct.pack('<f', value))[0]
    try:
        if any(f32(value) != value for value in values):
            raise ValueError('UNPROVEN_SKIN_NUMERIC_SCOPE')
        total = 0.0
        for value in sorted(values, reverse=True):
            total = f32(total + value)
        first = tuple(f32(value / total) for value in values)
        second_total = 0.0
        for value in sorted(first, reverse=True):
            second_total = f32(second_total + value)
        reciprocal = f32(1.0 / second_total)
        expected = tuple(f32(value * reciprocal) for value in first)
    except (OverflowError, ZeroDivisionError, struct.error) as error:
        raise ValueError('UNPROVEN_SKIN_NUMERIC_SCOPE') from error
    if any(not math.isfinite(value) or value < 2**-126 for value in expected):
        raise ValueError('UNPROVEN_SKIN_NUMERIC_SCOPE')
    return tuple(struct.unpack('<I', struct.pack('<f', value))[0] for value in expected)


def prepare_export_weight_witness(source, noop, stamped, realization_id, bone_mappings):
    """Read canonical exported weights and stamp a spare UV only in private copies."""
    from io_scene_fbx import encode_bin, parse_fbx
    source, noop, stamped = map(Path, (source, noop, stamped))
    if len({p.resolve() for p in (source, noop, stamped)}) != 3 or noop.exists() or stamped.exists():
        raise ValueError('WEIGHT_WITNESS_OUTPUT_OCCUPIED')
    before = source.read_bytes()
    root, version = parse_fbx.parse(str(source), use_namedtuple=True)
    objects, = [n for n in root.elems if n.id == b'Objects']
    connections, = [n for n in root.elems if n.id == b'Connections']
    nodes = {n.props[0]: n for n in objects.elems}
    if len(nodes) != len(objects.elems):
        raise ValueError('WEIGHT_FBX_IDENTITY_DUPLICATED')
    def marker(node, name):
        values = [p.props[-1] for container in node.elems if container.id == b'Properties70'
                  for p in container.elems if p.id == b'P' and p.props and p.props[0] == name]
        if len(values) > 1:
            raise ValueError('WEIGHT_RECEIPT_DUPLICATED')
        return values[0].decode('utf8') if values else None
    model, = [n for n in objects.elems if n.id == b'Model' and n.props[2] == b'Mesh'
              and marker(n, b'_vapb_fbx_realization_id') == realization_id]
    edges = [row.props[1:3] for row in connections.elems
             if row.id == b'C' and row.props[0] == b'OO' and len(row.props) == 3]
    incoming = {}
    for child, parent in edges:
        incoming.setdefault(parent, []).append(child)
    geometry, = [nodes[uid] for uid in incoming.get(model.props[0], [])
                 if nodes[uid].id == b'Geometry' and nodes[uid].props[2] == b'Mesh']
    if [parent for child, parent in edges if child == geometry.props[0]] != [model.props[0]]:
        raise ValueError('SHARED_GEOMETRY_WEIGHT_WITNESS_UNSUPPORTED')
    vertices, = [n.props[0] for n in geometry.elems if n.id == b'Vertices']
    count = len(vertices) // 3
    existing = [n for n in geometry.elems if n.id == b'LayerElementUV']
    channel = len(existing)
    if len(vertices) % 3 or not 0 < count < 2**24:
        raise ValueError('CONTROL_POINT_RANGE_UNSUPPORTED')
    if channel >= 8 or [n.props[0] for n in existing] != list(range(channel)):
        raise ValueError('NO_SPARE_WEIGHT_UV_CHANNEL')
    skin, = [uid for uid in incoming.get(geometry.props[0], [])
             if nodes[uid].id == b'Deformer' and nodes[uid].props[2] == b'Skin']
    receipts = {row['edited_bone_realization_id'] for row in bone_mappings}
    if not receipts or len(receipts) != len(bone_mappings):
        raise ValueError('WEIGHT_BONE_RECEIPTS_INVALID')
    points = [{} for _ in range(count)]
    seen = set()
    for cluster_uid in incoming.get(skin, []):
        cluster = nodes[cluster_uid]
        if cluster.id != b'Deformer' or cluster.props[2] != b'Cluster':
            raise ValueError('WEIGHT_CLUSTER_INVALID')
        bone_uid, = incoming.get(cluster_uid, [])
        bone = nodes[bone_uid]
        receipt = marker(bone, b'_vapb_fbx_bone_realization_id')
        if bone.id != b'Model' or bone.props[2] != b'LimbNode' or receipt not in receipts or receipt in seen:
            raise ValueError('WEIGHT_BONE_RECEIPT_INVALID')
        seen.add(receipt)
        indices = [n.props[0] for n in cluster.elems if n.id == b'Indexes']
        weights = [n.props[0] for n in cluster.elems if n.id == b'Weights']
        if not indices and not weights:
            continue
        if len(indices) != 1 or len(weights) != 1 or len(indices[0]) != len(weights[0]):
            raise ValueError('WEIGHT_CLUSTER_ARRAYS_INVALID')
        if len(set(indices[0])) != len(indices[0]):
            raise ValueError('WEIGHT_CP_DUPLICATED')
        for cp, weight in zip(indices[0], weights[0]):
            if type(cp) is not int or not 0 <= cp < count or not math.isfinite(weight) or weight < 0:
                raise ValueError('WEIGHT_CP_OR_VALUE_INVALID')
            if weight > 0:
                points[cp][receipt] = weight
    if seen != receipts:
        raise ValueError('WEIGHT_BONE_MEMBERSHIP_CHANGED')
    rows = []
    for cp, values in enumerate(points):
        bits = unity_skin_expected_bits(tuple(values.values()), '2022.3.22f1')
        rows.append(dict(cp=cp, bone_realization_ids=list(values),
            raw_bits=[struct.unpack('<I', struct.pack('<f', v))[0] for v in values.values()],
            expected_bits=list(bits)))
    baseline = canonical(root)
    def element(parent, name, method=None, value=None):
        node = encode_bin.FBXElem(name); parent.elems.append(node)
        if method:
            getattr(node, method)(value)
        return node
    for destination, add_marker in ((noop, False), (stamped, True)):
        encoded = encode_node(root, False)
        if add_marker:
            encoded_objects = next(n for n in encoded.elems if n.id == b'Objects')
            position, = [i for i,n in enumerate(objects.elems) if n.props[0] == geometry.props[0]]
            target = encoded_objects.elems[position]
            uv = element(target, b'LayerElementUV', 'add_int32', channel)
            element(uv, b'Version', 'add_int32', 101)
            element(uv, b'Name', 'add_string', b'VAPB_CONTROL_POINT_INDEX')
            element(uv, b'MappingInformationType', 'add_string', b'ByVertice')
            element(uv, b'ReferenceInformationType', 'add_string', b'Direct')
            element(uv, b'UV', 'add_float64_array', [v for i in range(count) for v in (float(i+1), .375)])
            layer_positions = [i for i,n in enumerate(geometry.elems) if n.id == b'Layer' and n.props[0] == channel]
            if len(layer_positions) > 1:
                raise ValueError('WEIGHT_UV_LAYER_DUPLICATED')
            layer = target.elems[layer_positions[0]] if layer_positions else element(target, b'Layer', 'add_int32', channel)
            if not layer_positions:
                element(layer, b'Version', 'add_int32', 100)
            reference = element(layer, b'LayerElement')
            element(reference, b'Type', 'add_string', b'LayerElementUV')
            element(reference, b'TypedIndex', 'add_int32', channel)
        encode_bin.write(str(destination), encoded, version)
        decoded, after_version = parse_fbx.parse(str(destination), use_namedtuple=True)
        if add_marker:
            target = next(n for n in next(n for n in decoded.elems if n.id == b'Objects').elems
                          if n.props[0] == geometry.props[0])
            uv, = [n for n in target.elems if n.id == b'LayerElementUV' and n.props[0] == channel]
            values, = [n.props[0] for n in uv.elems if n.id == b'UV']
            if list(values) != [v for i in range(count) for v in (float(i+1), .375)]:
                raise ValueError('WEIGHT_CP_MARKER_CHANGED')
            target.elems.remove(uv)
            layer, = [n for n in target.elems if n.id == b'Layer' and n.props[0] == channel]
            reference, = [n for n in layer.elems if n.id == b'LayerElement' and
                any(child.id == b'Type' and child.props == [b'LayerElementUV'] for child in n.elems)]
            layer.elems.remove(reference)
            if not any(n.id == b'Layer' and n.props[0] == channel for n in geometry.elems):
                target.elems.remove(layer)
        if version != after_version or canonical(decoded) != baseline:
            raise ValueError('WEIGHT_WITNESS_NON_MARKER_DATA_CHANGED')
    if source.read_bytes() != before:
        raise ValueError('WEIGHT_WITNESS_SOURCE_CHANGED')
    return dict(version=1, unity_version='2022.3.22f1', control_point_count=count,
                uv_channel=channel, points=rows)


def source_skin_bone_uids(source, model_uid, geometry_uid, *, ordered=False):
    """Read one original Skin's explicit bone membership, including empty clusters."""
    from io_scene_fbx import parse_fbx
    decoded, _ = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = [node for node in decoded.elems if node.id == b'Objects']
    connections = [node for node in decoded.elems if node.id == b'Connections']
    if len(objects) != 1 or len(connections) != 1:
        raise ValueError('Source FBX skin graph is unavailable')
    by_uid = {}
    for node in objects[0].elems:
        if (not node.props or type(node.props[0]) is not int or
                not node.props[0] or node.props[0] in by_uid):
            raise ValueError('Source FBX object identity is invalid or duplicated')
        by_uid[node.props[0]] = node
    incoming = {}
    for row in connections[0].elems:
        if row.id == b'C' and row.props and row.props[0] == b'OO':
            if len(row.props) != 3 or any(type(uid) is not int for uid in row.props[1:]):
                raise ValueError('Source FBX object connection is invalid')
            incoming.setdefault(row.props[2], []).append(row.props[1])

    def kind(uid, element, subtype=None):
        node = by_uid.get(uid)
        return (node is not None and node.id == element and
                (subtype is None or len(node.props) > 2 and node.props[2] == subtype))

    model, geometry = int(model_uid), int(geometry_uid)
    if (not kind(model, b'Model') or not kind(geometry, b'Geometry', b'Mesh') or
            incoming.get(model, []).count(geometry) != 1):
        raise ValueError('Source FBX Model and Geometry relation is invalid')
    skins = [uid for uid in incoming.get(geometry, []) if kind(uid, b'Deformer', b'Skin')]
    if len(skins) != 1:
        raise ValueError('Source FBX skin is missing or ambiguous')
    clusters = incoming.get(skins[0], [])
    if (not clusters or len(set(clusters)) != len(clusters) or
            any(not kind(uid, b'Deformer', b'Cluster') for uid in clusters)):
        raise ValueError('Source FBX skin clusters are missing or ambiguous')
    bones = []
    for uid in clusters:
        linked = [bone for bone in incoming.get(uid, []) if kind(bone, b'Model')]
        if len(linked) != 1:
            raise ValueError('Source FBX cluster bone is missing or ambiguous')
        bones.append(str(linked[0]))
    if len(set(bones)) != len(bones):
        raise ValueError('Source FBX skin bone membership is duplicated')
    return tuple(bones) if ordered else frozenset(bones)


def ordered_skin_cluster_connections(objects, connections, bone_mappings, source_bone_order):
    """Preserve the original Skin's cluster-link sequence using exact Bone receipts."""
    order = tuple(source_bone_order)
    mapping = {}
    for row in bone_mappings:
        uid, receipt = row['source_model_uid'], row['edited_bone_realization_id']
        if not uid or not receipt or uid in mapping or receipt in mapping.values():
            raise ValueError('Skin Bone receipts are missing or duplicated')
        mapping[uid] = receipt
    if not order or len(set(order)) != len(order) or set(order) != set(mapping):
        raise ValueError('Source Skin cluster order is incomplete or duplicated')
    nodes = {}
    selected = {}
    for node in objects:
        if (not node.props or type(node.props[0]) is not int or
                not node.props[0] or node.props[0] in nodes):
            raise ValueError('Exported FBX object identity is invalid or duplicated')
        uid = node.props[0]
        nodes[uid] = node
        markers = [p.props[-1] for container in node.elems if container.id == b'Properties70'
                   for p in container.elems if p.id == b'P' and p.props and
                   p.props[0] == b'_vapb_fbx_bone_realization_id']
        if markers:
            if (node.id != b'Model' or len(node.props) < 3 or node.props[2] != b'LimbNode'
                    or len(markers) != 1 or not isinstance(markers[0], bytes)):
                raise ValueError('Exported Bone receipt has an invalid semantic role')
            receipt = markers[0].decode('utf8')
            if receipt not in mapping.values() or receipt in selected:
                raise ValueError('Exported Bone receipt is unknown or duplicated')
            selected[receipt] = uid
    if set(selected) != set(mapping.values()):
        raise ValueError('Exported Bone receipts are incomplete')
    skins = [uid for uid,n in nodes.items() if n.id == b'Deformer' and len(n.props) == 3 and n.props[2] == b'Skin']
    clusters = {uid for uid,n in nodes.items() if n.id == b'Deformer' and len(n.props) == 3 and n.props[2] == b'Cluster'}
    if len(skins) != 1 or not clusters:
        raise ValueError('Exported Skin is missing or ambiguous')
    incoming = {}
    positions = []
    for position, row in enumerate(connections):
        if row.id == b'C' and row.props and row.props[0] == b'OO':
            if len(row.props) != 3 or any(type(uid) is not int for uid in row.props[1:]):
                raise ValueError('Exported object connection is invalid')
            child, parent = row.props[1:]
            incoming.setdefault(parent, []).append(child)
            if parent == skins[0]:
                if child not in clusters:
                    raise ValueError('Exported Skin has an unknown cluster link')
                positions.append(position)
    linked = incoming.get(skins[0], [])
    if set(linked) != clusters or len(linked) != len(clusters):
        raise ValueError('Exported Skin cluster links are incomplete or duplicated')
    bone_to_source = {selected[receipt]: uid for uid,receipt in mapping.items()}
    rows_by_source = {}
    for position in positions:
        row = connections[position]
        bones = incoming.get(row.props[1], [])
        if len(bones) != 1 or bones[0] not in bone_to_source:
            raise ValueError('Exported cluster Bone link is missing or ambiguous')
        source = bone_to_source[bones[0]]
        if source in rows_by_source:
            raise ValueError('Exported Skin Bone membership is duplicated')
        rows_by_source[source] = row
    if set(rows_by_source) != set(order):
        raise ValueError('Exported Skin membership differs from source')
    result = list(connections)
    for position, source in zip(positions, order):
        result[position] = rows_by_source[source]
    return result


def preserve_skin_cluster_order(output, bone_mappings, source_bone_order):
    """Rewrite only private staged Cluster-to-Skin rows; verify all other FBX data."""
    from io_scene_fbx import encode_bin, parse_fbx
    output = Path(output)
    temporary = output.with_suffix(output.suffix + '.ordered')
    if temporary.exists():
        raise ValueError('Skin order rewrite output is occupied')
    decoded, version = parse_fbx.parse(str(output), use_namedtuple=True)
    objects = [n for n in decoded.elems if n.id == b'Objects']
    connections = [n for n in decoded.elems if n.id == b'Connections']
    if len(objects) != 1 or len(connections) != 1:
        raise ValueError('Exported Skin graph is unavailable')
    connections[0].elems[:] = ordered_skin_cluster_connections(
        objects[0].elems, connections[0].elems, bone_mappings, source_bone_order)
    expected = canonical(decoded)
    try:
        encode_bin.write(str(temporary), encode_node(decoded, False), version)
        actual, actual_version = parse_fbx.parse(str(temporary), use_namedtuple=True)
        if actual_version != version or canonical(actual) != expected:
            raise ValueError('Skin order rewrite changed FBX semantics')
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()


def source_skin_shared_parent(source, model_uid, geometry_uid, *, allow_single=False):
    """Prove selected Skin roots are siblings under one actual source Null Model."""
    bones = source_skin_bone_uids(source, model_uid, geometry_uid)
    from io_scene_fbx import parse_fbx
    decoded, _ = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(n for n in decoded.elems if n.id == b'Objects')
    nodes = {str(n.props[0]): n for n in objects.elems}
    models = {uid for uid, n in nodes.items() if n.id == b'Model'}
    parents = {uid: [] for uid in bones}
    connections = next(n for n in decoded.elems if n.id == b'Connections')
    for row in connections.elems:
        if row.id == b'C' and row.props[0] == b'OO':
            child, parent = map(str, row.props[1:3])
            if child in parents and parent in models:
                parents[child].append(parent)
    if any(len(rows) > 1 for rows in parents.values()):
        raise ValueError('Source Skin parent connection is ambiguous')
    parents = {uid: rows[0] if rows else None for uid, rows in parents.items()}
    roots = [uid for uid in bones if parents[uid] not in bones]
    if allow_single and len(roots) == 1:
        # Preserve the established single-root route, including FBX world UID 0.
        return None
    if any(parent is None for parent in parents.values()):
        raise ValueError('Source Skin parent connection is missing')
    external = {parents[uid] for uid in roots}
    if len(roots) < 2 or len(external) != 1:
        raise ValueError('Source Skin does not have a unique shared nonbone parent')
    parent, = external
    if len(nodes[parent].props) < 3 or nodes[parent].props[2] != b'Null':
        raise ValueError('Source Skin shared parent is not a Null Model')
    for uid in bones:
        seen = set()
        while uid in bones:
            if uid in seen:
                raise ValueError('Source Skin bone hierarchy is cyclic')
            seen.add(uid)
            uid = parents[uid]
        if uid != parent:
            raise ValueError('Source Skin bone hierarchy is disconnected')
    return parent, parents


def encode_node(node, witness):
    from io_scene_fbx import encode_bin
    from io_scene_fbx.fbx_utils import elem_props_set
    encoded = encode_bin.FBXElem(node.id)
    for kind, value in zip(node.props_type, node.props):
        getattr(encoded, METHODS[kind])(value)
    encoded.elems.extend(encode_node(child, witness) for child in node.elems)
    if witness and node.id == b'Model':
        containers = [child for child in encoded.elems if child.id == b'Properties70']
        if len(containers) > 1:
            raise ValueError('DUPLICATE_PROPERTY_CONTAINER')
        properties = containers[0] if containers else encode_bin.FBXElem(b'Properties70')
        old = [child for child in node.elems if child.id == b'Properties70']
        if old and any(p.props and p.props[0] == PROPERTY for p in old[0].elems):
            raise ValueError('EXISTING_WITNESS_PROPERTY')
        if not containers:
            encoded.elems.append(properties)
        elem_props_set(properties, 'p_string', PROPERTY, str(node.props[0]), custom=True)
    return encoded


def canonical(node, path=()):
    path = path + ((node.id,) if node.id else ())
    # Official writer metadata only; no geometry, source UID or connection is
    # excluded. The additional witness property is checked separately below.
    if path in {(b'FileId',), (b'CreationTime',)}:
        return None
    if node.id == b'P' and node.props and node.props[0] == PROPERTY:
        return None
    properties = []
    for kind, value in zip(node.props_type, node.props):
        if isinstance(value, array.array):
            value = value.tobytes()
        elif kind == ord('F'):
            value = struct.pack('<f', value)
        elif kind == ord('D'):
            value = struct.pack('<d', value)
        properties.append((kind, value))
    children = tuple(value for child in node.elems
                     if (value := canonical(child, path)) is not None)
    if node.id == b'Properties70' and not properties and not children:
        return None
    return node.id, tuple(properties), children


def prepare_witness(source, noop, witness):
    from io_scene_fbx import encode_bin, parse_fbx
    source, noop, witness = (Path(p).resolve() for p in (source, noop, witness))
    if len({source, noop, witness}) != 3 or noop.exists() or witness.exists():
        raise ValueError('WITNESS_OUTPUT_OCCUPIED')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    decoded, version = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(child for child in decoded.elems if child.id == b'Objects')
    models = [node for node in objects.elems if node.id == b'Model']
    uids = [node.props[0] for node in models]
    if (not uids or len(set(uids)) != len(uids) or
            any(type(uid) is not int or uid == 0 or not -(2 ** 63) <= uid < 2 ** 63 for uid in uids)):
        raise ValueError('SOURCE_MODEL_UID_INVALID')
    baseline = canonical(decoded)
    for destination, add_marker in ((noop, False), (witness, True)):
        encode_bin.write(str(destination), encode_node(decoded, add_marker), version)
        after, after_version = parse_fbx.parse(str(destination), use_namedtuple=True)
        if version != after_version or baseline != canonical(after):
            raise ValueError('SOURCE_SEMANTICS_CHANGED')
        if add_marker:
            after_objects = next(child for child in after.elems if child.id == b'Objects')
            for model in (node for node in after_objects.elems if node.id == b'Model'):
                properties = next(child for child in model.elems if child.id == b'Properties70')
                markers = [p for p in properties.elems if p.props and p.props[0] == PROPERTY]
                if len(markers) != 1 or markers[0].props[-1] != str(model.props[0]).encode():
                    raise ValueError('WITNESS_MARKER_INVALID')
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise ValueError('SOURCE_CHANGED')
    return [str(uid) for uid in uids]
