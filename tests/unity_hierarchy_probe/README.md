# Independent semantic hierarchy Oracle

Current checkpoint: original Majun and authored Bone-pose public followups are
GREEN (53 EXACT), including rename/reopen and six actual negative controls.
The real differential remains RED at the source/default geometry boundary. See
[RENDERER_FREE_LOOP.md](RENDERER_FREE_LOOP.md) for current authority and next action.

## Historical phase 1 checkpoint

Status: **PARTIAL**. Unity observation is verified; Unity ↔ Blender parity is
**UNVERIFIED**. No production behavior was changed.

Use a new, isolated Unity 2022.3.22f1 project with standard Unity modules.
Copy `Editor/VapbHierarchyOracle.cs` to its `Assets/Editor/` directory.
Generate `Assets/VapbHierarchy/Model.fbx` using Blender 5.2.1:

```text
VAPB_HIERARCHY_MODEL=<isolated project>/Assets/VapbHierarchy/Model.fbx
blender --background --factory-startup --python-exit-code 1 --python tests/blender_hierarchy_oracle_fixture.py
VAPB_HIERARCHY_OUTPUT=<evidence directory outside repository>
Unity -batchmode -nographics -projectPath <isolated project> -executeMethod VapbHierarchyOracle.Run -logFile <evidence directory>/unity.log
```

Environment variables must be set in the invoking shell. The Unity probe creates
or replaces `Assets/VapbHierarchy/Accessory.prefab` and `Majun.prefab`; run it only
in the isolated synthetic project. It writes `unity_oracle.json` and exports the
corresponding `Majun.unitypackage`. Failure explicitly exits Unity with code 1.

## Observed baseline, 2026-09-30

- Blender fixture generation: exit 0, `VAPB_HIERARCHY_FIXTURE_PASS`.
- Unity Editor version: 2022.3.22f1; actual Editor compilation and execution PASS.
- Unity execution: exit 0, `VAPB_HIERARCHY_ORACLE_PASS`.
- Semantic nodes: 12; parent edges: 11; Renderer owners: 1.
- Skin bones: 2; rootBone present; repeated accessory instances: 2.
- Repeated instances share exact source GUID/localID and have distinct instance
  handles and Transform GlobalObjectIds.
- The fixture includes Head/Face/Hair, two nested accessory instances and an
  attachment under the second Bone. It contains a Model root named Armature
  **and** the FBX Rig child; both are Unity semantic Transforms. This accounts
  for the additional node relative to the eleven-node illustrative hierarchy.

The skin model is unpacked before creating the synthetic prefab so children can
be rearranged using public APIs. Its Mesh remains an FBX subasset reference;
its prefab GameObjects/Bones do not claim an inherited FBX GameObject source
chain. The accessory instances retain their actual source/instance relations.
Names are diagnostic labels, not correspondence keys. Skin bone order is
observed from `SkinnedMeshRenderer.bones`, not inferred from names.

Recorded `unity_oracle.json` is direct public-API output, independent of VAPB
parsers/projection. It includes GUID/signed localID/GlobalObjectId, parent
Transform references, source chains, ordered ancestor instance handles,
Renderer owner/Mesh/rootBone/ordered bones, local TRS and world matrices.
Matrix arrays use Unity Matrix4x4's single-index order (column-major).

Generated public synthetic artifacts remain outside Git. SHA-256 for this run:

| Artifact | SHA-256 |
| --- | --- |
| Majun.unitypackage | `358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098` |
| Model.fbx | `0bbe404623f074ff08666416aa3525346df62ad62691285e17b3b154bd0a9ce3` |

Re-running generation creates a new revision/IDs. Always compare the Oracle
against its own exported package, never a previous Oracle against regenerated
input. Recorded IDs are entirely synthetic. No private corpus was used.

## Remaining acceptance work

Next action: normally import this exact exported package into Blender and
capture occurrence/receipt-based semantic state before any production change.
Then build the independent comparator, obtain baseline RED/GREEN, investigate
any divergence, and verify rename/save/reopen and negative controls.

Blender node/edge/Renderer/Bone/technical-helper counts, parity enum counts,
placement/local/world agreement, save/reopen, negative controls and full Python
regressions are **NOT RUN** for this mission. Earlier 438-test evidence belongs
to the unchanged predecessor and is not a fresh hierarchy acceptance run.
No axis/unit model was changed. Geometry regression need remains undecided
until a concrete production fix is identified. Broad Unity/VRC restoration,
Release/ZIP and private validation were not started.

The phase 1 checkpoint was selected to preserve the requested 15+ credit
reserve from the observed 18.2968137500 opening balance. In-session usage is
not reflected reliably by that balance; unchanged balance is not proof of zero
spend. Only the required read-only scope reviewer was delegated (PASS).

## Exact-package witness and independent observation workflow

The phase 1 status above is historical. Use this workflow to observe an existing
package revision; keep all generated evidence outside the repository. Commands
below run from the repository root in PowerShell. Set the placeholders first:

```powershell
$Blender = '<Blender 5.2 executable>'
$Unity = '<Unity 2022.3.22f1 Editor executable>'
$Package = '<external exact .unitypackage>'
$Sha = '<SHA-256 of that package>'
$SourceProject = '<new external source-control project>'
$OracleProject = '<different new external Oracle project>'
$SelectedPrefab = 'Assets/<selected composition>.prefab'
$BlenderEvidence = '<new external Blender evidence directory>'
```

1. Extract the exact FBX/meta and prepare original, no-op and stamped source
   controls. The preparer currently requires exactly one FBX in the package.

```powershell
python tests/unity_hierarchy_probe/prepare_exact_witness.py $Package $Sha $SourceProject
& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/blender_fbx_source_witness.py -- $SourceProject
$Process = Start-Process -FilePath $Unity -WindowStyle Hidden -PassThru -ArgumentList @('-batchmode','-nographics','-projectPath',('"'+$SourceProject+'"'),'-executeMethod','VapbBoneWitnessProbe.Run','-logFile',('"'+$SourceProject+'/unity.log"'))
$Process.WaitForExit()
$Process.ExitCode
```

Require actual exit 0 and `VapbBoneWitnessResult.json` PASS controls, including
original/no-op/stamped/restored equivalence and restored FBX/meta hashes.
`VapbHierarchyBoneObservation.json` is separate public-API diagnostic evidence:
ordered authored Skin slots, stamped Model UIDs, parent UIDs, origins and full
`local_to_world_matrix` values for Bones and all stamped Models. Matrices are
16 column-major values. Display names never establish correspondence.

2. Promote the exact revision. This preserves v1 and creates v2 with validated
   authored Bone-slot UIDs and optional source Bone world matrices.

```powershell
& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/unity_hierarchy_probe/promote_exact_witness.py -- $SourceProject
```

Outputs are `witness_v1.json` and `witness_v2.json`. Reuse of source controls for
another package requires identical FBX/meta bytes and explicit external reuse
provenance; promote against the new package SHA. Never reuse controls for a
changed FBX or meta revision.

3. Import the exact package independently into a second isolated Unity project.
   The copied package probe observes the selected Prefab through public APIs and
   writes both full `unity_oracle.json` and typed Skin observations.

```powershell
python tests/unity_hierarchy_probe/prepare_exact_witness.py $Package $Sha $OracleProject
$env:VAPB_HIERARCHY_SELECTED_PREFAB_PATH = $SelectedPrefab
$Process = Start-Process -FilePath $Unity -WindowStyle Hidden -PassThru -ArgumentList @('-batchmode','-nographics','-projectPath',('"'+$OracleProject+'"'),'-executeMethod','VapbHierarchyPackageSkinObservation.Run','-logFile',('"'+$OracleProject+'/unity.log"'))
$Process.WaitForExit()
$Process.ExitCode
Remove-Item Env:VAPB_HIERARCHY_SELECTED_PREFAB_PATH
```

The package observer may enable Model readability in this isolated diagnostic
copy. The package archive stays unchanged. Keep dependency state explicit;
missing external scripts/shaders do not become restored components by observing
the available Transform/Renderer/Mesh/Bone APIs.

4. Normally import that same package into Blender with the witness and capture
   the native representation through the snapshot hook.

```powershell
$env:VAPB_HIERARCHY_WITNESS = "$SourceProject/witness_v2.json"
$env:VAPB_HIERARCHY_SOURCE_OBSERVATION = "$SourceProject/VapbHierarchyBoneObservation.json"
$env:VAPB_HIERARCHY_PACKAGE_OBSERVATION = "$OracleProject/VapbHierarchyPackageSkinObservation.json"
$env:VAPB_HIERARCHY_CONTROL_REPORT = "$SourceProject/VapbBoneWitnessResult.json"
& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/blender_hierarchy_snapshot.py -- $Package $Sha $SelectedPrefab $BlenderEvidence
Remove-Item Env:VAPB_HIERARCHY_WITNESS,Env:VAPB_HIERARCHY_SOURCE_OBSERVATION,Env:VAPB_HIERARCHY_PACKAGE_OBSERVATION,Env:VAPB_HIERARCHY_CONTROL_REPORT
```

`blender_snapshot.json` includes `native_skin`; `baseline.blend` preserves the
normal import. Native observation validates exact Mesh identity and receipt
UIDs, authored Skin slots, live Armature/Bone targets, semantic carriers and
transient pose motion/restoration. Observation alone does not declare parity.
Full Bone-frame diagnostics compare evaluated native world matrices with
`convertedPrefabWorld * inverse(convertedSourceWorld) * nativeRestWorld`.

### Geometry measurement boundary

The Unity probe uses `BakeMesh(mesh, useScale: true)` followed by the renderer
Transform's `TransformPoint`. For the public nonuniform-scale fixture, this was
checked against Renderer bounds and explicit public-API weighted skinning on
scene instances. The default/false overload followed by TransformPoint applied
scale twice and was not a valid Oracle measurement. This is a measured boundary,
not a general guarantee for every animation/dependency state.

Unity baked triangle corners and Blender evaluated triangle corners corroborate
surface geometry without pairing split/welded vertices by index. They do not
prove UVs, normals, materials, or overall representation equivalence.

For source/default geometry diagnostics, run `source_geometry_boundary.py` in
Blender with `-- BLEND SOURCE_OBSERVATION CONTROL_REPORT OUTPUT`. It selects
source-cache Meshes through exact realization/receipt links. BVH distances sample
triangle corners, edge midpoints and centroids in both directions; triangles
with area at most `1e-12` are counted and excluded from that surface sampling.
Referenced-corner point coverage is reported separately from all Mesh vertices.
Finite samples are diagnostics and never establish full surface equivalence.
Optional `--triangulate-mode FIXED` (also `FIXED_ALTERNATE`,
`SHORTEST_DIAGONAL`, `LONGEST_DIAGONAL`, `BEAUTY`) inserts a temporary standard
Triangulate modifier before Armature evaluation. `--ngon-mode CLIP` can replace
the default `BEAUTY` n-gon mode. The tool records raw polygon/zero-area counts,
removes the temporary modifier and asserts restoration; it never saves the Scene.
