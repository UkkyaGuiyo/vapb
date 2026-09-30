# Exact public Shape channel experiment

## Measured acceptance checkpoint

Public two-occurrence normal Import: Shape **6 EXACT**, hierarchy **38 EXACT**,
geometry **2 EXACT**. Nine actual corruptions are rejected; Object/Bone/KeyBlock
rename/save/reopen passes. The independent comparator rejects missing/empty
witness mappings even when another shaped Mesh passes. Repository-parent Python
suite: **467 PASS**. Blender 5.2.1 process checks use `--python-exit-code 1`.

Private aggregate only: **171 channels / 11 shaped Meshes** pass exact UID and
occurrence-weight checks on fresh Import and rename/save/reopen. Hierarchy stays
**1,274 EXACT**. Geometry remains **14 EXACT / 20 mismatch**: two RED Skins change
corners after weight realization but remain RED; eighteen RED Skins do not change.
This is causal separation, not a geometry parity claim.

The promoted optional witness uses schema `vapb-model-identity-witness-v3`.
`promote_shape_witness.py` takes v2 witness, channel controls, exact source FBX,
exact source meta, independent Shape oracle and a new output file, under Blender.
The source graph, frame controls and exact hashes must all agree. Native receipt
capture uses the installed FBX importer's returned UID-to-KeyBlock handles.
Production supports the measured direct local Renderer scope; nested Shape
overrides and progressive frames are not inferred. Edited/reordered Key data
invalidates import-time proof rather than being rematched by a display name.

This firstparty probe uses Unity 2022.3 public APIs. Outputs stay in new external
projects. Channel names are diagnostic; ordinary names, array order and channel
counts do not prove an FBX UID correspondence.

Run from the repository with external paths substituted:

```powershell
$Unity = 'C:/Program Files/Unity/Hub/Editor/2022.3.22f1/Editor/Unity.exe'
$Blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
$Evidence = 'C:/external/shape-evidence'
$env:VAPB_SHAPE_FIXTURE_FBX = "$Evidence/input/Source.fbx"
& $Blender --background --factory-startup --python-exit-code 1 --python tests/blender_shape_identity_fixture.py
Remove-Item Env:VAPB_SHAPE_FIXTURE_FBX
python tests/unity_shape_probe/prepare_probe.py create "$Evidence/input/Source.fbx" "$Evidence/creator"
& $Unity -batchmode -nographics -projectPath "$Evidence/creator" -executeMethod VapbShapeProbe.Create -logFile "$Evidence/create.log"
$Package = "$Evidence/creator/ShapeOccurrences.unitypackage"
python tests/unity_shape_probe/prepare_probe.py oracle $Package "$Evidence/oracle"
& $Unity -batchmode -nographics -projectPath "$Evidence/oracle" -executeMethod VapbShapeProbe.Run -logFile "$Evidence/oracle.log"
$env:VAPB_HIERARCHY_SELECTED_PREFAB_PATH = 'Assets/VapbShape/ShapeOccurrences.prefab'
& $Unity -batchmode -nographics -projectPath "$Evidence/oracle" -executeMethod VapbHierarchyPackageSkinObservation.Run -logFile "$Evidence/hierarchy.log"
Remove-Item Env:VAPB_HIERARCHY_SELECTED_PREFAB_PATH
$Sha = (Get-FileHash $Package -Algorithm SHA256).Hash.ToLowerInvariant()
python tests/unity_hierarchy_probe/prepare_exact_witness.py $Package $Sha "$Evidence/witness"
& $Blender --background --factory-startup --python-exit-code 1 --python tests/blender_fbx_source_witness.py -- "$Evidence/witness"
& $Unity -batchmode -nographics -projectPath "$Evidence/witness" -executeMethod VapbBoneWitnessProbe.Run -logFile "$Evidence/bones.log"
& $Blender --background --factory-startup --python-exit-code 1 --python tests/unity_hierarchy_probe/promote_exact_witness.py -- "$Evidence/witness"
& $Blender --background --factory-startup --python-exit-code 1 --python tests/blender_shape_channel_witness.py -- "$Evidence/witness"
python tests/unity_shape_probe/prepare_probe.py controls "$Evidence/witness" "$Evidence/shape-controls"
& $Unity -batchmode -nographics -projectPath "$Evidence/shape-controls" -executeMethod VapbShapeControls.Run -logFile "$Evidence/shape-controls.log"
```

For a process exit witness in PowerShell, launch Unity with `Start-Process
-WindowStyle Hidden -PassThru`, call `WaitForExit()`, and record `ExitCode`.
The output marker alone does not establish the process exit status.

`UnityShapeObservation.json` records exact package/FBX/meta hashes, Mesh GUID and
signed localID, channel index, diagnostic name, every frame weight and position,
normal and tangent delta array. Renderer component identities own serialized and
current weights. The fixture fully unpacks the imported model before saving;
both Renderer components and their Bone hierarchy are local prefab content.
Two occurrences share the same Mesh and authored Bone array,
with weights `[25,60,0]` and `[75,0,35]`. Baked world points use `BakeMesh(true)`
and the renderer Transform, following the existing hierarchy probe's measured
scale boundary. This observation alone does not prove general geometry parity.

`UnityShapeChannelControls.json` imports original → no-op → marked → restored
copies with exact source meta. A mapping is usable only if all controls pass:
exact Mesh GUID/localID, base vertex/triangle signature and per-index frame
weights/deltas remain identical; all observed UID markers are unique; final
FBX/meta hashes are restored. Marker input construction separately proves that
only authored Shape/BlendShapeChannel display labels changed. This bounds the
experiment to its exact source revision; it does not authorize ordinary
name-based matching or a guessed fallback.

Control schema 2 stores `original/noop/marked/restored.meshes`; each Mesh row is
keyed by its GUID and signed localID. Comparison rejects duplicate identities
and joins dictionaries by that exact identity, independently of Mesh ordering.
Channel indices remain explicit slots within their exact Mesh.

For an existing exact package, set `VAPB_SHAPE_MODEL_PATH` to its FBX asset path
and `VAPB_SHAPE_SELECTED_PREFAB_PATH` to the selected prefab asset path before
`VapbShapeProbe.Run`. The preparer writes the sole FBX asset locator to external
`SelectedModelPath.txt`; locators select assets and do not establish channel
identity. Keep private locators and all raw output outside the repository.
Set `VAPB_SHAPE_INCLUDE_FRAME_DELTAS=0` for a compact oracle: the report explicitly
records `include_frame_deltas=false`, omits the raw delta arrays and retains
frame weights plus SHA256 signatures of the public API delta arrays. Full-array
serialization can exceed JsonUtility's practical limits on large inputs.

The bone witness v2 remains separate and unchanged. The existing hierarchy
README documents normal VAPB snapshot and native Bone observation commands.

## Public truncated-array control

Keep the full-weight fixture above as the main two-occurrence case. For a
separate new creator project, set `VAPB_SHAPE_TRUNCATE_WEIGHTS=1` only while
running `VapbShapeProbe.Create`. Its first local Renderer stores one weight
(`[25]`); the second stores an empty array. Import the resulting package into a
fresh oracle project and run `VapbShapeProbe.Run` without that environment flag.
Compare exact Renderer identities and serialized/current arrays in the oracle.
The observed public fixture returns `[25,0,0]` and `[0,0,0]`, respectively,
while the unchanged source model returns `[100,100,100]`. This is a measured
serialized-array default boundary for this independent fixture, not padding
performed by the probe. The probe calls `GetBlendShapeWeight` for every valid
Mesh channel index and records the returned values independently of array length.

[SerializedProperty.arraySize](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SerializedProperty-arraySize.html)
documents the array truncation used in this control.

Public API references:

- [GetBlendShapeFrameVertices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetBlendShapeFrameVertices.html)
- [GetBlendShapeWeight](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SkinnedMeshRenderer.GetBlendShapeWeight.html)
