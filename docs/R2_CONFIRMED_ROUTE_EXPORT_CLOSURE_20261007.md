# Confirmed-Route Export and Archive Observation

Date: 2026-10-07  
Project: VAPB  
Repository: https://github.com/UkkyaGuiyo/vapb  
Branch: `feature/r2-material-slot-reorder`  
Evidence run: disposable Blender 5.2.1 LTS processes; no Unity Editor run

## Result

The existing fresh-process-reopened `USER_CONFIRMED` scene was exported through
the normal `export_scene.vapb_unitypackage` operator using the direct model-skin
route. The export reported `RESTORE_DIRECT_SKIN_VARIANT_V1`. A separate fresh
Blender process inspected the generated package and imported its generated FBX.
This is a bounded **confirmed-route export observation**. It does not change the
strict no-edit T0-A **FAIL** or the T0-B **BLOCKED** status.

| Evidence | Observed value |
|---|---|
| Input UnityPackage SHA-256 | `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c` |
| Reopened source blend SHA-256 | `58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c` |
| Output UnityPackage SHA-256 | `f2ad9a77339cc85baa03e621f4e724add15d30c10bb99be5cde5c9dfb5c26e65` |
| Generated FBX SHA-256 | `66c73d0c91ee03f76ac7a779342d31491948684ee8dda14e6140dc0734ca509e` |
| Export result | `PASS`; source package has 6 records, output has 15 |
| Closure checker result | `CONFIRMED_ROUTE_CLOSURE_PASS`; separate fresh Blender process, exit 0 |

The six source archive records retained the same asset payload, `.meta`, and
path. The three source Material payloads and metadata were byte-identical. The
raw Prefab references the three expected Material GUIDs, each with local file
ID `2100000`; the export manifest carried those references and the three
corresponding transport IDs. The generated FBX was listed in the manifest and
its payload hash matched the manifest. The manifest declared no external
dependencies. Its three shader references point to Unity's built-in shader
GUID; the source Materials have no non-null Texture references, so Texture
closure is N/A for this fixture.

The independent FBX import observed three material groups in the expected
transport-ID order and triangle counts `[2, 4, 6]`. For each group, the
multiset of world-space triangle coordinate signatures matched the confirmed
scene after coordinates were rounded to six decimal places and vertex order
within each triangle was sorted. This checks the recorded geometric grouping;
it does not establish winding, UV preservation, or skin-deformation
preservation.

The recorded scene snapshot digest before and after export was the same
(`c0f17bbbef9e2b3c193826890532fc06d9a292f1b1b3c6307e9d189d8c3aeee1`). This
means the fields included in that snapshot matched; it is not a proof that
every scene property, such as all material nodes, UV data, and images, was
unchanged. Likewise, `external_dependencies=[]` and the manifest listing all
new output records are observed checker values, not an independent general
dependency-graph proof. The checker did not run a required-Material-removal
negative control or inventory the entire source archive store before and
after export.

## Limitations and status

- This run used the explicitly confirmed binding route. Strict no-edit T0-A
  remains **FAIL** for this fixture; T0-B remains **BLOCKED** behind that gate.
- Unity was not run. No general Unity import or runtime claim follows from this
  Blender archive/FBX inspection.
- The result is limited to this synthetic fixture and this confirmed scene.
  It does not establish universal dependency closure or automatic Mesh ID
  mapping.

## Evidence artifacts

The run produced `export-result.json`, `closure-result.json`,
`fbx-material-facegroup-result.json`, and process logs. The export and
independent verification ran in distinct Blender processes. The correction to
the verifier normalized JSON tuple/list representations before exact nested
comparison; coordinate values, nesting, cardinality, and GUID group remain in
the equality check. Early attempts that aborted before the product export
produced no result and were not used as passing evidence.
