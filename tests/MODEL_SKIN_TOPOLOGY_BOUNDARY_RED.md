# Public synthetic normal model-Skin topology-boundary RED

This prepares a fixture and expected-rejection probe. It does not change the
Finalizer and does not claim Unity was run.

## Exact fixture contract

`--topology-boundary-vertex-split` prepares a smooth quad with one material,
triangulated into two faces. The source has four vertices, two faces, and six
triangle indices:

```text
source faces: [0,1,2], [0,2,3]
source groups: Root 1.0 on v0,v1; Child 1.0 on v2,v3
```

The Blender-final mesh duplicates both endpoints of the shared edge for the
second face, copies each endpoint's bone weight, and remaps only vertex sharing:

```text
final faces: [0,1,2], [4,5,3]
final groups: Root 1.0 on v0,v1,v4; Child 1.0 on v2,v3,v5
source/final faces: 2 / 2
source/final indices: 6 / 6
source/final vertices: 4 / 6
submeshes/materials: 1 / 1
```

The duplicated positions equal their source endpoints. Only the UVs at the two
duplicated corners differ, creating a seam so the destination importer retains
the vertex split. All face positions, material assignments, bone weights,
bones/root/rest mapping, and shape schema (empty on both sides) remain fixed.
This tests a vertex-layout/index-reference change induced by a UV seam: the two
triangle faces cover the same positions, while their shared-edge vertex
connectivity differs. It does not claim general topology-edit support. Pure
assertions for arrays, face geometry, UVs, and copied weights live in
`tests/test_model_skin_topology_boundary_fixture.py`.

## Reproduction route

Use one marked, disposable Unity 2022.3.22f1 SourceProject/TargetProject pair.
The prepared route uses only synthetic assets and the product exporter:

1. Run `blender_skin_package_test.py -- <run-root>/SourceProject
   --prepare-fbx --topology-boundary-vertex-split` to generate
   `Assets/VapbSkinRoundtrip/Input.fbx`.
2. Run `VapbModelSkinTopologyBoundarySourceFixture.Prepare` in SourceProject.
   This imports the FBX, applies the readable/material-name/weld/optimization
   settings, creates `Original.mat` and an outer Avatar prefab that retains a
   nested model-prefab instance, then writes `Source.unitypackage` and fixture
   evidence with create-new semantics.
3. Copy `Source.unitypackage` into a fresh `ModelSkinEvidence` directory and
   create `case.json` as `{"vertex_split_only": true}`. Run
   `blender_model_skin_package_test.py -- <run-root>/ModelSkinEvidence` to use
   the real importer, mutate only the synthetic skin mesh, save/reopen, and
   invoke the normal Blender model-Skin exporter. It writes the ordinary
   `Output.unitypackage` and `TopologyBoundaryEvidence.json`.
4. Copy that package to `<run-root>/Output.unitypackage`. Run
   `model_skin_topology_boundary_package_preflight.py -- <run-root>` before
   importing it. For this reviewed disposable run, the preflight requires the
   exact 12-path set and package SHA256
   `157eee6379cc435ad9829db2011c1dabeb6f44259d97c385d6e47e3c2db8da73`. This
   hash pins this one reviewed run, including its generated FBX bytes; it is not
   a reusable hash for regenerated FBX fixtures. A regenerated package must be
   independently reviewed and receive its own exact package/inventory pins.
   It verifies every package asset pathname, GUID, payload/meta pair, the four
   canonical support-script payloads, all TargetProject path/GUID collisions,
   and exactly one normal `RESTORE_MODEL_SKIN_VARIANT_V1` task. It writes
   `OutputPackageInventory.json`; ImportRunner accepts only that exact package
   SHA and the reviewed inventory SHA256
   `e8dd9cec0cdee54eb777c4e3779f47d8347fd620f3e7fe701cf62852a800255f` before
   `AssetDatabase.ImportPackage`.
5. Before package import, move only the already-staged
   `Assets/VAPBModelSkinTopologyBoundary` fixture folder (including its folder
   `.meta`) outside TargetProject/Assets and preserve its inventory/hashes. The
   package supplies the product marker and Finalizers at their canonical
   paths. Stage ImportRunner in an independent Editor folder and invoke
   `VapbModelSkinTopologyBoundaryImportRunner.ImportAndCaptureBaseline`.
   After its baseline passes, stage only
   `VapbModelSkinTopologyBoundaryRedProbe.cs` and its `.meta` back into the
   owned fixture folder and invoke `VapbModelSkinTopologyBoundaryRedProbe.Run`.

The source fixture contains one package-backed Standard material. The Blender
topology-boundary case explicitly binds that one imported material identity
before rebuilding the mesh; the actual importer initially created a
same-named synthetic FBX material without Unity GUID provenance. Keeping the
package-backed material in this test is necessary for the real exporter to
reach the topology task, and the material identity is recorded in the fixture
evidence. The earlier failed export attempt is retained separately for audit.

The expected current Finalizer result is
`VAPB_MODEL_SKIN_VARIANT_REJECTED=TOPOLOGY_OR_LAYOUT_CHANGED`, no Variant at the
task path, and unchanged source/final model, source Prefab, manifest, and their
meta files. The RED probe requires `VAPB_STAGE3_TEST_ROOT`, exact Source/Target
direct-child paths, ownership markers, Unity 2022.3.22f1, no Git checkout in
the root ancestry, no reparse points on owned paths, and an unoccupied result
path. The result uses create-new semantics. Mesh preconditions compare
geometric triangle rows and weights mapped through source bone UIDs, then
prove exactly two source shared-edge vertices are UV-split into pairs with a
0.25 U offset. The probe rejects zero weights, a DirectKind task, other mesh
counts, shape/submesh differences, a pre-existing Variant, missing
components, or any component outside Transform, SkinnedMeshRenderer, and VAPB
realization/export markers.

This reviewed run also relies on the existing Target-only runtime definition
`Assets/VAPBFinalState/VapbExportObjectMarker.cs`, which is outside the eight
fixture staging files moved before package import and outside the 12 package
paths. Its SHA256 is
`01e692ecda93ed309f284c743e32caa6c46f94d6b81c51ca91d5a94495b41eb1`, matching
`unity_editor/VapbExportObjectMarker.cs` at the reviewed repo HEAD. The
`VapbModelSkinTopologyBoundaryRedProbe` references that type when checking the
allowed component set. This fixture is not self-contained on a clean Target:
preserve/provide the reviewed runtime marker dependency before compiling the
probe. Do not move or alter `VAPBFinalState` as part of this run.

Current verified fixture artifacts: source FBX export passed at 4 vertices,
2 faces/6 indices, and 2 bones; SourceProject generated the nested-instance
package; the Blender importer/exporter completed the vertex-split package;
the package preflight passed for 12 assets and one normal model-Skin task.
The TargetProject import/baseline and RED probe still require parent review of
the exact local fixture diff before Unity runs.

## Explicit unsupported scope

This RED uses a minimal synthetic hierarchy only. Any additional or unknown
component that could hold vertex/index-addressed state is unsupported for a
layout-changing Green and must remain a rejection condition before Variant
creation, with source and manifest bytes/meta unchanged. Cloth remains an
explicit rejection. Do not generalize acceptance to arbitrary Prefabs,
components, topology edits, shape-key changes, or DirectKind. Product guards
remain unchanged until the parent reviews the RED evidence and the narrow
acceptance policy.
