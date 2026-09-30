# Diagnostic control-point transport

## Measured residual checkpoint

Public nonplanar CP topology is RED with four affected polygons and 18 triangles
in each runtime. Public three-Shape topology is EXACT. Source CP connectivity
for the measured real input is **14 EXACT / 20 mismatch**, matching its separate
Prefab geometry categories by exact Mesh/owner identities. No surface equality
is inferred from CP transport alone.

`tests/control_point_comparator.py` consumes four matching hashes, both runtimes'
noninterference controls and observed-set removal/range negatives. It reports
every Mesh, including any unproven map as RED. An observed-vertex proof does not
override strict source coverage failure or claim a raw-CP bijection.

`tests/blender_geometry_tessellation_candidates.py` tests first fan,
Blender FIXED/EAR_CLIP with transported integer CP attributes, and first-plane
bounded CDT with original vertex/face IDs. All three fail the public nonplanar
RED. CDT matches the omission fixture only; none is a validated production fix.
This is the mission's three-candidate reassessment boundary. Python **474 PASS**;
compileall and final bounded scope review PASS. No production geometry change.

GPL-3.0-or-later firstparty tooling. This uses a spare FBX UV layer and Unity
2022.3 public APIs; it does not change production topology or choose triangles.
The UV values are explicit markers `(raw_control_point_index + 1, 0.375)`.
Ordinary labels, candidate counts and geometric proximity do not establish
identity. Meshes join by exact GUID and signed localID from an existing validated
source witness; raw Geometry UID selects the corresponding source array.

```powershell
$Blender = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
$Unity = 'C:/Program Files/Unity/Hub/Editor/2022.3.22f1/Editor/Unity.exe'
$Source = 'C:/external/source-witness' # Source.fbx, Source.fbx.meta, witness_v2.json
$Project = 'C:/external/new-control-project' # must not exist
& $Blender --background --factory-startup --python-exit-code 1 --python tests/unity_geometry_probe/prepare_control.py -- $Source $Project
$Process = Start-Process $Unity -ArgumentList '-batchmode','-nographics','-projectPath',$Project,'-executeMethod','VapbControlPointProbe.Run','-logFile',"$Project/unity.log" -WindowStyle Hidden -PassThru
$Process.WaitForExit()
$Process.ExitCode
& $Blender --background --factory-startup --python-exit-code 1 --python tests/unity_geometry_probe/classify_missing_points.py -- $Project "$Project/missing-points.json"
```

Preparation preserves the original source files and creates `Source.fbx/meta`,
`Noop.fbx`, `Stamped.fbx`, and `ControlPointManifest.json` in a new isolated
project. Decoding the encoded files independently verifies the marker values;
removing only the new UV layer/reference must recover the original canonical
FBX. Existing UV sets must be contiguous and leave an unused channel below 8.
The target Unity UV channel must also be empty before stamping. No occupied or
generated UV channel is overwritten to make a control pass.

`UnityControlPointBridge.json` contains all four checked input hashes and
original/no-op/stamped/restored Mesh rows. Ordered base, submesh, skin, existing
UV and shape arrays compare exactly solely as non-interference controls. A
stamped row with `observed_vertex_map_valid` exposes `vertex_control_point_indices`,
`triangle_vertex_indices`, and `triangle_control_point_indices`. Source index
markers establish the correspondence; array ordering alone does not.

The initial contract requires full raw control-point coverage and rejects
fractional, nonfinite, sentinel, out-of-range and missing markers. Legitimate
Unity vertex splits may repeat one raw control-point marker. In-memory negative
controls remove an entire CP's coverage through duplication and introduce an
out-of-range marker; neither modifies an asset. Missing-point diagnostics record
failure categories and exact absent CP indices outside the repository.

`observed_vertex_map_valid` separately requires every observed Unity vertex to
have a finite integer marker in range, the exact sentinel, and a UV array whose
length equals the vertex count. `raw_source_cp_complete` reports whether all raw
source CPs were observed. Missing raw CPs do not fabricate Unity vertices: a
qualified observed map may be emitted while strict `marker_valid` and report
`pass` remain false. Its use still requires all four exact input hashes and all
original/no-op/stamped/restored signature and restoration guards. An additional
negative control removes a CP from the fixed original observed set and verifies
`negative_observed_set_removal_rejected`; out-of-range markers also remain rejected.

`classify_missing_points.py` checks all four revisions and import/restoration
flags before joining missing CPs to raw `PolygonVertexIndex` membership. It
separates loose points, points referenced only by zero-area/degenerate base
polygons, and points referenced by positive unsigned fan-area base polygons.
Immediate-neighbor equality, distances, cross norms and thresholds are explicit.
The fan-area measurement does not infer Unity's tessellation algorithm. Base
position classification does not prove behavior at all shape/skin deformations;
membership in Shape index arrays does not itself prove movement. Classification
does not relax the acceptance contract.

Public nonplanar and three-shape controls passed actual Unity execution with
source/meta restoration. The private control preserved every import signature
but failed full coverage on five Meshes; that RED remains recorded. No general
geometry equivalence follows from a successful marker transport.

A separate public nine-control-point fixture acquired fresh Unity package,
independent channel oracle and actual source bone controls. All import signatures
and restoration passed, but Unity exposed seven CP markers: one raw loose point
and one exactly coincident adjacent polygon corner were absent. Strict coverage
remained RED. The fully degenerate triangle's points were retained in this case;
do not infer that this fixture reproduces every private omission category.
The separate observed-map run decoded all seven public Unity vertices and all
34 private Meshes, including the five with incomplete raw coverage. Both strict
runs exited 1. Observed-set removal and range negatives passed, and every emitted
triangle CP was checked against its decoded vertex marker. This proves transport
for observed vertices, not complete source realization or geometry equivalence.

Documented APIs and data semantics:

- [Unity Mesh.GetUVs](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetUVs.html)
- [Unity UV channel swapping](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-swapUVChannels.html)
- [Autodesk FBX mapping and direct-array modes](https://help.autodesk.com/cloudhelp/2020/ENU/FBX-API-Reference/cpp_ref/class_fbx_layer_element.html)
