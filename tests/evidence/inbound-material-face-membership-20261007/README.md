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

## Offline frame derivation (2026-10-07)

The raw FBX frame was derived from its GlobalSettings and Geometry-to-Model/parent chain using the installed Blender 5.2 importer/parser source. The derived G·L predicts the captured native-import point transform with maximum matrix residual 3.9745984281580604e-14; all 12 raw triangle corner triples match that transform. The source Model geometric transform is identity and no ancestor geometric transform is inherited.

For this exact fixture, the predeclared candidate C = 0.01·reflectX maps the raw FBX vertex position set to the captured Unity source mesh vertex set, allowing Unity vertex splits. The full triangle multiset matches only under one uniform corner reversal; direct corner order does not match. The 12 unoriented raw triangle signatures are unique at six-decimal quantization, so this fixture’s geometric triangle correspondence is unique. The independently recorded B·M·C vs G·L maximum matrix residual is 7.549789948769024e-8.

This is a fixture-specific measured relationship, not a general Unity importer rule. The pinned Unity metadata has bakeAxisConversion=0 and file units/scale enabled, but does not independently establish the candidate mesh-local factorization or index-reversal provenance. Accordingly the comparator remains UNPROVEN_ORIENTATION_OR_FRAME; mapping=null is preserved, and no product fallback or slot permutation is selected.

The pure perturbation controls rejected changed axis, unit, Model transform, and candidate reflection; index reversal was detected separately. The existing comparator’s label-swap, equal-count, duplicate, ambiguous and multiplicity counterexamples remain unchanged. This offline diagnostic did not start Unity or edit inputs. It used Blender 5.2’s bundled Python to parse the pinned FBX and installed importer source; a separate Blender CLI version sanity check exited normally, with no project import/save.

| Artifact | SHA-256 |
| --- | --- |
| [Frame verifier](verify_inbound_frame.py) | 67cb45077ecc676ea25f52e5f468d05b6c66f3c88643cb20b17ebc3ccea3341d |
| [Frame result](frame-diagnostic-v3.json) | 9e740f2654e3c1a885ae8b291583ae6b2f67cee7004c4c2bc59366d34ff84e42 |

LUNA low authored and ran the offline verifier; SOL medium reviewed the final script/result. The first reviewer pass found missing signature-uniqueness assertion, misleading vertex-count semantics, and an unisolated reflection control; these were corrected before the final run/review. The unique-position comparison explicitly allows Unity vertex splits.

## Diagnostic file ownership and parser source pin (2026-10-08)

A review found that the verifier derived a fixed temp FBX path from its final output, used an existence check followed by a write, and unconditionally unlinked that path. Concurrent runs could collide, and a dangling symlink could pass the existence check. The verifier now creates an unpredictable temp file with exclusive creation, records its device/inode identity, and only removes it when the current path still names that regular file. The final JSON retains exclusive x creation.

The parser loader also now checks the expected SHA-256 of Blender 5.2’s import_fbx.py, fbx_utils.py, and parse_fbx.py before importing the parser module. A wrong-hash synthetic control rejects the input before import. The script sets sys.dont_write_bytecode=True before the target parser import. The installed source tree had no .pyc files after the run. This is a fresh CLI process; an embedded interpreter with an already-cached parser module is outside this check.

Synthetic controls passed for preserving an existing fixed-path file, two overlapping calls using distinct temp files, cleanup after a parse-like exception, preserving a replacement inode, and rejecting a wrong parser revision before import. The dangling-symlink control was skipped because the operating system denied symlink creation; no security setting was changed. The immediate device/inode check followed by unlink has a small residual check-to-unlink race.

The offline fixture diagnostic exited 0 and retained status UNPROVEN_FRAME_CANDIDATE_ONLY with mapping=null; all prior geometry controls remained unchanged.

| Artifact | SHA-256 |
| --- | --- |
| [Updated verifier](verify_inbound_frame.py) | 866387a63b12254469257fce730b31aebccc9fa678aeac91e26d0adec9569744 |
| [Ownership and source pin result](frame-diagnostic-ownership.json) | 52c15704c9adb65691489712cb1360f89877505ac3cc124e26fd1bf8b97623c9 |

LUNA low implemented and ran the change. SOL medium reviewed the final code/result and accepted the bounded ownership check, with the residual race above.

## Current Confirm source: uncovered uniform face slots refused (2026-10-09)

`uniform-used-face-coverage-source-fix.json` records a narrow product defect found
while tracing the old override seam. The existing distinct-Material guard already
refuses unproven correspondence, but a shortened uniform nonnull Material plan
could pass. Confirm then cleared uncovered used slots to None and persisted
USER_CONFIRMED. Actual import/Confirm on one author-owned copy reproduced this:
the Prefab array alone was shortened to its first reference, while FBX, metadata
and all other package entries stayed unchanged. Ten of twelve triangles then
lost their assigned Material. This copied input is separate from the old fixture.

Read-only Material planning now rejects uncovered used face slots before mutation.
The same actual operator input rejects with no slot/count or binding changes.
Actual Blender regression changed from one failure to 12 passing tests; fully
covered uniform references and an extra unused slot remain accepted. The user
gets an explicit unproven face/Material explanation. No map is inferred from
slot counts, names, triangle counts or the old numeric frame candidate.

This fix does not prove old override reconstruction or winding. The old frame
candidate remains unproven; current triangle staging already preserves ordered
triangles and original corner normals. [Unity's documented front-face rule](https://docs.unity3d.com/2022.3/Documentation/Manual/AnatomyofaMesh.html) alone does
not justify a particular importer reflection. No new runner, manifest schema,
generic parser, Unity launch or original Asset/meta modification was introduced.

## Latest bounded source winding diagnosis: independent UV correspondence (2026-10-09)

`uv-anchored-frame-and-winding.json` explains the previously observed reversal
for the pinned source Mesh. The existing frame probe reads normals, UV0 and
submesh indices through read-only MeshData in the existing dedicated Project.
`source-uv-normal-observation.json` is a public synthetic observation. Source
GUID/fileID, all 24 vertex values and submesh index arrays exactly match the
unchanged earlier Unity diagnostic. The current explicit-remap meta is different;
this join does not pretend the two metadata contexts are identical.

Correspondence is selected solely by unique unordered UV triangle triples and
unique within-triangle UV corners, before inspecting positions or normals.
All 12 signatures are unique, using exact dyadic UV values without quantization.
The already declared C = 0.01 * reflectX then matches every corresponding point
with maximum residual 6.33e-10. Its normalized inverse-transpose normal transform
matches with maximum residual 2.98e-11. All 12 corner orders are reversed and
none are direct; geometric face normals agree with imported corner normals
(minimum dot 0.99999975). Thus the reversal accompanies this measured negative
determinant conversion; reversal alone was not proof of inverted product normals.

The existing verifier now exposes `diagnose_pinned_uv_source_frame` for replay.
It reuses the pinned FBX parser, produces no production map and writes no files.
Wrong-axis, changed/duplicate UV and one-triangle order controls pass. Normal
Editor exited 0, all 211 existing Asset/settings/package files remained byte
identical, owned Editor/children and lock were absent, and the frame was released.
There was no Apply, reimport, Scene save, new runner or production schema change.

This is a fixture-bound source orientation diagnosis. Ambiguous/repeated UV
signatures reject, and C is not generalized to other assets/import policies.
Historical outputs and UNPROVEN reports remain intact. Old override face/Material
correspondence is still absent from ordinary input and remains unresolved; the
diagnostic does not introduce a guessed Material assignment or accept the old
confirmed override export or arbitrary edited normals/winding.
