# Inbound material face membership diagnostic — 2026-10-07

## Bounded result

The unchanged comparator returns `UNPROVEN_ORIENTATION_OR_FRAME`. This is **not** a product acceptance PASS.

Separately, this pinned fixture establishes geometric face membership modulo **one uniform winding reversal**, at six-decimal coordinate quantization. Full corner triples and multiplicities, without fitting coordinates or using material names/counts to choose the mapping, uniquely associate Unity source submeshes 0/1/2 with Blender material partitions 2/1/0. All 12 triangles match under the same reversal in four stages: raw FBX native import, fresh package import before Confirm, after Confirm, and the previously saved confirmed scene.

In the reproduced transition, effective material GUID/fileID/package identities are blank before Confirm. Confirm finishes, installs scoped OBJECT materials in serialized Renderer order, and leaves geometry, relative matrices and polygon material indices unchanged. Two resulting material identities disagree with corresponding source faces. The saved confirmed scene repeats this mismatch.

| Source material (all local IDs 2100000) | Source faces | Faces receiving this material after Confirm | Geometric source submesh → Blender partition |
| --- | ---: | ---: | --- |
| Mat2: eb805efb35118044db5e74adc652673a | 6 | 2 | 0 → 2 |
| Mat1: 0318f358e4c29034aa90cc8c50b58a93 | 4 | 4 | 1 → 1 |
| Mat0: 64f92a1bd9b35a040bf9e2c6d200b34c | 2 | 6 | 2 → 0 |

The six-face source Mat2 partition receives Mat0 after Confirm; the two-face source Mat0 partition receives Mat2. A global winding reversal does not change triangle membership and cannot explain this GUID swap. This supports a fixture-bounded inbound confirmation assignment defect; it does not establish a Finalizer defect.

## Provenance and execution

- Product checkout: `2288f5a714b5018f7f29c05a726851be86dfbef0`. Target branch: `feature/r2-material-slot-reorder`.
- Blender 5.2.1, one owned process PID 43360, 2026-10-07 14:05:47.7575052Z–14:05:59.0009530Z, exit 0.
- No new Unity process, no .blend save or FBX export. Seven input hashes unchanged; owned Blender absent and existing Unity Target count 0 at postflight.
- Fresh Blender factory scene imported the unchanged public package through the product operator, then called the existing `vapb.confirm_renderer_binding` once. This is an in-memory reproduction, not a historical pre-confirm snapshot.
- Read the existing confirmed blend without embedded script execution; never saved it back.
- LUNA low authored diagnostic code. SOL medium approved the frozen code/launcher and reviewed actual results. Astra medium independently reviewed the bounded interpretation.
- Comparator shell returned 1 for its non-success verdict; the script intentionally exits nonzero for any verdict other than `MAPPING_PROVEN_DIAGNOSTIC`. The unproven result is preserved.

### Exact hashes

| Artifact | SHA-256 |
| --- | --- |
| Original ThreeSlotSource.unitypackage | d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c |
| Original Input.fbx | fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5 |
| Original Input.fbx.meta | ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d |
| Existing saved confirmed blend | 58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c |
| [Existing Unity diagnostic](unity-diagnostic.json) | af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2 |
| [Capture script](capture_inbound_material_faces.py) | e8d241a09d74d33f7a9ce7ffebe1e1c62158bc02a540c40fc6f988e550878b11 |
| [Comparator](compare_material_face_partitions.py) | dd10c12ad7cf199e3a7f8f84cdb0058c010c40e6c8a074cc250090d717ed3f46 |
| [Capture](capture.json) | c0949a10fa0b4ab789d21d62ee4381742240d116f7de5067048fbd7a19f686a7 |
| [Comparison](comparison.json) | 7d23b9ab0d06ff8a8ff307e9489d2d422ca4b37bfeb938aac7170e61429d7918 |

The existing Unity report's `package_sha256=20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd` belongs to the **exported output package**. It is not the original fixture identity. The source-content join verifies original FBX/meta and Prefab/meta bytes, source Mesh GUID/fileID, raw Renderer identity and Material refs. Both package contexts remain distinct. The source join reports PASS.

Source Mesh is `abcdefabcdefabcdefabcdefabcdefab / 3538053534738119282`, Renderer `3728717051629469441`, Prefab `7cbdcbe81fde386408bcfb379e62b6bb`, FBX Model/Geometry UIDs `208084244 / 329684292`.

## What the artifacts contain

- `capture.json`: source revision join, raw FBX GlobalSettings/model properties/material layers/connections, native FBX import, saved scene, and fresh before/after Confirm mesh corners/slots/transforms/receipts. Product module hashes are recorded.
- `comparison.json`: both oriented and globally reversed candidates. Direct winding equality is false in all four stages; uniform reverse equality is true. The accepted top-level mapping remains null. Reverse candidates and their identity failures are evidence, not a production mapping.
- `execution.json`: sanitized process ledger and selected log lines. Raw local logs and ledger are not published.
- `unity-diagnostic.json`: unchanged earlier public synthetic Unity observation; this run did not launch Unity.

Controls passed: 720 permutations of six distinct partitions, equal-count disjoint geometry, an equal-count face-label swap rejection, cyclic rotation, reversed winding detection, changed geometry, duplicate/empty/unused partitions, repeated exact material identity, multiplicity, wrong identity/package, and stale metadata. These are diagnostic comparator controls, not production regression tests.

## Limitations and next design boundary

Six-decimal equality is precision-bounded, not bitwise equality. Winding/front-face fidelity and the cause of the observed reversal remain unproven. This finding proves neither normals, vertex lineage, deformation nor a general importer permutation. Do not hardcode 0/2 reversal or fix the Finalizer using source ordinal order.

The concrete assignment seam is `operators/renderer_binding.py`: a serialized Renderer material array is assigned directly to same-numbered Blender material slots. Existing witness/dependency code also carries that ordinal without a geometric partition contract. The current Confirm UI establishes Renderer↔Mesh identity, not explicit face mapping.

See [the saved comparison plan](../../../docs/R2_MATERIAL_PARTITION_DIAGNOSTIC_PLAN_20261007.md) for manual mapping, optional geometry witness, and scoped unresolved behavior. No product option, schema extension or compatibility policy was selected here. Normal import must not require Unity Editor/project (PRODUCT_SPEC.md:17,457–458); development observations and an optional exact-revision witness are allowed. The existing witness does not prove material face partitions. A product fix needs a trustworthy correspondence contract and ambiguity behavior; this diagnostic supplies a bounded RED case for that work.
