# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture authored/staged/raw weights and real evaluated Armature deformation."""
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.fbx_export import export_fbx


def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]
def neighbor(value,step):return struct.unpack('<f',struct.pack('<I',bits(value)+step))[0]


def main():
    import bpy
    from io_scene_fbx import parse_fbx
    out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=False)
    controls=[('half',[.5,.5]),('quarter',[.25,.75]),('awkward3',[.1,.2,.7]),
        ('awkward4',[.1,.2,.3,.4]),('under',[.2,.3]),('over',[.7,.6]),
        ('near_below',[.5,neighbor(.5,-1)]),('near_exact',[.5,.5]),
        ('near_above',[.5,neighbor(.5,1)]),('tiny4',[.0005,.1995,.3,.5]),
        ('order_a',[.1,.2,.3,.4]),('order_b',[.4,.3,.2,.1]),
        ('order_c',[.2,.4,.1,.3]),('awkward3_reverse',[.7,.2,.1]),
        # First-party seed-930 values distinguish accumulation order and division.
        ('sensitive_a',[.2149483859539032,.6295662522315979,.7433511018753052,.282781720161438]),
        ('sensitive_b',[.282781720161438,.7433511018753052,.6295662522315979,.2149483859539032]),
        ('sensitive_c',[.7433511018753052,.2149483859539032,.282781720161438,.6295662522315979]),
        # Seed-9302/9303 analogues distinguish one from two normalization passes.
        ('two_pass2',[.08581870049238205,.0663706362247467]),
        ('two_pass3',[.535895586013794,.3291786015033722,.13492579758167267]),
        ('two_pass4',[.3887108564376831,.21534879505634308,.06777431815862656,.32816603779792786])]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh=bpy.data.meshes.new('NumericControl')
    mesh.from_pydata([(i*.03+x,y,0) for i in range(len(controls)) for x,y in [(0,0),(.01,0),(0,.01)]],[],
        [(3*i,3*i+1,3*i+2) for i in range(len(controls))])
    obj=bpy.data.objects.new('NumericControl',mesh);bpy.context.collection.objects.link(obj)
    layer=mesh.uv_layers.new(name='CP')
    for loop in mesh.loops:layer.data[loop.index].uv=(loop.vertex_index+1,.375)
    obj['_vapb_weight_mesh_id']='WEIGHT-MESH-0'
    rig=bpy.data.objects.new('Rig',bpy.data.armatures.new('Rig'));bpy.context.collection.objects.link(rig)
    rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for i in range(4):
        bone=rig.data.edit_bones.new('Bone'+str(i));bone.head=(i*.01,0,0);bone.tail=(i*.01,0,.1)
    bpy.ops.object.mode_set(mode='OBJECT')
    groups=[obj.vertex_groups.new(name=bone.name) for bone in rig.data.bones]
    for i,bone in enumerate(rig.pose.bones):bone['_vapb_weight_bone_id']='WEIGHT-BONE-'+str(i)
    for index,(_,weights) in enumerate(controls):
        for cp in range(index*3,index*3+3):
            for bone,w in enumerate(weights):groups[bone].add([cp],w,'REPLACE')
    obj.parent=rig;modifier=obj.modifiers.new('Skin','ARMATURE');modifier.object=rig
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    def observe(target):
        rows=[]
        for vertex in target.data.vertices:
            weights=[dict(bone='WEIGHT-BONE-'+str(g.group),value=g.weight,bits=bits(g.weight)) for g in vertex.groups]
            total=0.
            for w in weights:total=f32(total+w['value'])
            rows.append(dict(cp=vertex.index,weights=weights,sum64=sum(w['value'] for w in weights),sum32=total,
                             exact_sum_hex=sum(w['value'] for w in weights).hex()))
        return rows
    before=observe(obj);staged=[]
    def writer(**options):
        copy,=[o for o in bpy.context.selected_objects if o.type=='MESH']
        assert copy is not obj and copy.data is not obj.data
        staged.extend(observe(copy))
        return bpy.ops.export_scene.fbx(**options)
    proxy=SimpleNamespace(context=bpy.context,data=bpy.data,types=bpy.types,ops=SimpleNamespace(export_scene=SimpleNamespace(fbx=writer)))
    export_fbx(out/'Ladder.fbx',bpy_module=proxy)
    assert before==staged==observe(obj),'B0_B1_SOURCE_CHANGED'
    root,_=parse_fbx.parse(str(out/'Ladder.fbx'),use_namedtuple=True)
    nodes={n.props[0]:n for n in next(n for n in root.elems if n.id==b'Objects').elems};edges={}
    for c in next(n for n in root.elems if n.id==b'Connections').elems:
        if c.props[0]==b'OO':edges.setdefault(c.props[2],[]).append(c.props[1])
    geom,=[n for n in nodes.values() if n.id==b'Geometry' and n.props[2]==b'Mesh']
    skin,=[nodes[u] for u in edges[geom.props[0]] if nodes[u].id==b'Deformer' and nodes[u].props[2]==b'Skin']
    clusters=[]
    for uid in edges[skin.props[0]]:
        node=nodes[uid]
        if node.props[2]!=b'Cluster':continue
        model,=[nodes[u] for u in edges[uid] if nodes[u].id==b'Model']
        label,=[p.props[-1].decode() for group in model.elems if group.id==b'Properties70'
                for p in group.elems if p.props[0]==b'_vapb_weight_bone_id']
        indices=next(p.props[0] for p in node.elems if p.id==b'Indexes');weights=next(p.props[0] for p in node.elems if p.id==b'Weights')
        clusters.append(dict(cluster_uid=str(uid),bone_uid=str(model.props[0]),bone_label=label,
            weights=[dict(cp=int(cp),weight=float(w),double_hex=float(w).hex(),double_bits=struct.pack('<d',w).hex()) for cp,w in zip(indices,weights)]))
    # Actual pose deformation, then restore the editing state.
    bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get()
    def evaluated():
        depsgraph.update(); evaluated=obj.evaluated_get(depsgraph); data=evaluated.to_mesh()
        try:return [tuple(obj.matrix_world@v.co) for v in data.vertices]
        finally:evaluated.to_mesh_clear()
    rest=evaluated()
    moves=[]
    for i,bone in enumerate(rig.pose.bones):
        matrix=bone.matrix.copy();matrix.translation.x+=(i+1)*.125;bone.matrix=matrix
        moves.append(dict(bone='WEIGHT-BONE-'+str(i),world_dx=(i+1)*.125))
    bpy.context.view_layer.update();posed=evaluated()
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update();assert before==observe(obj)
    report=dict(schema='vapb-weight-numeric-source-1',fbx_sha256=hashlib.sha256((out/'Ladder.fbx').read_bytes()).hexdigest(),
        geometry_uid=str(geom.props[0]),skin_uid=str(skin.props[0]),mesh_label='WEIGHT-MESH-0',cp_count=len(mesh.vertices),
        controls=[dict(label=label,first_cp=i*3) for i,(label,_) in enumerate(controls)],B0=before,B1=staged,clusters=clusters,
        moves=moves,blender_rest=rest,blender_posed=posed)
    (out/'Source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Source.blend'))
    print('NUMERIC_B0_B1_RAW_CAPTURED controls=%d cp=%d'%(len(controls),len(mesh.vertices)))


if __name__=='__main__':main()
