# R2 material partition diagnostic plan — 2026-10-07

## Status and scope

Diagnostic design by GPT-6 Astra at medium reasoning, based on the fixed public ThreeSlotSource fixture and existing Unity 2022.3.22f1 observations. This plan changes no product policy, fixture, acceptance expectation or Finalizer behavior. The next experiment uses those observations offline; it does not require another Unity launch. Diagnostic code is to be authored by GPT-6 LUNA at low reasoning and reviewed by GPT-6.1 SOL at medium reasoning before execution.

## Authoritative product requirements

- [PRODUCT_SPEC.md:17](../PRODUCT_SPEC.md#L17) defines normal input as `.unitypackage` directly into Blender and Unity Editor/project as a development verification oracle, not an import-time user prerequisite.
- [PRODUCT_SPEC.md:457–458](../PRODUCT_SPEC.md#L457) explicitly excludes mandatory Unity Editor/MCP/VCC and prior Unity unpacking, FBX searches, GUID investigation or ordinary-case manual Material reassignment.
- [README.md:148–150](../README.md#L148) permits an optional exact-revision model identity witness, while limiting its existing proof to generated subasset IDs and native FBX identity.
- [README.md:152](../README.md#L152) rejects automatic Material association from names, ordering or candidate counts.
- [PRODUCT_SPEC.md:34](../PRODUCT_SPEC.md#L34) makes the edited Blender geometry and face assignment authoritative for export. This does not prove that inbound reconstruction faithfully matched the original Unity assignment.

Normal import must remain available without a user Unity Project. These provisions do not prohibit isolated Unity development verification or optional witness data. Absence of a production material-partition witness is not a reason to stop an offline diagnosis using existing observations.

## Existing boundary evidence

The source Unity Renderer uses Material2, Material1, Material0 with triangle counts 6, 4, 2. The confirmed Blender Mesh uses the same GUID/fileID sequence with counts 2, 4, 6. Raw input FBX connections are fixtureMaterial0, fixtureMaterial1, fixtureMaterial2, with counts 2, 4, 6. The source and exported FBXs have the same ordered triangle corners and polygon material indices `[2,2,2,2,2,2,1,1,1,1,0,0]`. Export transport labels preserve the already confirmed Blender assignment. Counts constrain the hypothesis but do not establish geometry correspondence.

The concrete assumption to test is [operators/renderer_binding.py:244](../operators/renderer_binding.py#L244): `plan[index]` is assigned to `mesh.material_slots[index]`. The witness material planner similarly copies source Renderer slot ordinal into `consumer_slot_index`, and the dependency resolver consumes it as a Blender slot. Existing confirmed-route winding evidence proves preservation of the confirmed Blender state through export; it does not prove inbound fidelity.

## Bound inputs

| Input | SHA-256 |
| --- | --- |
| Original public ThreeSlotSource package | `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c` |
| Original Input.fbx | `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5` |
| Original FBX meta | `ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d` |
| Confirmed-three-slot blend | `58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c` |
| Existing Unity diagnostic JSON | `af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2` |

The diagnostic JSON observes the original source asset inside the exported package `20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd`. Bind that source observation to the original fixture through exact source FBX/meta bytes, source Mesh identity and raw Prefab references; do not treat the two package hashes as interchangeable.

Select by identities, not names: source Mesh GUID `abcdefabcdefabcdefabcdefabcdefab`, local ID `3538053534738119282`; FBX Model UID `208084244`, Geometry UID `329684292`; Prefab GUID `7cbdcbe81fde386408bcfb379e62b6bb`, Renderer file ID `3728717051629469441`. Material local IDs are `2100000`; GUIDs are Material2 `eb805efb35118044db5e74adc652673a`, Material1 `0318f358e4c29034aa90cc8c50b58a93`, Material0 `64f92a1bd9b35a040bf9e2c6d200b34c`. Each Blender run has its own occurrence/root/native-realization IDs.

## Minimum offline experiment

1. Pin all input hashes and actual product module hashes. Read the original raw Prefab material references independently.
2. Extract raw FBX polygon corners, material-layer mapping/reference modes, connection-resolved Material UID, axis/unit settings and model/geometric transforms. Names remain diagnostic labels.
3. Read Unity source vertices, per-submesh triangle indices, exact Renderer material references and `source_mesh_to_prefab_root` from the preserved JSON.
4. Capture the saved confirmed Blender state. If no historical pre-confirm snapshot is proven, replay the existing import and Confirm once on a fresh in-memory fixture scene. Capture immediately before and after; label this a reproduction. Do not save or export that scene.
5. Record raw Blender vertices, polygon/loop-triangle corners, material indices, DATA identities, OBJECT overrides/effective identities, Mesh/root matrices and binding receipts.
6. Declare the Unity↔Blender coordinate conversion from existing import conventions and FBX metadata independently of material identity. Include units and model/geometric transforms. Record matrices, determinants and scales. Require complete unlabelled triangle-multiset correspondence before deriving any material map; never fit separate transforms per material or accept an unexplained reflection.
7. Match complete geometric partitions with multiplicity. Only then attach serialized exact Material GUID/fileID references and compare effective assignments before/after Confirm. Missing, coincident or ambiguous partitions remain unproven.
8. Compute cyclic-canonical orientation separately from unoriented membership. Cyclic corner rotations are equal, reversed order is separate. Report the declared global orientation conversion and any precision bound; rounded equality is not bitwise equality.
9. In comparator memory only, exchange one distinct triangle's Material label between two groups. Counts stay equal and semantic comparison must fail. Cyclic rotation must pass, reversal must be detected, and changing duplicate-triangle multiplicity must fail.

Output an exclusive new diagnostic JSON containing input bindings, coordinate proof, full unlabelled comparison, partition membership matrix, before/after exact references, winding and ambiguity results, and comparator controls. Preserve all previous results and input bytes.

## Product options to compare after the diagnosis

| Option | Benefit | Constraint |
| --- | --- | --- |
| Explicit manual Material↔face mapping | Records user-authored intent for identified actual partitions without mandatory Unity | Existing Confirm Renderer does not collect this mapping. A new default manual workflow would conflict with the ordinary-case requirement and needs separate design. User intent alone does not prove source fidelity. |
| Optional revision-bound geometry witness | Can certify source Unity submesh↔native FBX/Blender partition relation using exact observations | Existing identity witness lacks this proof. A production extension needs revision/import-policy binding, ambiguity handling and compatibility tests. Existing data is already usable as a diagnostic oracle. |
| Scoped unresolved refusal | Avoids unsupported reconstruction claims when evidence is missing or ambiguous | Refuse only the unproven material reconstruction/claim; do not invent a blanket import prohibition or silently change old V1 export compatibility. |

Recommendation: execute the bounded offline geometry diagnosis first. This plan does not select a production option. A single fixture does not establish handling of duplicate/unused/null slots, coincident geometry, altered import policy, arbitrary topology, skin deformation or broader Avatar semantics.
