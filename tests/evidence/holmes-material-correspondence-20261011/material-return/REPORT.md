# HOLMES-20261011-04 — saved edited face Material returns to Unity

ID HOLMES-20261011-04 / READY; instruction source
CHAT_FALLBACK_NOT_SAVED_TO_GITHUB; **no GitHub issuing commit**.
Project VAPB; repository UkkyaGuiyo/vapb.
Base branch `feature/holmes-import-face-material-20261011`, SHA
`096c6f18cbeff3dd189407578371172b2c270deb`.
Work branch `feature/holmes-material-return-20261011`.
Actual runtime source/evidence result:
[d502b2a88dce01eeb9dfb1536b373e12dc63bcd4](https://github.com/UkkyaGuiyo/vapb/commit/d502b2a88dce01eeb9dfb1536b373e12dc63bcd4).
Common AGENTS actual reread SHA256:
`9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`.

## Actual result

**PASS for bounded static-route face/Material return.** Existing self-authored
OrderedSix only; no new fixture, product repair or historical -03 rerun.

| Phase | Actual result |
|---|---|
| Standard Import, native single-user Mesh, save | PASS |
| Normal exit and separate-process reopen without reimport | PASS |
| Receipt/binding retention and standard Renderer Confirm | PASS |
| Independently identify p4; R0 to existing R2; p0 retains R0 | PASS |
| Save/exit/reopen; actual UV/topology/Material rows | PASS |
| Standard VAPB UnityPackage Mesh/Skin static Export | PASS |
| Serialized FBX/manifest/consumer identity transport | PASS |
| Normal Unity ImportPackage and explicit existing Finalizer Apply | PASS |
| Actual Mesh submesh faces and Renderer Material GUID/fileID | PASS |
| Positions, oriented/culling fidelity, render, human GUI operation | NOT_RUN |
| Separate edited Variant creation | NOT_ESTABLISHED by this static route |

See [import.json](import.json), [confirm-edit.json](confirm-edit.json),
[export.json](export.json), [native.json](native.json),
[transport.json](transport.json), [judgment.json](judgment.json).
This is not complete VAPB delivery or a broader geometry/importer guarantee.

## Final-face correspondence

Final edited Blender state is authoritative. The diagnostic identifies actual
faces by existing exact fixture UV corners, never names or presumed face ordinal
equality. Reopened faces are independently obtained and compared again.

| Independently identified face | Final Material | Unity triangles / group |
|---|---|---|
| p0 triangle | R0 | 1 / 0 |
| p1 quad | R1 | 2 / 1 |
| p2 quad | R2 | 2 / 2 |
| p3 triangle | R3 | 1 / 3 |
| p4 triangle, edited | R2 | 1 / 2 |
| p5 quad | R1 | 2 / 1 |

Both serialized FBX and Unity contain nine triangles. Existing independent
corner/edge coverage proves each quad's two triangles cover its boundary with
one cancelling internal diagonal; missing/duplicate faces are rejected. Every
actual triangle's submesh Material GUID/fileID matches its final Blender face.
Four slot-array references alone are not the proof. Recorded UV winding is FBX
+1 and uniformly Unity -1; oriented/culling and rendered fidelity are unproven.

Actual returned Mesh GUID `d6f28bcc59f94dbeba9883a9c79a0e03`, signed fileID
`-7713446866133851500` (source `-7487798873075540560`). Renderer GUID
`983dd9d36c5824d488269d7d6d6f0434`, fileID `9090392177786753814`.
Serialized FBX realization ID equals manifest and one actual Unity marker.
Packaged first-party consumers exactly match current source. Standard static
consumer `VapbReferenceFinalizer.Apply` changes the imported owned Prefab copy;
no distinct Variant is claimed.

## Failure, recovery and preservation

First failure ENVIRONMENT_BLOCKED before Blender Import. Historical
[blocked.json](blocked.json) stays unchanged. Parent confirmed resource release
and explicitly instructed continuation. Fresh 11:03 UTC checks: real Editor /
Blender / mutex absent, all slots FREE, RAM 5.057 GiB. Every launch enforced the
existing shared-resource contract and 4 GiB minimum.

The Unity runner first safely refused preflight because comparison-only packaged
consumer files were missing; lease/mutex returned, no Editor launched. A later
launch request was automatically rejected for perceived conflict-guard removal.
Actual refusal guard was verified intact, exact original/backup/inventory SHA
checks and explicit own-consumer allowlist were added; safer launch approved.
Package assets entered through normal ImportPackage, not manual copying.
No product defect reproduced or product code changed; no repair RED/GREEN or
additional regression was needed.

Three separate Blender processes exited 0. Unity exited 0 at
11:10:04.181867 UTC; all 3,041 protected Assets/Packages/ProjectSettings files
restored exactly: changed 0 / unexpected 0, owned children and lock absent.
Lease returned 11:10:06.6273555 UTC; mutex released. All 13 original frozen
package/FBX/meta/Prefab/Material hashes match. Existing Scene/settings preserved.
No private/purchased assets, raw logs or personal paths published. Public native
capture reduces full importer policy to effective Mesh policy. Actual exits,
RAM and executed-source hashes: [run-summary.json](run-summary.json).

## Versions, hashes and review

Actual Blender **5.2.1 LTS**, Unity **2022.3.22f1**.
Official importer SHA:
`262127c8e6af3e748d696d81070366f39e449aa73e6bc1d9463092b5cbf86741`.
Output package SHA:
`0ccf9cd8d4f507a8589c02631d8865ddc456bd8e2627394ae9a8549843118dc9`.
Output FBX SHA:
`86511b3319fb83a9d18e2ee46740bb3037be8d8df8210b466a4b3c545b1f5087`.
Manifest SHA:
`b26d11116b63bef9e4e8c41d324eaa345ca6a6e14052be45640f024835358048`.
Unchanged product source: fbx_receipt.py
`aa83b3716d14436f0e606694b3c9a88d8f015fb100a9e5406c20d35c2e8aefdc`;
renderer_binding.py
`11064a91b3ef3ac364772845918475d31a712ddb6d194ad2b7ba0d0b518dffa4`.

Independent new runtime review **GPT-6.1 SOL / medium: KEEP**, recomputing actual
faces, serialized transport, hashes and preservation. See [REVIEW.md](REVIEW.md).
Primary actual model/reasoning unavailable; no configured value claimed as observed.
Formal remaining 97%; no reset. Atlas remained read-only per existing instruction.

Next minimum: report this completed bounded result for the next authorized product
decision. Render/position/culling and separate Variant are outside this proof;
no extra measurement is silently started. Output .blend/package remain local.
No main/dev merge, force, Release, ZIP rebuild or new foundation.
