# Independent four-case coordinate holdout: paired observation

Project: VAPB. Branch: `feature/r2-material-slot-reorder`. Source base: `ab90e934fbf08cccba4e3b65cb4319f5cd40f11b`. The coordinator assigned one Unity turn for the exact four previously preregistered FBXs. Unity 2022.3.22f1 launched once in an owned disposable Project, using the saved probe and normal exit guard, with no MCP package. All four FBX and both deployed C# hashes matched before and after capture. No equation, tolerance, fixture or importer setting was tuned.

## Fixed gates

| Case | Local maximum | World matrix maximum | World point maximum | Candidate |
|---|---:|---:|---:|---|
| H0 | 0 | 5.960464477539063e-8 | 1.8708001769951466e-7 | PASS |
| H1 | 0 | 3.178651297730539e-8 | 8.391639760851888e-8 | PASS |
| H2 | 1.7881393449270533e-8 | 7.450580596923828e-9 | 3.4562837036844485e-8 | PASS |
| H3 | 1.7881393449270533e-8 | 3.427267075695184e-8 | 6.66844579555459e-8 | PASS |

The unchanged `1e-4` threshold applies to exactly local, world matrix and world point maxima. The matrix-chain-point quantity remains diagnostic only. The comparison reused the original frozen scalar oracle and each case's authored unit ratio, with row-major matrices and exact eighteen U tags. It ran once against the capture; the original seven-case comparison is unchanged.

The separate Unity authored-world hypothesis passes 4/4, maximum error `3.4809113846900885e-7`. Unity H1 minus H0 maximum is `2.4473462190144346e-7`; H2 minus 0.1 H0 maximum is `1.7881393449270533e-8`. Both pass. The earlier Blender authored-world and within-tool gates also passed. Each Unity case has one transform, one renderer, eighteen vertices, no unmatched faces and synthetic fixture-material face membership matching. Effective importer settings match all eight frozen values.

## Provenance and terminal state

- Prepared input SHA-256: `0848806638b57e43f5ff1f245a9e42935ca0184e5df42f7e39f662b175f86af3`.
- Unity capture SHA-256: `9512bfef157b125de501b6c717590d85c40bd3c05832344a85f1998176c81872`.
- Blender capture SHA-256: `1c1941357bed53058d30e140b6ff79741844c035dfebafb17ea662292329b117`.
- Original fixture manifest SHA-256: `b203347a088ea4925231111e707704505473911b9b7ae18262b82cc6d8dd0401`.
- Frozen preregistration SHA-256: `a75edd729c68799091b5bbb904480fa7be3830f6a8071e9cf3edfaf7e4b17036`.

`compare_fixed_capture.py` checks artifact/source/deployed-input hashes, exact case sets, matrix shape, tag population and paired input identities before using the frozen oracle. `paired-comparison.json` records its source hash and all maxima. Run it with the repository, preserved Blender run and preserved Unity run as positional arguments; output uses exclusive creation. Original FBXs, Project and raw logs remain local and untouched.

The probe's successful capture selects its source-defined `EditorApplication.Exit(0)` path; native shutdown log records and owned process disappearance were observed. The launcher did not retain the OS process exit code, so no independently measured exit-code claim is made. Postflight confirmed zero Editors and the pre-existing Hub serve still present. No forced stop, other-Project manipulation, authentication/license change or MCP safety bypass occurred. Licensing client validation/update warnings were logged; the capture completed, but the log is not claimed clean.

## Scope and next minimum

The candidate `C(x,y,z)=(-x,z,-y)` / `D=diag(-s,s,s,1)` now passes independent runtime observation on these four single-root synthetic holdouts under the frozen versions/settings. This is not a general importer proof or full product round-trip. Parent-child import, winding/normal transport, external-package Material GUID/fileID to face association and Unitypackage closure remain unproven. Fixture name joins do not supply the external material bridge.

Next minimum is the existing separate material identity gate using an author-owned source and output with equal-count disjoint face partitions, without name/count/index fallback or a fixed swap. Do not schedule another Unity launch implicitly. Requested primary model/reasoning: GPT-6.1 Sol / Medium; actual runtime selection was unobservable. Formal account weekly quota was 30% remaining at preflight and at postflight; context capacity was not used as quota. Knowledge candidates remain PENDING_REVIEW for the designated aggregate, with no formal Entry adoption or old-Atlas push.
