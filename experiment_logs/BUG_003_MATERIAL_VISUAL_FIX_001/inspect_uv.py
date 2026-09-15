import bpy
from pathlib import Path
import json

rows=[]
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not obj.data or not any(m and m.name == 'SyntheticMaterial' for m in obj.data.materials):
        continue
    layers=obj.data.uv_layers
    values=[]
    if layers:
        values=[(round(loop.uv.x,4),round(loop.uv.y,4)) for loop in layers.active.data[:min(20,len(layers.active.data))]]
    rows.append({'object':obj.name,'uv_layers':[layer.name for layer in layers],'uv_count':len(layers.active.data) if layers else 0,'sample':values})
out=Path(__file__).with_name('sample_garment_uv_summary.json'); out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8'); print('UV',json.dumps(rows[:5],ensure_ascii=False),flush=True); bpy.ops.wm.quit_blender()
