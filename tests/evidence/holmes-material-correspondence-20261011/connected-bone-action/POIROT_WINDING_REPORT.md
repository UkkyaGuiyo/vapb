# POIROT-20261014-01 — directed face correspondence

Current outcome, phase2 new reconstruction: **W1_ORIENTATION_PRESERVED — SUPPORTED_IN_SCOPE**; W2 **NOT_OBSERVED_IN_SCOPE**. Independent result review KEEP/must-fix0. This concerns the two self-authored native faces and captured Mesh/Transform state only; no rendered, animated/skinned, GUI or VRC acceptance. Product code unchanged.

Historical phase1 outcome: **UNDETERMINED**. Saved-observation inspection completed offline. Neither W1 nor W2 was established from the old original Unity native source -> completed Unity Variant records. Phase1 performed no application launch. Those missing-array/sorted-order records remain unmodified and are not retrospectively promoted to PASS.

## Authority and baseline

- Supplemental owner chat instruction relayed by parent; state SUPPLEMENTAL_READY. Current chat is the authority. A GitHub publication commit for this new instruction is unconfirmed. Private owner/conversation identifiers are not published.
- Parent's latest read of the fixed instruction handoff still concerned POIROT-20261013-01/WAITING_FOR_RESULT. The local instruction-branch ref is unavailable. Neither is used as the development base or as a new execution instruction.
- Project VAPB; canonical origin `https://github.com/UkkyaGuiyo/vapb.git`; branch `feature/connected-bone-action-20261012`; actual fixed start `fed7c630d535477be0c6196c02e32b5e7cbbac74`, clean. Exact tracked-ID search and bounded local artifact-name check found no prior result for this new ID.
- Global AGENTS actual SHA256 `9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`; repo AGENTS, PRODUCT_SPEC final-state/preservation/acceptance clauses and latest Holmes REPORT/PLAN reread. Shared Failure Atlas consulted as read-only reference, particularly separate acceptance gates and fixture-oracle scope.
- Main CASE24 GUI acceptance remains active with its existing operation/resource prerequisites. This supplement does not cancel it. The parent reports another project's ongoing Unity work; no shared frame is assumed available.
- Previous evidence remains [POIROT_REPORT.md](POIROT_REPORT.md): execution988caa2, correctione61735c. Its A/B Material result and preservation findings are not repeated or promoted into winding proof.

## Existing self-authored subject and fixed bytes

The same two-face A/A -> slot1/B subject is reused; no new model, Material, fixture, link mode or input is created. Previous OBJECT/OBJECT links and shared Mesh users2 remain historical observations.

| Existing input | SHA256 |
| --- | --- |
| Normal source package | `1a6443bf2f2990b4eda9367543d806003895eedc325c209d99da437fe0dff9c2` |
| Original FBX owned copy | `263411f59dd4a02d721af7bd362d19b19262e4ea3a40cce04e32daebfab827dd` |
| Saved EditedAB Scene | `933567bec54cc89265e8b25e64d9770532a12a957b526916fe2d2ce2f5a7efd5` |
| Completed output package | `3daadb5ad379998eaa50a18954b21f4c682f2ddae5bb1bc0ab9bcad637c741ba` |
| Source native result | `b3f29b1874b8402ef1ed602f464f4b995616a282989e6a2031d79a8ece4645a9` |
| Variant face result | `abf701ae9d2ee60db4931834228d61841883498c9669f1c99c76a2bafeffe54b` |
| Separate native detail result | `505b1ab73379eb55ce6b763533ef9776e7e546c5597b832c996347f6dfd97c1a` |

Source model GUID `704df84fcfe318c48908f90130e496e6` and source Prefab GUID `b1ef5076bc94668488e5d59e6c373d8c` are declared by the retained manifest. Actual source native Mesh/Renderer signed identities were not serialized in the source observation. Do not manufacture them from FBX UID, names or vertex counts.

Separate detail run records final Mesh `dd427cbcafa0154657e14b3bbbf50a83/-249969726160171967` and Renderer `fa0ac7d873ac28d418ec9b5b8b09e4bd/7753468105853849844`. That Renderer belongs to a separately regenerated Variant; it is not asserted to be the first face-run Renderer identity. The first face result lacks those actual identities and cannot be cross-joined to the detail Renderer by assumption.

## Order inventory and comparison

F0 is `7af28f094004b1cfbd4949dcd87e820ae3e852f217075418558ec1d669c2ce26`; F1 is `9f67a0215846516ae25887bfc4286151d3120c8fa91900572a37c13aabc8ac0f`. These existing IDs use unordered position/UV fingerprints for face membership only. Ordered Blender loop rows were retained separately.

| Face | Saved Blender corner order: position / UV | Before -> reopened cyclic order | Original Unity indices/order | Completed Unity indices/order | Previous final submesh / Material |
| --- | --- | --- | --- | --- | --- |
| F0 | `(0,0,0)/(0,0)` -> `(1,0,0)/(1,0)` -> `(0,1,0)/(0,1)` | EXACT | NOT_CAPTURED | LOST_BY_SORTING | 0 / `3f77663a081c14944b0f13bb3cc139a6/2100000` |
| F1 | `(2,0,0)/(0,0)` -> `(3,0,0)/(1,0)` -> `(2,1,0)/(0,1)` | EXACT | NOT_CAPTURED | LOST_BY_SORTING | 1 / `5221bf0c1c21d4446b22699654a18425/2100000` |

Each Blender row has three distinct position/UV corners and a nonzero geometric cross product `(0,0,1)` in its stored local frame. This is a bounded Blender saved-order check, not original Unity -> final Unity acceptance.

The original Unity source observer compares native vertices/indices/UV/weights/bindposes in memory, then serializes an equality bool and counts. It does not serialize those arrays, normals, Transform matrices or actual Mesh/Renderer identities. Source observer hash: `b50ff4ddf8af57fd874a2e5a73558f26d0af24dfb720b864bf9f01e2d1567404`.

The Variant observer calls `GetIndices(slot,true)` but immediately converts to position/UV rows and applies `rows.Sort(...)` before serialization. Only the sorted rows survive; no triangle index array or original order survives. Face observer hash: `4d25db0c3af31dd2c11a4961439ad34724a68ff4867c2b4d7b298ba14f4ffac5`.

An offline information-loss check on each existing captured corner row confirms that reversing its order preserves the sorted multiset but is not a cyclic permutation. Cyclic rotations are equivalent; reversal is distinct. This demonstrates why the retained result cannot decide W1/W2. The reversed permutation is a logical alternative, **not an observed native reversal or a new test asset**. No tolerance or threshold is introduced or changed. Original FBX order is not treated as Unity order.

## Coordinates, normals and first divergence

Previous Variant corner-set proof used declared reflectX plus centimetres -> metres in model-local coordinates and recorded useFileScale/fileScale0.01/globalScale1. A reflectX map has algebraic determinant sign negative; that declaration does not provide the actual source and Variant local-to-world matrices or their determinant signs. Those native matrices were not captured. World-frame correspondence, actual mirror compensation and geometric-normal versus stored-normal alignment are **UNDETERMINED / NOT_RUN**.

No first product mismatch is established. The first documented information loss is in observation/serialization: original native arrays omitted; final corner order discarded by sorting. It must not be called a product winding defect. Normals are absent from both native records. Material identity remains the previous separate result.

## Gates and preservation

| Stage | Result |
| --- | --- |
| New-ID reconciliation and offline field/hash inspection | PASS |
| Saved Blender F0/F1 order and nondegeneracy | PASS_IN_SCOPE |
| Original Unity -> completed Variant directed comparison, W1 / W2 | UNDETERMINED |
| Native normal alignment / world Transform determinant | NOT_RUN / UNDETERMINED |
| Counterexample to native orientation preservation | NOT_ESTABLISHED |
| Second-phase Unity observation | NOT_RUN; parent resource assignment required |
| Product correction, new export/input, Action/Weight/Shape checks, GUI/render/VRC | NOT_RUN / OUT_OF_SCOPE |

Thirteen existing subject/evidence/observer files were hashed before and after offline inspection and are unchanged. No old result or original is overwritten. The private diagnostic initially treated the saved reopen list as a dictionary and failed before output; only that reader access was corrected. No application rerun followed. Previous native cleanup records retain3041protected files unchanged/no unexpected files; that is historical preservation, not a new Project inventory. This phase touches no Unity Project, lease, mutex, Editor or foreign process. Purchased corpus, raw private logs and secrets are not published.

## Necessary next observation and result handoff

Request one parent-ordered observation in the same existing owned Gimmick01 Project using the fixed source/output packages above. Read original source Renderer/Mesh and final Variant Renderer/Mesh actual GUID/signed fileIDs, per-submesh topology and ordered `GetIndices(...,true)`, vertex position/UV and available normals, local-to-world/parent matrices, native importer unit settings and actual Material identities. Retain array order and actual identities in the same capture; join F0/F1 by their existing unique corners, then compare cyclic order in a declared common frame and independently evaluate determinant signs/normals. Unknown/degenerate/ambiguous joins remain UNDETERMINED. First differing measured stage/frame must be recorded if a reversal is found.

The previously observed Variant was removed by normal Project restoration and no retained native Variant/array snapshot was found in the bounded saved folders. If reconstructing it requires import and one unchanged existing Finalizer Apply, that prerequisite is a Project mutation and must be explicitly included in the parent's allocation/procedure; it is not described as a pure read of a surviving Variant. Do not rerun the prior Material/Weight/Shape/Action acceptance or reApply merely to obtain orientation. No new Project, foreign Editor stop, lock removal or forced resource acquisition. Coordinate with the parent's active Unity work and CASE24 GUI priority before launch.

Evidence goes to fresh Holmes; even a product counterexample authorizes no implementation in this supplement. CASE24 remains the main task. No instruction-publication SHA is invented. Primary actual model/reasoning unavailable; inference requested SOL/xhigh, effective runtime unavailable. Latest formal remaining94%, no reset used.

Fixed phase1 result commit: [0a15e9f1358806becfdb5bd2990e0793ceb7cabd](https://github.com/UkkyaGuiyo/vapb/commit/0a15e9f1358806becfdb5bd2990e0793ceb7cabd), normal push and exact remote readback of this report and PLAN confirmed before inference. This later section records the returned inference; its own save SHA is reported with exact readback rather than inventing a self-referential file hash.

Fresh independent Holmes completed: **UNDETERMINED for W1 and W2**, supporting the bounded phase1 conclusion. It independently inspected the observers/results and five assigned retained artifact folders, verified all13input hashes, and confirmed that sorting destroys final order while the source observation omits native arrays. It found no retained native Variant/ordered-array snapshot in those folders; this is not a global absence claim. Saved Blender order, logical permutation control, separate detail identities and Material results remain separate from native orientation. Requested/configured SOL/xhigh, effective runtime unavailable; inherited workspace-write/auto_review with a behavioral read-only role. No inference edits, Git writes or application launches.

Watson checks those grounds against the existing capture code and results. Next remains the single parent-allocated same-Project ordered observation specified above, including any necessary import/one unchanged Apply reconstruction explicitly; no reApply acceptance repeat, product fix or CASE24 cancellation. Phase2 remains NOT_RUN pending allocation/procedure. A missing observation prevents W1/W2 acceptance, not all project work.

## Phase2 — newly approved reconstruction and ordered capture

Owner approved the parent's concrete Import/one existing Apply/read/restore proposal at2026-10-14 02:44:41UTC. Parent assigned this next shared frame after the other project reported Unity unused/no planned use. This clears the phase1 resource/procedure gate only; product correction, new fixture and repeated acceptance remain out of scope.

Actual start baseline remained branch `feature/connected-bone-action-20261012` / `c94c78911bcbca7db94b44bbf619f16d842696b8`, canonical remote and clean. Same fixed Output package3daadb5 and its bundled original assets/helpers are normally imported into the existing owned Gimmick01 Project. The established lease/mutex/backup/restore guard is reused. Fresh preflight found only recognized Hub serve, no Editor/Blender, all slots FREE/unowned, no Project lock or shared batch opt-in, actual freeRAM5.2244682GiB. Owner VAPB-POIROT-winding-20261014; Unity2022.3.22f1 PID6968/start02:50:10.8715203UTC.

Observer preserves native index order and captures source model, source Prefab, edited model and newly reconstructed Variant in one run. Existing Finalizer Apply calls=**1**; no reApply, new export, Blender launch, or additional Action/Weight/Shape acceptance. Original asset/meta plus manifest hashes before/after Apply match. No GUI operation or scene-authoring step.

Sanitized first-party capture/judgment: [POIROT_WINDING_NATIVE.json](POIROT_WINDING_NATIVE.json). Private raw result SHA256 `ced777ef0c513432215fbc3822ed098a110e831ce60907fd5e96c0ba117690a1`; private observer SHA256 `304b01f7dae9ad77da28e9a2d895554441bd08562b88ff6bfa378788d26601d3`. Raw observers/logs/absolute paths stay local.

### Actual identities and independent joins

| New capture role | Renderer GUID / signed fileID | Mesh GUID / signed fileID |
| --- | --- | --- |
| Source model | `704df84fcfe318c48908f90130e496e6/-7985938101188212478` | `704df84fcfe318c48908f90130e496e6/-7643034884740281656` |
| Source Prefab | `b1ef5076bc94668488e5d59e6c373d8c/6330520556445165755` | Same original Mesh above |
| Edited model | `dd427cbcafa0154657e14b3bbbf50a83/3356982228806475034` | `dd427cbcafa0154657e14b3bbbf50a83/-249969726160171967` |
| New final Variant | `b946cd15b799f344cae14d2f1d85e633/355806476397743439` | Same edited Mesh above |

Actual final corresponding Renderer is the captured source Prefab Renderer; source Prefab corresponding Renderer is the captured source model Renderer. These are **this reconstruction's identities**, not the old face-run or old detail-run Variant identity.

The previously frozen unique position/UV corner sets identify F0/F1 independently of slot, Material or face-number prediction. Actual source and final index arrays supply order only after that join. Float32 position/UV identities match exactly; numerical signed zero is treated as geometric zero as in the existing equality convention, no epsilon or fitted conversion.

| Face | Source actual indices | Final actual indices | Ordered corner permutation relative to the existing Blender triplet | Source -> final cycle | Final Material |
| --- | --- | --- | --- | --- | --- |
| F0 | `[0,2,1]` | `[0,2,1]` | Native first/third/second in both captures | SAME_CYCLE; reverse=false | A `3f77663a081c14944b0f13bb3cc139a6/2100000` |
| F1 | `[3,5,4]` | `[3,5,4]` | Native first/third/second in both captures | SAME_CYCLE; reverse=false | B `5221bf0c1c21d4446b22699654a18425/2100000` |

Three distinct corners and nonzero geometric cross per triangle; duplicate/ambiguous/degenerate joins are absent. Source F1 retains A while final F1 has intentionally authored B. Material preservation is a separate exact GUID/fileID observation; it does not decide orientation. FBX/Blender index order is not assumed to be Unity order.

### Transform and normal findings

Source Prefab and final Variant local matrices, parent-world matrices and complete local-to-world matrices match exactly. Therefore their native-local corner comparison is also valid under the same invertible world map. Recorded importer useFileScale=true/fileScale0.01/globalScale1 agree. Independent exact rational determinant of the captured world matrix is `1099511460003862025/1099511627776`, positive; Unity's float determinant999999.875 is independently positive. No mirror-sign difference or unknown frame is required to obtain this result.

Available local native corner normals give positive dot with the ordered geometric cross at all three corners of each face, on both source and final. With the same positive-determinant matrix, inverse-transpose normal transformation preserves that sign relationship in world space. This is stored native rest-Mesh normal/cross consistency, not rendered shading or evaluated Skin deformation.

Diagnostic distinction: the edited model asset's own import-root matrix is not bitwise identical to the source/final root matrix (for example its y/z rotation terms differ); its determinant sign is also positive. Its native vertices/UV/normals/index orders agree with the final Mesh, while the final Variant retains the original Prefab's exact Transform. The raw model-root difference is retained in the JSON, not hidden behind a tolerance or called a winding defect. No full Blender->FBX->raw-model world-transform equivalence claim.

### Restoration, independent review and current result

Unity normal exit0 at02:51:05.7684182UTC; all3041preexisting Project files exact, unexpected0, owned children and Project lock absent. Lease release02:51:07.8763339UTC and mutex returned. Fresh02:59:04UTC host recheck found only recognized Hub serve, no Editor/Blender, all slots FREE/unowned and mutex immediately acquired/released. All13historical input/evidence hashes independently rechecked unchanged. This does not replace the phase1/previous-run preservation records.

Independent SOL/medium result/observer review completed **before publication**, as the latest owner instruction requires; KEEP/must-fix0. It recomputed both ordered joins, determinant, corner-normal signs, actual ancestry, oneApply and preservation, and reviewed public safety. Effective model/reasoning unavailable; behavioral read-only review, no writes/runtime launches. This is an independent result review, not a repeated production code review or a claim that role rules technically prevent writes. Primary actual settings unavailable.

Current stage verdicts: reconstructed native ordered comparison **PASS_IN_SCOPE/W1 SUPPORTED_IN_SCOPE**, W2 **NOT_OBSERVED_IN_SCOPE**, Material **EXACT_SEPARATE**, captured Transform/determinant/normal findings **PASS_IN_SCOPE**, restoration/resource return **PASS**. Product implementation, reApply, animated/skinned deformation, GUI, rendering and VRC **NOT_RUN**. Old phase1 winding remains **UNDETERMINED**. No counterexample or product correction follows from this evidence.

POIROT-20261014-01 directed-face question is complete for this bounded reconstruction. Remaining main next minimum is CASE24 actual GUI acceptance when the supported operation surface/parent ordering is available; this supplement neither cancels it nor creates a global stop. Normal purpose-specific save and exact remote readback follow the independent review; final save SHA is reported to parent.
