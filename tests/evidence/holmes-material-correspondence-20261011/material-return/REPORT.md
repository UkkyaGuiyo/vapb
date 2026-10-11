# HOLMES-20261011-04 — environment blocked before Import

Instruction ID: HOLMES-20261011-04 / READY.
Instruction source: CHAT_FALLBACK_NOT_SAVED_TO_GITHUB; no GitHub issuing commit.
Project: VAPB; repository: UkkyaGuiyo/vapb.
Base branch: `feature/holmes-import-face-material-20261011`.
Base SHA: `096c6f18cbeff3dd189407578371172b2c270deb`.
Work branch: `feature/holmes-material-return-20261011`.
Prepared source/evidence result: [5632b1f67f42e8fb16e2909cce079a1708bf54a7](https://github.com/UkkyaGuiyo/vapb/commit/5632b1f67f42e8fb16e2909cce079a1708bf54a7).
Common AGENTS actual reread SHA256:
`9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`.

## Actual outcome

First failure: **ENVIRONMENT_BLOCKED**, Blender launch before standard Import.
The existing private runner stopped at `Mutex occupied`, before an app launch or
process marker. No .blend, edited package, FBX, manifest or runtime capture was
produced for this instruction. No product defect was reproduced or source repaired.
Prepared source is not executed product success.

| Phase | Actual outcome |
|---|---|
| Standard Import | BLOCKED before Blender launch |
| Before-Confirm save/exit/reopen | NOT_RUN |
| Standard Renderer Confirm | NOT_RUN |
| Independently identify p4 and change R0 to existing R2, retain p0 R0 | NOT_RUN |
| Final save/exit/reopen and final-face persistence | NOT_RUN |
| Standard Mesh/Skin static Export | NOT_RUN |
| Exported FBX/manifest/material identity transport | NOT_RUN |
| Unity normal Import and explicit Finalizer Apply | NOT_RUN |
| Actual final faces/submeshes including quad triangulation | NOT_RUN |

At 2026-10-11T10:52:27.3555581Z another authorized Unity task held the shared
resource; actual free RAM was 3.132781982421875 GiB against the existing 4 GiB
minimum. Parent scheduling gave that task priority and prohibited a new Unity
lease until release. At the subsequent 10:59 UTC read-only check, its Editor
remained active and shared mutex existed; free RAM was 3.59422302246094 GiB.
Pool slots being FREE does not authorize concurrent launch. This work owns no
Editor, Blender process, Unity lease or mutex. No other app was stopped or lock
removed. The VAPB verification Project has no Editor or UnityLockfile; no OnlyYou
files/menu/dummy were added. GUI/node_repl capability is unavailable in this
session; human-facing menu retention remains unperformed.

## Prepared path and limits

[blender_return.py](blender_return.py) uses existing self-authored OrderedSix,
standard Import and Confirm, ordinary native single-user Mesh copy, independent
fixture corner evidence for actual p4 selection, existing R2, then the standard
Mesh/Skin static export operator. Separate process runners retain the existing
resource contract. No fixture, product schema, binding/receipt injection or
relaxed guard was introduced. Historical -03 runtime/review was not repeated.

After reopening, the prepared export phase independently obtains actual polygon
UV/topology/material rows again and compares them to the saved final rows.
The prepared path does not yet prove exported transport or Unity final faces.
When reached, the existing independent corner/coverage diagnostic must compare
the edited final Blender truth against actual Unity submesh faces, accounting
for quad-to-triangle coverage. Material slot arrays alone cannot satisfy this.

Prepared source AST parse: PASS; native execution: NOT_RUN.
Prepared source SHA256:
`e78abcc8a3cf3dca0677eb71761dc377e84a6f4795cd28e2bfc514b74019a6d4`.
Installed official FBX importer SHA256:
`262127c8e6af3e748d696d81070366f39e449aa73e6bc1d9463092b5cbf86741`.
Blender -04 runtime version: NOT_RUN; previous -03 measured 5.2.1 LTS.
Unity -04 runtime version: NOT_RUN; installed Editor 2022.3.22f1.
Unchanged product `blender/fbx_receipt.py` SHA256:
`aa83b3716d14436f0e606694b3c9a88d8f015fb100a9e5406c20d35c2e8aefdc`.
Unchanged product `operators/renderer_binding.py` SHA256:
`11064a91b3ef3ac364772845918475d31a712ddb6d194ad2b7ba0d0b518dffa4`.

All 13 frozen original package/FBX/meta/Prefab/Material hashes match the existing
fixture evidence; see [blocked.json](blocked.json). No Unity Scene/settings or
private/purchased assets were changed or published. Only new public-safe prepared
source/evidence is saved. Atlas remained read-only per the scheduling instructions.

Independent reviewer **GPT-6.1 SOL / medium**: KEEP checkpoint, with Unity phase
label and reopened face evidence corrections applied. See [REVIEW.md](REVIEW.md).
Primary actual model/reasoning settings are unavailable; no configured value is
claimed as observed. Formal usage read at checkpoint: used 3%, remaining 97%; no
reset redeemed. Existing remaining-5% save/stop condition stays in force.

## Next minimum

After parent scheduling release, freshly verify shared mutex/processes/pool and
at least 4 GiB free RAM, then run the prepared Import stage once. Continue with
normal exit/reopen without reimport; stop/classify the first actual failure.
No Unity lease before the scheduling release. This report saves a blocked
checkpoint, not a completed material return or complete VAPB product.
