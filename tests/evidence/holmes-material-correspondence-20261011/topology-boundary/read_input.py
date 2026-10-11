"""Read existing parsed FBX nodes; independent of the fixture generator."""
import importlib.util
from pathlib import Path
import sys
sys.dont_write_bytecode = True


def child(node, name):
    values = [n for n in node.elems if n.id == name]
    if len(values) != 1:
        raise ValueError('missing/ambiguous node: ' + name.decode())
    return values[0]


def value(node, name):
    return child(node, name).props[0]


def validate_layer_binding(g, uv, material):
    layer = child(g, b'Layer')
    if layer.props != [0]:
        raise ValueError('only sole active Layer0 supported')
    bindings = [n for n in layer.elems if n.id == b'LayerElement']
    for selected in (uv, material):
        matching = [n for n in bindings if value(n, b'Type') == selected.id]
        if len(matching) != 1 or value(matching[0], b'TypedIndex') != selected.props[0]:
            raise ValueError('missing/ambiguous/wrong active layer binding')


def decode(root):
    objects = child(root, b'Objects').elems
    nodes = {n.props[0]: n for n in objects}
    if len(nodes) != len(objects):
        raise ValueError('duplicate object UID')
    geometries = [n for n in objects if n.id == b'Geometry' and n.props[2] == b'Mesh']
    if len(geometries) != 1 or any(n.id in (b'Deformer', b'AnimationStack') for n in objects):
        raise ValueError('outside single static Mesh scope')
    g = geometries[0]
    links = child(root, b'Connections').elems
    owners = [n.props[2] for n in links if n.props[:2] == [b'OO', g.props[0]]]
    if len(owners) != 1 or owners[0] not in nodes or nodes[owners[0]].id != b'Model':
        raise ValueError('unique Geometry/Model connection required')
    model = owners[0]
    slots = [n.props[1] for n in links if n.props[0] == b'OO' and n.props[2] == model
             and n.props[1] in nodes and nodes[n.props[1]].id == b'Material']
    if not slots or len(slots) != len(set(slots)):
        raise ValueError('missing/duplicate Material connections')
    layer = child(g, b'LayerElementMaterial')
    if value(layer, b'MappingInformationType') != b'ByPolygon' or value(layer, b'ReferenceInformationType') != b'IndexToDirect':
        raise ValueError('unsupported Material layer')
    uv_layer = child(g, b'LayerElementUV')
    validate_layer_binding(g, uv_layer, layer)
    if value(uv_layer, b'MappingInformationType') != b'ByPolygonVertex' or value(uv_layer, b'ReferenceInformationType') != b'IndexToDirect':
        raise ValueError('unsupported UV layer')
    raw = list(value(g, b'PolygonVertexIndex'))
    vertices, uvs = list(value(g, b'Vertices')), list(value(uv_layer, b'UV'))
    ui, materials = list(value(uv_layer, b'UVIndex')), list(value(layer, b'Materials'))
    if len(vertices) % 3 or len(uvs) % 2 or len(ui) != len(raw):
        raise ValueError('invalid stream dimensions')
    polygons, current = [], []
    for i, index in enumerate(raw):
        cp = -index - 1 if index < 0 else index
        if not 0 <= cp < len(vertices) // 3 or not 0 <= ui[i] < len(uvs) // 2:
            raise ValueError('corner reference out of range')
        current.append((cp, tuple(vertices[cp*3:cp*3+3]), tuple(uvs[ui[i]*2:ui[i]*2+2])))
        if index < 0:
            p = len(polygons)
            if p >= len(materials) or not 0 <= materials[p] < len(slots):
                raise ValueError('Material reference out of range')
            polygons.append(dict(polygon=p, uid=slots[materials[p]], raw_slot=materials[p],
                                 cp=[c[0] for c in current], positions=[c[1] for c in current],
                                 uv=[c[2] for c in current]))
            current = []
    if current or not polygons or len(materials) != len(polygons):
        raise ValueError('unterminated polygon or Material stream mismatch')
    return dict(model_uid=model, geometry_uid=g.props[0], material_connections=slots, polygons=polygons)


def parse(path, repo, addon):
    # Reuse the established installed official parser loader, not a new parser.
    helper_path = Path(repo) / 'tests/evidence/inbound-material-face-membership-20261007/verify_inbound_frame.py'
    spec = importlib.util.spec_from_file_location('existing_fbx_parser_loader', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    parser = helper.load_parser(Path(addon))
    root, version = parser.parse(str(path), use_namedtuple=True)
    return root, version
