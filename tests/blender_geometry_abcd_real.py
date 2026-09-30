# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded real D spot check. All artifacts stay in an external private folder.

Blender CLI: PRIVATE_BASELINE_FOLDER PRIVATE_CP_REPORT NEW_EXTERNAL_OUTPUT.
Selection uses proven occurrence identity, not names or scene ordering.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_geometry_abcd import observe, explicit_copy, label_materials
from unitypackage_blender_importer.export.fbx_export import export_fbx, FBX_EXPORT_PRESET


def main():
    import bpy
    baseline, cp_report, output=map(Path,sys.argv[sys.argv.index('--')+1:][:3])
    assert not output.exists()
    blend=baseline/'baseline.blend'
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    revision=digest(blend)
    snapshot=json.loads((baseline/'blender_snapshot.json').read_text())
    topology=json.loads(cp_report.read_text())
    categories={(r['mesh_guid'],r['mesh_local_id']):r['category'] for r in topology['meshes']}
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    candidates=[]
    for skin in snapshot['native_skin']['skins']:
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and
                 o.get('_vapb_renderer_occurrence_id')==skin['occurrence_id']]
        assert len(objects)==1,'OCCURRENCE_IDENTITY_UNPROVEN'
        obj,=objects
        if len(obj.data.uv_layers)>=8 or any(len(p.vertices)<3 for p in obj.data.polygons):continue
        referenced={l.vertex_index for l in obj.data.loops}
        if len(referenced)!=len(obj.data.vertices):continue
        key=(skin['mesh_guid'],str(skin['mesh_local_id']))
        assert key in categories
        candidates.append((skin,obj,categories[key],sum(len(p.vertices)>4 for p in obj.data.polygons)))
    exact=[r for r in candidates if r[2]=='EXACT']
    red=[r for r in candidates if r[2]=='TOPOLOGY_MISMATCH']
    assert exact and len(red)>=3,'BOUNDED_SAMPLE_UNAVAILABLE'
    # Complexity only chooses a sample; actual correspondence is occurrence evidence.
    exact.sort(key=lambda r:(not bool(r[1].data.shape_keys),len(r[1].data.vertices)))
    red.sort(key=lambda r:(-r[3],len(r[1].data.vertices)))
    selected=[exact[0],*red[:3]]
    output.mkdir(parents=True)
    selection=[]
    for index,(skin,obj,category,ngons) in enumerate(selected):
        case=output/('sample_%02d'%index);case.mkdir()
        source_before=observe(obj,index)
        materials_before=tuple(slot.material.as_pointer() if slot.material else None for slot in obj.material_slots)
        original_data=obj.data.copy()
        original_keys=[k.value for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else []
        copies=[]
        for mode in ('D0','D1'):
            copied=obj.copy();copied.data=original_data.copy()
            bpy.context.scene.collection.objects.link(copied)
            copied.parent=None;copied.matrix_world=obj.matrix_world.copy()
            copied.name='VAPB-EXP-MESH-'+str(index)
            if '--material-labels' in sys.argv:label_materials(copied)
            if copied.data.shape_keys:
                for key in copied.data.shape_keys.key_blocks:key.value=0
            marker=len(copied.data.uv_layers)
            layer=copied.data.uv_layers.new(name='VAPB_FINAL_VERTEX_DIAGNOSTIC')
            for loop in copied.data.loops:layer.data[loop.index].uv=(loop.vertex_index+1,.375)
            if mode=='D1' and '--production-triangles' not in sys.argv:
                old=copied;copied=explicit_copy(copied)
                bpy.data.objects.remove(old,do_unlink=True)
            armatures=[]
            bone_labels={}
            for modifier in copied.modifiers:
                if modifier.type!='ARMATURE':raise ValueError('NON_ARMATURE_MODIFIER_UNSUPPORTED')
                rig=modifier.object;assert rig is not None
                newrig=rig.copy();newrig.data=rig.data.copy()
                bpy.context.scene.collection.objects.link(newrig)
                newrig.parent=None;newrig.matrix_world=rig.matrix_world.copy()
                # Native group->Bone binding is Blender's actual Armature relation.
                # Fresh labels are assigned to these actual handles, not guessed.
                for bone_index,bone in enumerate(newrig.data.bones):
                    oldname=bone.name;label='VAPB-EXP-BONE-%04d'%bone_index
                    group=copied.vertex_groups.get(oldname)
                    if group is not None:group.name=label
                    bone.name=label;bone_labels[label]=str(bone.get('_vapb_fbx_model_uid','UNPROVEN'))
                modifier.object=newrig;armatures.append(newrig)
            shape_ids={}
            if copied.data.shape_keys:
                for n,key in enumerate(copied.data.shape_keys.key_blocks):
                    if n:
                        key.name='VAPB-EXP-SHAPE-%04d'%n;shape_ids[key.as_pointer()]=n
            bpy.context.view_layer.update()
            row=observe(copied,index,marker,len(copied.data.vertices),shape_ids)
            for scene_obj in bpy.context.scene.objects:scene_obj.select_set(False)
            copied.select_set(True)
            for rig in armatures:rig.select_set(True)
            if mode=='D0':
                options=dict(FBX_EXPORT_PRESET,filepath=str(case/(mode+'.fbx')))
                assert bpy.ops.export_scene.fbx(**options)=={'FINISHED'}
            else:
                export_fbx(case/(mode+'.fbx'))
            copies.append(dict(mode=mode,fbx_sha256=digest(case/(mode+'.fbx')),pre_export=[row],
                               source_objects_unchanged=True,bone_export_labels=bone_labels))
            for rig in armatures:bpy.data.objects.remove(rig,do_unlink=True)
            bpy.data.objects.remove(copied,do_unlink=True)
        assert observe(obj,index)==source_before,'SOURCE_SEMANTIC_STATE_CHANGED'
        assert tuple(slot.material.as_pointer() if slot.material else None for slot in obj.material_slots)==materials_before,'SOURCE_MATERIAL_HANDLES_CHANGED'
        assert obj.data is not original_data
        assert ([k.value for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else []) == original_keys
        manifest=dict(meshes=[dict(uv_channel=marker,control_point_count=len(obj.data.vertices))])
        (case/'ControlPointManifest.json').write_text(json.dumps(manifest,indent=2))
        (case/'BlenderD.json').write_text(json.dumps(dict(baseline_blend_sha256=revision,
             source_package_sha256=snapshot['package_sha256'],shape_weights_fixed_to_zero=True,exports=copies),indent=2))
        selection.append(dict(sample=index,source_category=category,source_ngon_count=ngons,
             source_occurrence=skin['occurrence_id'],mesh_guid=skin['mesh_guid'],mesh_local_id=skin['mesh_local_id']))
    assert digest(blend)==revision,'SOURCE_BLEND_CHANGED'
    (output/'PrivateSelection.json').write_text(json.dumps(selection,indent=2))
    print('BOUNDED_REAL_D_EXPORTED exact=1 mismatch=3 source_blend_unchanged=1')


if __name__=='__main__':main()
