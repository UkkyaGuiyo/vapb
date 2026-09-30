# SPDX-License-Identifier: GPL-3.0-or-later
"""Classify two existing exact-revision artifacts; private tables stay external."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_small_weight_real_check import raw_skin_weights
from unitypackage_blender_importer.tests.weight_numeric_models import models,bits,ulp


def main():
    folder,blender_report,output=map(Path,sys.argv[sys.argv.index('--')+1:])
    raw=raw_skin_weights(folder)
    report=json.loads(blender_report.read_text());before,=next(e for e in report['exports'] if e['mode']=='D1')['pre_export']
    b0={}
    for cp,weights in zip(before['vertex_control_point_indices'],before['skin_weights']):
        values={w['group']:w['weight'] for w in weights if w['weight']>0}
        if cp in b0 and b0[cp]!=values:raise ValueError('B0_CP_WEIGHT_CONFLICT')
        b0[cp]=values
    capture=json.loads((folder/'D1.json').read_text());observed,=capture['meshes']
    assert capture['input_sha256']==hashlib.sha256((folder/'D1.fbx').read_bytes()).hexdigest()
    labels={b['index']:b['export_label'] for b in observed['bones']}
    per_vertex={}
    for row in observed['bone_weights']:per_vertex.setdefault(row['vertex'],{})[labels[row['bone']]]=row['weight']
    actual={}
    for vertex,cp in enumerate(observed['vertex_control_point_indices']):
        values=per_vertex.get(vertex,{})
        if cp in actual and actual[cp]!=values:raise ValueError('UNITY_SPLIT_WEIGHT_CONFLICT')
        actual[cp]=values
    grouped={}
    for (cp,label),w in raw.items():
        if w>0:grouped.setdefault(cp,{})[label]=w
    model_counts={k:0 for k in models([.5,.5])};classes=dict(A=0,B=0,C=0,UNCHANGED=0)
    result=[];maxBF=0;maxFU=0;maxBFulp=0;maxFUulp=0;bfexact=0
    for cp,weights in grouped.items():
        if set(weights)!=set(b0[cp]) or set(weights)!=set(actual[cp]):raise ValueError('INFLUENCE_ID_SET_CHANGED')
        keys=list(weights);values=[weights[k] for k in keys];predictions=models(values)
        for name,expected in predictions.items():
            model_counts[name]+=sum(bits(v)==bits(actual[cp][k]) for k,v in zip(keys,expected))
        for label,w in weights.items():
            authored=b0[cp][label];native=actual[cp][label];changedBF=authored!=w;changedFU=w!=native
            classes['C' if changedBF and changedFU else 'A' if changedBF else 'B' if changedFU else 'UNCHANGED']+=1
            bfexact+=int(not changedBF);maxBF=max(maxBF,abs(authored-w));maxFU=max(maxFU,abs(w-native))
            maxBFulp=max(maxBFulp,ulp(authored,w));maxFUulp=max(maxFUulp,ulp(w,native))
            result.append(dict(cp=cp,bone=label,B0=authored,F=w,U=native,ulp_BF=ulp(authored,w),ulp_FU=ulp(w,native),
                model_matches=[name for name,prediction in predictions.items() if bits(prediction[keys.index(label)])==bits(native)]))
    aggregate=dict(total_influences=len(result),cp_count=len(grouped),classes=classes,exact_B0_F=bfexact,
        changed_B0_F=len(result)-bfexact,model_exact_counts=model_counts,max_abs_B0_F=maxBF,max_abs_F_U=maxFU,max_ULP_B0_F=maxBFulp,max_ULP_F_U=maxFUulp)
    output.write_text(json.dumps(dict(aggregate=aggregate,private_rows=result),indent=2));print(json.dumps(aggregate))


if __name__=='__main__':main()
