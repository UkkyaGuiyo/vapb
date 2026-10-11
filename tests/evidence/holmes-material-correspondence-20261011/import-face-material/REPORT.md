# HOLMES-20261011-03 — bounded Import/Confirm face material proof

Instruction: **HOLMES-20261011-03 / READY**, approved 09:41 UTC chat-transferred
text. There is **no GitHub issuing commit** for -03. The old -02 instruction
commit is not its authority. Expired OnlyYou coordination is excluded.

Project: VAPB. Branch: `feature/holmes-import-face-material-20261011`.
Base: `b8e2d11e2618e77dcd77959988139b1ca8525a24`.
Code/evidence result: [`f6faf286e866e61b32a1d4c05f540ded5d0cc1a7`](https://github.com/UkkyaGuiyo/vapb/commit/f6faf286e866e61b32a1d4c05f540ded5d0cc1a7).
Common AGENTS reread SHA256:
`9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`.

## Result

| Requirement | Actual result |
|---|---|
| Normal VAPB Import | PASS |
| Standard Renderer Confirm | PASS, bounded static receiver |
| Actual per-face Material GUID/signed fileID | PASS |
| Existing guard / unsupported or stale input refusal | PASS, unchanged state |
| Exception restoration | PASS: slots/backing/link/material, face indices, receipt, binding |
| Original Object/Mesh and source asset preservation | PASS |
| Unity return / Finalizer | NOT_RUN |
| Rendering | NOT_RUN |
| Save/reopen runtime | NOT_RUN |

This is a product Import/Confirm connection, not complete VAPB delivery.
No Unity measurement was repeated. Existing -02 native/judgment/supplement are
immutable supporting observations for the restricted pair-first candidate.

## Actual importer proof

Installed official Blender **5.2.1 LTS**, importer SHA256
`262127c8e6af3e748d696d81070366f39e449aa73e6bc1d9463092b5cbf86741`.
The official `blen_read_material` creates and returns a datablock from its FBX
Material element; the temporary hook records that actual return and UID.
The official Model-connection assignment appends those same datablocks into actual
Mesh slots. Slots are identified by captured native handles at import completion,
not by names or an assumed Unity/FBX slot permutation.

The official `blen_read_geom_layer_material` writes `ByPolygon/IndexToDirect`
values into the real Mesh material attribute. The hook captures the actual
write and polygon-loop incidence. Import completion must preserve that entire
state after `Mesh.validate` and `validate_material_indices`; changed/clamped
state gets no proof. This establishes UID→actual slot→actual face directly at
the runtime write boundary, without joining source and Blender face numbers.
Pointers are not persisted. No unique UV, UV layer or material name participates
in receipt capture, prediction or application.

ThreeSlotSource demonstrated creator/layer continuity only; its skinned/shared
receiver was not admitted into the static product scope. OrderedSix standard
Import then produced the six receipt pairs:
`A/T, B/Q, A/Q, B/T, A/T, B/Q` (A UID 26834720; B UID 505943850).
The approved `(UID,effective topology)` first-appearance candidate produces
`0,1,2,3,0,1`. Actual standard Confirm applies these into four OBJECT slots and
matches each serialized external Material GUID/fileID. **PAIR_FIRST is supported
in this fixture; no universal importer guarantee is claimed.** Previous -02
PAIR_RUN and UID_FIRST falsifications remain unchanged.

## Minimal implementation and safety

Existing `blender/fbx_receipt.py` import hooks now retain a bounded material-write
receipt. Application is connected only at `operators/renderer_binding.py`
standard Confirm. The normal root/occurrence/owner/realization checks remain.
The direct static source requires one Geometry/Model, no deformers/modifiers/
shape keys, nonshared local Mesh, all connected native slots used, supported
material layer, triangles or exact axis-planar quads, KeepQuads enabled, and the
captured importer policy/revisions. The receiver uses complete signed references.

Confirm rechecks source FBX/meta hashes, actual Prefab revision and its exact
MeshFilter/Renderer references, scoped unique providers, current provider file
hash, actual provider meta GUID and actual unique serialized class21/fileID,
Mesh state and native slot identity. The ordered-pair count must exactly match
the receiver references. No fallback chooses names, positions or array ordinals.
Distinct guard remains active for inputs without this proof. The source template
is preserved; positive test uses ordinary Blender Make Single User before Confirm.

Eleven unchanged refusal controls: shared Mesh, wrong Material reference, null,
wrong Mesh fileID, unproven source, unused slot, user face edit, same-name provider
identity conflict, provider revision mismatch, provider meta GUID change and
missing provider meta. An injected exception after slot/face mutation restores
the entire captured state. Package/FBX/meta/Prefab/Material asset bytes remain
unchanged. No purchased assets, GUI work, original Unity Scene/settings changes,
new framework, Export restriction, main/dev merge, force or Release operation.

## Verification and independent review

Native RED→GREEN: absent material receipt; standard distinct-material refusal;
provider-meta GUID change incorrectly accepted, then safely refused after repair.
Final native validation exits 0, owns no remaining children and releases mutex.
Focused existing receipt/binding/provenance suite: **30 run, 1 skipped, PASS**.
Initial unit launcher namespace/temp-directory environment errors were corrected
in the private test launcher; product source was not changed for those errors.

Independent separate actor **GPT-6.1 SOL / medium** reviewed the complete change
and final evidence: **KEEP**, no remaining blocking issue, UV correspondence
not consumed. One actual provider-meta gap was fixed and reviewed in the same
review. See [REVIEW.md](REVIEW.md), [confirm.json](confirm.json),
[probe-summary.json](probe-summary.json), [run-summary.json](run-summary.json).
Primary actual runtime model/reasoning retrieval is unavailable; no setting is
fabricated. No completed old review was repeated. Atlas remained read-only.

Minimum remaining blocker: broader geometry/importer policies and persistent
save/reopen behavior need separate evidence before admission. Unity return/
Finalizer and rendered appearance are unverified for this new connection.
Final edited Blender state remains the Export authority; this import proof is
not made mandatory for final Export.
