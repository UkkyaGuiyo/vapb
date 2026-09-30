"""Source-cache geometry diagnostic; no Prefab pose/morph equivalence claim.
Blender CLI: BLEND SOURCE_OBSERVATION CONTROL_REPORT OUTPUT (outside repository).
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
def main():
 import bpy
 from mathutils import Vector,kdtree
 from mathutils.bvhtree import BVHTree
 from unitypackage_blender_importer.tests.hierarchy_comparator import point_multiset_equal
 args=sys.argv[sys.argv.index('--')+1:]
 blend,source_path,controls_path,output=args[:4]
 assert len(args)>=4 and len(args)%2==0, 'INVALID_DIAGNOSTIC_ARGUMENTS'
 options=dict(zip(args[4::2],args[5::2]))
 assert set(options)<={'--triangulate-mode','--ngon-mode'}, 'INVALID_DIAGNOSTIC_OPTION'
 mode=options.get('--triangulate-mode'); ngon=options.get('--ngon-mode','BEAUTY')
 assert mode is None or mode in ('FIXED','FIXED_ALTERNATE','SHORTEST_DIAGONAL','LONGEST_DIAGONAL','BEAUTY'), 'INVALID_TRIANGULATE_MODE'
 assert ngon in ('BEAUTY','CLIP'), 'INVALID_NGON_MODE'
 source=json.loads(Path(source_path).read_text(encoding='utf-8-sig')); controls=json.loads(Path(controls_path).read_text(encoding='utf-8-sig'))
 assert controls['pass'] and controls['sourceRawRestored'] and controls['sourceMetaRestored'], 'SOURCE_CONTROLS_INVALID'
 bpy.ops.wm.open_mainfile(filepath=blend); objects=list(bpy.context.scene.objects); dg=bpy.context.evaluated_depsgraph_get()
 rows=[]
 def point_distances(a,b):
  tree=kdtree.KDTree(len(b))
  for i,p in enumerate(b): tree.insert(Vector(p),i)
  tree.balance(); return [tree.find(Vector(p))[2] for p in a]
 def coverage(a,b):
  return max(point_distances(a,b))
 def surface(corners):
  triangles=[]; zero_area=0
  for i in range(0,len(corners),3):
   a,b,c=(Vector(p) for p in corners[i:i+3])
   if (b-a).cross(c-a).length*0.5 <= 1e-12:
    zero_area+=1
   else: triangles.append((a,b,c))
  assert triangles, 'NONZERO_TRIANGLE_SURFACE_UNAVAILABLE'
  points=[p for triangle in triangles for p in triangle]
  tree=BVHTree.FromPolygons(points,[(i,i+1,i+2) for i in range(0,len(points),3)],all_triangles=True)
  return triangles,tree,zero_area
 def sample_distances(triangles,tree):
  maximum=0.0; above=0; count=0
  for a,b,c in triangles:
   for point in (a,b,c,(a+b)*0.5,(b+c)*0.5,(c+a)*0.5,(a+b+c)/3.0):
    nearest=tree.find_nearest(point)
    assert nearest[0] is not None, 'SURFACE_NEAREST_UNAVAILABLE'
    distance=nearest[3]; maximum=max(maximum,distance); above+=distance>3e-5; count+=1
  return dict(sample_count=count,maximum_distance=maximum,count_above_3e_5=above)
 for observed in source['skinned_renderers']:
  members=[o for o in objects if o.type=='MESH' and o.get('_vapb_root_context_id') and str(o.get('_vapb_fbx_model_uid'))==str(observed['renderer_model_uid']) and o.get('_vapb_fbx_source_asset_guid')==source['model_guid'] and o.get('_vapb_fbx_source_asset_sha256')==source['source_fbx_sha256']]
  source_ids={o.get('_vapb_fbx_source_realization_id') for o in members}
  assert len(source_ids)==1 and None not in source_ids, 'SOURCE_REALIZATION_BRIDGE_UNAVAILABLE'
  cache,=[o for o in objects if o.type=='MESH' and not o.get('_vapb_root_context_id') and o.get('_vapb_fbx_realization_id') in source_ids]
  assert cache.get('_vapb_fbx_model_uid')==members[0].get('_vapb_fbx_model_uid') and cache.get('_vapb_fbx_mesh_receipt_id')==members[0].get('_vapb_fbx_mesh_receipt_id') and cache.get('_vapb_fbx_source_asset_sha256')==source['source_fbx_sha256'], 'SOURCE_RECEIPT_BRIDGE_MISMATCH'
  polygons=list(cache.data.polygons)
  quad_count=sum(len(p.vertices)==4 for p in polygons)
  ngon_count=sum(len(p.vertices)>4 for p in polygons)
  cache.data.calc_loop_triangles()
  raw_zero=sum((cache.matrix_world@cache.data.vertices[t.vertices[1]].co-cache.matrix_world@cache.data.vertices[t.vertices[0]].co).cross(cache.matrix_world@cache.data.vertices[t.vertices[2]].co-cache.matrix_world@cache.data.vertices[t.vertices[0]].co).length*0.5<=1e-12 for t in cache.data.loop_triangles)
  original_modifiers=tuple(cache.modifiers)
  temporary=None
  if mode:
   temporary=cache.modifiers.new('Temporary source triangulation diagnostic','TRIANGULATE')
   temporary.quad_method=mode; temporary.ngon_method=ngon
   cache.modifiers.move(len(cache.modifiers)-1,0)
   bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
  evaluated=cache.evaluated_get(dg); mesh=evaluated.to_mesh()
  try:
   mesh.calc_loop_triangles(); vertices=[list(evaluated.matrix_world@v.co) for v in mesh.vertices]; corners=[vertices[i] for t in mesh.loop_triangles for i in t.vertices]
  finally:
   evaluated.to_mesh_clear()
   if temporary:
    cache.modifiers.remove(temporary); bpy.context.view_layer.update()
   assert tuple(cache.modifiers)==original_modifiers, 'TEMPORARY_MODIFIER_NOT_RESTORED'
  unity_vertices=[[-p['x'],-p['z'],p['y']] for p in observed['baked_world_vertices']]; unity_corners=[[-p['x'],-p['z'],p['y']] for p in observed['baked_world_triangle_corners']]
  forward=coverage(vertices,unity_vertices); backward=coverage(unity_vertices,vertices)
  native_triangles,native_tree,native_zero=surface(corners)
  unity_triangles,unity_tree,unity_zero=surface(unity_corners)
  rows.append(dict(renderer_model_uid=str(observed['renderer_model_uid']),mesh_local_id=observed['mesh_local_id'],source_realization_id=next(iter(source_ids)),source_receipt_valid=True,triangulate_quad_method=mode,triangulate_ngon_method=ngon if mode else None,temporary_modifier_restored=True,source_quad_polygon_count=quad_count,source_ngon_polygon_count=ngon_count,raw_base_zero_area_triangle_count=raw_zero,native_vertex_count=len(vertices),unity_vertex_count=len(unity_vertices),native_corner_count=len(corners),unity_corner_count=len(unity_corners),vertex_coverage_max_distance=max(forward,backward),vertex_coverage_equal=max(forward,backward)<=3e-5,triangle_corners_equal=point_multiset_equal(corners,observed['baked_world_triangle_corners']),referenced_corner_coverage_max_distance=max(coverage(corners,unity_corners),coverage(unity_corners,corners)),native_vertices_not_on_referenced_corner_count=sum(d>3e-5 for d in point_distances(vertices,corners)),unity_vertices_not_on_referenced_corner_count=sum(d>3e-5 for d in point_distances(unity_vertices,unity_corners)),native_zero_area_triangle_count=native_zero,unity_zero_area_triangle_count=unity_zero,native_to_unity_surface_samples=sample_distances(native_triangles,unity_tree),unity_to_native_surface_samples=sample_distances(unity_triangles,native_tree)))
 report=dict(status='OBSERVED_SOURCE_GEOMETRY_NOT_PREFAB_PARITY',rows=rows,mesh_count=len(rows),vertex_coverage_equal_count=sum(r['vertex_coverage_equal'] for r in rows),triangle_corners_equal_count=sum(r['triangle_corners_equal'] for r in rows),corner_count_difference_count=sum(r['native_corner_count']!=r['unity_corner_count'] for r in rows))
 Path(output).write_text(json.dumps(report,indent=2)); print('SOURCE_GEOMETRY_BOUNDARY meshes='+str(len(rows))+' vertex_coverage_equal='+str(report['vertex_coverage_equal_count'])+' triangle_corners_equal='+str(report['triangle_corners_equal_count'])+' corner_count_difference='+str(report['corner_count_difference_count']))
if __name__=='__main__': main()
