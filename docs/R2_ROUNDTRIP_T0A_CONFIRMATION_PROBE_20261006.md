# R2 strict import and Renderer confirmation probe

**Repository:** `https://github.com/UkkyaGuiyo/vapb`

**Branch:** `feature/r2-material-slot-reorder`

**Starting checkout:** `ab0aa4267706031bd3e2005eed765eb0b0baf380`

**Plan:** [`2026-10-06-r2-roundtrip-discriminating-verification.md`](superpowers/plans/2026-10-06-r2-roundtrip-discriminating-verification.md)

## Scope

This is bounded evidence for the public synthetic `ThreeSlotSource.unitypackage` input (`SHA-256 d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`) in Blender 5.2.1 LTS. It covers the immediate import state and the existing explicit Renderer confirmation operator. It does not cover export, package closure, textures, or Unity acceptance. No product source was changed.

The package's only Prefab renderer has three ordered Material references, each with file ID `2100000`:

1. `eb805efb35118044db5e74adc652673a`
2. `0318f358e4c29034aa90cc8c50b58a93`
3. `64f92a1bd9b35a040bf9e2c6d200b34c`

An independent raw native-FBX import selects exactly one three-slot Mesh with an Armature modifier and triangle counts `[2, 4, 6]`. Its FBX GUID is `abcdefabcdefabcdefabcdefabcdefab`, and the payload SHA-256 is `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5`. In the VAPB import, the selected native skin Mesh also has a valid persistent receipt for those FBX bytes.

## T0-A: import without manual confirmation

The production import completed with `RECONSTRUCT`, `prefab_choice=AUTO`, Materials on, Textures on, and no `model_witness_path`. The strict no-edit assertion failed before any export:

- Projection status is `EXACT`, with all three expected ordered Material GUID/fileID/package references.
- All three canonical Material datablocks exist with the expected GUID, file ID, and source package SHA.
- The exact native skin Mesh has a valid persistent receipt for the expected FBX GUID and SHA. Its face triangle counts match the independent native-FBX baseline `[2, 4, 6]`.
- Its three immediate slots are `DATA` linked and contain Materials without Unity GUID/fileID/package identity.
- The projected Prefab Renderer owner maps to an `EMPTY` scene object; the native Mesh has no Renderer occurrence/binding. The source FBX `asset.meta` has zero `externalObjects` rows. The scene dependency registry property is absent.

This localizes the bounded no-witness case after provider construction but before Prefab reference realization on the native Mesh. It is consistent with the add-on's explicit confirmation boundary; it does not establish a regression, a general product defect, or that an automatic semantic join is safe.

Final diagnostic attempt `t0a-diagnostic-attempt09` returned the intended strict assertion failure with Blender exit code 1 (`--python-exit-code 1`). Result JSON SHA-256: `FC36CD43D38A6F4C390090E778D13E62B313B167F517C096EE95CC8A245DBB27`.

## Existing explicit confirmation route

A fresh process imported the same package and invoked `vapb.confirm_renderer_binding` exactly once for the projected occurrence and receipt-valid native Mesh. No Material slot, identity property, or witness was manually injected.

- Read-only binding preflight: `VALID`.
- Operator: `FINISHED`.
- Resulting ordered slot GUID/fileID/package identities exactly match the three Prefab references and the input package SHA.
- Resulting slots are `OBJECT` linked and the Mesh's in-memory custom property carries `USER_CONFIRMED` binding evidence. No `.blend` save/reopen persistence check was run.
- Triangle counts remain `[2, 4, 6]`.

Attempt `t0a-confirm-binding-attempt10` exited 0. Result JSON SHA-256: `751EBA5E102F95EDA0C22175E4D9837E272C7F7E1C9F1A4899205B4004567EA5`.

This is a PASS only for the existing explicit-confirmation route on this synthetic fixture. It does not change the strict no-edit T0-A result and does not justify continuing to T0-B as though the untouched import passed.

## Reproducible probes

- [`blender_roundtrip_fbx_slot_oracle.py`](../tests/blender_roundtrip_fbx_slot_oracle.py) measures the fixture's native imported FBX slot/face baseline without calling the add-on.
- [`blender_strict_unchanged_import_test.py`](../tests/blender_strict_unchanged_import_test.py) captures and asserts the no-witness immediate import state.
- [`blender_confirm_renderer_binding_probe.py`](../tests/blender_confirm_renderer_binding_probe.py) exercises the existing explicit confirmation operator and checks exact resulting identities.
- [`blender_confirm_renderer_binding_persistence_test.py`](../tests/blender_confirm_renderer_binding_persistence_test.py) prepares a confirmed scene in one process and validates its saved binding in a fresh process.

## Follow-up: save and fresh-process reopen

A later disposable run closed the persistence gap left by attempt10. It used two serial Blender 5.2.1 LTS background processes with factory startup and `--python-exit-code 1`: prepare imported the fixed package, independently parsed its raw Prefab Material refs, confirmed the exact receipt-valid native Mesh, and saved a new `.blend`; verify started in a separate process, opened that file, revalidated the saved binding and receipts, and compared the prepared identifiers with the reopened identifiers. Both processes exited 0 and reported PASS.

- Source package SHA-256 remained `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`.
- Prepared `.blend` SHA-256: `58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c`.
- Prepare report SHA-256: `06fdaa11fb0e8d3c993aa716e2c9e726e21c680321c506b921ba6ff18ba8ed4c`; fresh-process verify report SHA-256: `59e6589beaab6d5aef783f7941e1471541998b47b0a78fb86df5f461a8aa4006`.
- The same root context, Renderer occurrence, native realization, FBX GUID/SHA/model/geometry IDs, and Mesh receipt ID survived save/reopen. `validate_existing_binding` returned the saved binding unchanged; evidence remained `USER_CONFIRMED`; the native Object receipt validated and its Mesh-datablock receipt matched.
- All three ordered Material GUID/fileID/package identities remained present with `OBJECT` links after reopen. Face-slot triangle counts remained `[2, 4, 6]`.

This establishes persistence for the existing explicit confirmation route on this one synthetic fixture. It does not change the strict no-edit T0-A failure and is not a pass for automatic binding. No export or T0-B package closure was attempted; Unity was not started. The run reports and logs are retained outside the repository in the disposable `run-material-reopen-test-02` evidence directory; the `.blend` itself is not committed.

The original diagnostic run root was `r2-roundtrip-strict-run-20261006-01`; the follow-up persistence run used `run-material-reopen-test-02`. The Unity Editor was not started. No output `.unitypackage` was generated, so output closure and fresh Unity import remain untested.
