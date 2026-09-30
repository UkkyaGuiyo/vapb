# SPDX-License-Identifier: GPL-3.0-or-later
"""First-party two-Bone ladder; actual FBX Cluster graph is the source oracle."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.fbx_export import export_fbx

LADDER = [0, 1e-8, 1e-6, 1e-5, 1e-4, .00025, .0005, .0009,
          .000999, .001, .001001, .0015, .005, .01]


def main():
    import bpy
    from io_scene_fbx import parse_fbx
    out = Path(sys.argv[sys.argv.index('--') + 1]); out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new('Ladder')
    # Three independent CPs per threshold; authored UV labels survive vertex splits.
    mesh.from_pydata([(i*2+x, y, 0) for i in range(len(LADDER))
                     for x,y in [(0,0),(1,0),(0,1)]], [],
                    [(3*i,3*i+1,3*i+2) for i in range(len(LADDER))])
    obj = bpy.data.objects.new('Ladder', mesh); bpy.context.collection.objects.link(obj)
    uv = mesh.uv_layers.new(name='CP')
    for loop in mesh.loops: uv.data[loop.index].uv = (loop.vertex_index+1, .375)
    rig = bpy.data.objects.new('Rig', bpy.data.armatures.new('Rig'))
    bpy.context.collection.objects.link(rig); rig.select_set(True)
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
    for i in range(2):
        bone = rig.data.edit_bones.new('Bone'+str(i)); bone.head=(i,0,0); bone.tail=(i,0,1)
    bpy.ops.object.mode_set(mode='OBJECT')
    for i,bone in enumerate(rig.pose.bones): bone['_vapb_weight_bone_id']='WEIGHT-BONE-'+str(i)
    obj['_vapb_weight_mesh_id']='WEIGHT-MESH-0'
    groups=[obj.vertex_groups.new(name=bone.name) for bone in rig.data.bones]
    for i,w in enumerate(LADDER):
        for cp in range(i*3,i*3+3):
            if w: groups[0].add([cp],w,'REPLACE')
            groups[1].add([cp],1-w,'REPLACE')
    obj.modifiers.new('Skin','ARMATURE').object=rig; obj.parent=rig
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    export_fbx(out/'Ladder.fbx')
    root,_=parse_fbx.parse(str(out/'Ladder.fbx'),use_namedtuple=True)
    nodes={n.props[0]:n for n in next(n for n in root.elems if n.id==b'Objects').elems}
    edges={}
    for c in next(n for n in root.elems if n.id==b'Connections').elems:
        if c.props[0]==b'OO': edges.setdefault(c.props[2],[]).append(c.props[1])
    geometry,=[n for n in nodes.values() if n.id==b'Geometry' and n.props[2]==b'Mesh']
    skin,=[nodes[u] for u in edges[geometry.props[0]] if nodes[u].id==b'Deformer' and nodes[u].props[2]==b'Skin']
    clusters=[]
    for uid in edges[skin.props[0]]:
        n=nodes[uid]
        if n.id!=b'Deformer' or n.props[2]!=b'Cluster': continue
        model,=[nodes[u] for u in edges[uid] if nodes[u].id==b'Model']
        props=next(p for p in model.elems if p.id==b'Properties70')
        label,=[p.props[-1].decode() for p in props.elems if p.props[0]==b'_vapb_weight_bone_id']
        indices=next(p.props[0] for p in n.elems if p.id==b'Indexes')
        weights=next(p.props[0] for p in n.elems if p.id==b'Weights')
        clusters.append(dict(cluster_uid=str(uid),bone_uid=str(model.props[0]),bone_label=label,
                             weights=[dict(cp=int(cp),weight=float(w)) for cp,w in zip(indices,weights)]))
    assert len(clusters)==2
    raw={(row['cp'],c['bone_label']):row['weight'] for c in clusters for row in c['weights']}
    for cp in range(len(mesh.vertices)):
        actual={rig.pose.bones[g.group]['_vapb_weight_bone_id']:g.weight for g in mesh.vertices[cp].groups}
        for label in ('WEIGHT-BONE-0','WEIGHT-BONE-1'):
            assert raw.get((cp,label),0)==actual.get(label,0), 'BLENDER_TO_FBX_WEIGHT_LOSS'
    report=dict(schema='vapb-small-weight-source-1',fbx_sha256=hashlib.sha256((out/'Ladder.fbx').read_bytes()).hexdigest(),
                geometry_uid=str(geometry.props[0]),skin_uid=str(skin.props[0]),mesh_label='WEIGHT-MESH-0',
                cp_count=len(mesh.vertices),ladder=LADDER,clusters=clusters)
    (out/'Source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Source.blend'))
    print('SMALL_WEIGHT_RAW_FBX_VERIFIED',len(mesh.vertices))


if __name__=='__main__': main()
