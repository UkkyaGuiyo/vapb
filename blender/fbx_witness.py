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
