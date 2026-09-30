# SPDX-License-Identifier: GPL-3.0-or-later
"""Create three first-party public controls with exact raw-CP diagnostic labels.

Blender CLI: NEW_EXTERNAL_FOLDER. Source bytes and stamped bytes are separate.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_witness import canonical, encode_node
from unitypackage_blender_importer.export.fbx_export import FBX_EXPORT_PRESET


def main():
    import bpy
    from io_scene_fbx import parse_fbx, encode_bin
    args=sys.argv[sys.argv.index('--')+1:]
    folder=Path(args[0]); assert not folder.exists()
    fixtures={
        'planar': ([(0,0,0),(2,0,0),(2.4,1,0),(1,2,0),(0,1,0)],[(0,1,2,3,4)]),
        'concave': ([(0,0,0),(2,0,0),(2,2,0),(1,.6,0),(0,2,0)],[(0,1,2,3,4)]),
        'triangles': ([(0,0,0),(2,0,0),(2,2,.3),(0,2,0)],[(0,1,2),(0,2,3)]),
        'material_partitions': ([(0,0,0),(1,0,0),(0,1,0),(2,0,0),(3,0,0),(2,1,0),(4,0,0),(5,0,0),(4,1,0)],[(0,1,2),(3,4,5),(6,7,8)]),
        'small_weights': ([(0,0,0),(1,0,0),(0,1,0)],[(0,1,2)])}
    if len(args)>1:
        fixtures={label:fixtures[label] for label in args[1:]}
    else:
        fixtures={label:value for label,value in fixtures.items() if label not in {'small_weights','material_partitions'}}
    for label,(vertices,faces) in fixtures.items():
        out=folder/label;out.mkdir(parents=True)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        data=bpy.data.meshes.new('AuthoredControl'); data.from_pydata(vertices,[],faces)
        obj=bpy.data.objects.new('AuthoredControl',data);bpy.context.scene.collection.objects.link(obj)
        if label=='small_weights':
            rig=bpy.data.objects.new('AuthoredRig',bpy.data.armatures.new('AuthoredBones'))
            bpy.context.scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            a=rig.data.edit_bones.new('AuthoredBoneA');a.head=(0,0,0);a.tail=(0,0,1)
            b=rig.data.edit_bones.new('AuthoredBoneB');b.head=(0,0,1);b.tail=(0,0,2);b.parent=a
            bpy.ops.object.mode_set(mode='OBJECT')
            ga=obj.vertex_groups.new(name='AuthoredBoneA');gb=obj.vertex_groups.new(name='AuthoredBoneB')
            for index,weight in enumerate((.0005,.0015,.25)):
                ga.add([index],1-weight,'REPLACE');gb.add([index],weight,'REPLACE')
            obj.parent=rig;obj.modifiers.new('AuthoredSkin','ARMATURE').object=rig
        if label=='material_partitions':
            for n in range(3):data.materials.append(bpy.data.materials.new('AuthoredMaterial%d'%n))
            for polygon,slot in zip(data.polygons,(0,2,1)):polygon.material_index=slot
        uv=data.uv_layers.new(name='AuthoredUV')
        for loop in data.loops:uv.data[loop.index].uv=data.vertices[loop.vertex_index].co.xy
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        assert bpy.ops.export_scene.fbx(**dict(FBX_EXPORT_PRESET,filepath=str(out/'Source.fbx'))) == {'FINISHED'}
        guid=hashlib.sha256(('vapb-public-abcd-'+label).encode()).hexdigest()[:32]
        (out/'Source.fbx.meta').write_text('fileFormatVersion: 2\nguid: '+guid+'\nModelImporter:\n  serializedVersion: 22200\n  meshes:\n    globalScale: 1\n    useFileUnits: 1\n    meshCompression: 0\n    importBlendShapes: 1\n    keepQuads: 0\n    weldVertices: 1\n    indexFormat: 0\n  tangentSpace:\n    normalSmoothAngle: 60\n    normalImportMode: 0\n    tangentImportMode: 3\n  animationType: 0\n')
        if label=='small_weights':
            meta=out/'Source.fbx.meta'
            meta.write_text(meta.read_text().replace('animationType: 0','animationType: 2'))
        root,version=parse_fbx.parse(str(out/'Source.fbx'),use_namedtuple=True)
        objects=next(n for n in root.elems if n.id==b'Objects')
        geometry,=[n for n in objects.elems if n.id==b'Geometry' and n.props[2]==b'Mesh']
        index=objects.elems.index(geometry)
        channel=len([n for n in geometry.elems if n.id==b'LayerElementUV'])
        cp_count=len(next(n.props[0] for n in geometry.elems if n.id==b'Vertices'))//3
        encoded=encode_node(root,False)
        target=next(n for n in encoded.elems if n.id==b'Objects').elems[index]
        def add(parent,name,method=None,value=None):
            node=encode_bin.FBXElem(name);parent.elems.append(node)
            if method:getattr(node,method)(value)
            return node
        layer=add(target,b'LayerElementUV','add_int32',channel)
        add(layer,b'Version','add_int32',101);add(layer,b'Name','add_string',b'VAPB_CP_DIAGNOSTIC')
        add(layer,b'MappingInformationType','add_string',b'ByVertice')
        add(layer,b'ReferenceInformationType','add_string',b'Direct')
        add(layer,b'UV','add_float64_array',[v for i in range(cp_count) for v in (i+1.,.375)])
        ref=add(target,b'Layer','add_int32',channel);add(ref,b'Version','add_int32',100)
        entry=add(ref,b'LayerElement');add(entry,b'Type','add_string',b'LayerElementUV');add(entry,b'TypedIndex','add_int32',channel)
        encode_bin.write(str(out/'Stamped.fbx'),encoded,version)
        decoded,_=parse_fbx.parse(str(out/'Stamped.fbx'),use_namedtuple=True)
        d=next(n for n in decoded.elems if n.id==b'Objects').elems[index]
        d.elems[:]=[n for n in d.elems if not(n.id in (b'Layer',b'LayerElementUV') and n.props[0]==channel)]
        assert canonical(decoded)==canonical(root),'NON_MARKER_SOURCE_CHANGED'
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        manifest=dict(source_fbx_sha256=digest(out/'Source.fbx'),source_meta_sha256=digest(out/'Source.fbx.meta'),
                      stamped_fbx_sha256=digest(out/'Stamped.fbx'),meshes=[dict(geometry_uid=str(geometry.props[0]),
                      control_point_count=cp_count,uv_channel=channel)])
        (out/'ControlPointManifest.json').write_text(json.dumps(manifest,indent=2))
    print('PUBLIC_ABCD_INPUTS_CREATED count=%d' % len(fixtures))


if __name__=='__main__':main()
