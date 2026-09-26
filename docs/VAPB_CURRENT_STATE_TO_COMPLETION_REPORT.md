# Current product campaign checkpoint — 2026-09-26

This is continuing work. The current original request in PRODUCT_SPEC.md is authoritative; this checkpoint and older history cannot narrow or expand it. V1 is an intermediate milestone. Continue the next safe action without waiting at stage boundaries.

## Updated resource instruction — 2026-09-26

The user explicitly changed the next reset trigger: **use an earned reset when the remaining eligible usage window reaches approximately 10%**. Two authorized resets have now been used; one remains. The second reset was consumed through the official Codex app-server at 10% remaining, after checkpoint `5118980496c58114fe0a1bbdb1841b62f7039d15` was pushed with a clean worktree. The official usage read subsequently confirmed 100% remaining and one available reset. No credits were purchased. Keep saving verified checkpoints regularly so the next reset does not endanger unsaved work. The original final-window reserve of at least 30% still applies after the available resets are exhausted; the new instruction changes when remaining reset tickets are used.

## Current state and authority

### Priority amendment — Core Round-trip First (2026-09-26)

The latest user instruction changes priority, not the full product scope. Close the current skinned-Mesh roundtrip at a safe atomic checkpoint, recording code, tests, PROVEN/UNKNOWN and the exact next action in GitHub. Then prioritize multiple real private VRC packages, including the user-authorized representative avatar and different avatar/clothing/Variant/nested/cross-package cases selected from the existing private catalog.

Core acceptance requires actual package import, readable independent occurrence hierarchy, real Mesh/Armature/Material/Texture/shape edits, save/reopen, package export, fresh Unity import and necessary reference/state restoration for usable Unity/VRC results across multiple real inputs. Synthetic-only, appearance-only, FBX-only, package-generation-only or static-only success is not Core completion.

Use an ongoing loop: small synthetic proof -> multiple private import/regression cases -> isolate real failure -> generalize to a public-safe synthetic regression -> fix -> recheck private cases. Private originals remain read-only and outside Git. Do not publish commercial assets or private identity tables. Review executable third-party project content before Unity import. Existing catalog information should guide bounded selection rather than repeated whole-corpus scans.

Semantic Cleanup, Weight Transfer and Semantic Bone Merge remain mandatory final features. Defer their expansion/polish when it would delay Core roundtrip. Preserve useful current work; no abrupt discard or rollback. Save meaningful checkpoints at the current work boundary, first real imports, major real-data defects, roundtrip milestones and before resets/session transitions.

Exact next action after the current skin checkpoint: select heterogeneous representative packages from the existing private catalog and perform bounded Blender Import smoke, comparing occurrence/Mesh/Armature/Material structure before further feature expansion. Private validation is a continuous Core development layer, not a final-only gate.

- Branch: `feature/multi-package-identity`.
- Starting code HEAD: `c7dcb1b38dd63f1e5af366d538c818878f2ddd9f`; worktree was clean.
- Live remote branch query confirmed the same HEAD on 2026-09-26. Plain Git lacked usable credentials; a command-scoped `gh auth git-credential` helper used the existing authenticated GitHub CLI successfully. No credential or global config changes.
- Existing semantic contract/synthetic adapter, provenance/FBX receipt, export graph/planner/staging/writer are committed. Historical statements below about dirty/uncommitted modules are superseded.
- Historical 238 Python PASS and Blender integration PASS are retained as historical evidence, not a new campaign run. The semantic-occurrence/native-skin edge is not established by separate existence assertions.
- Current delivery status: **IN PROGRESS; requested specification not complete**. No new distribution artifact yet.
- Requirements have two independent axes: development status (未着手 / 実装中 / 実装済み未検証 / 検証済み / 阻害要因あり) and input coverage (Supported / Partial / Unsupported / Unknown / Ambiguous). Entries below are campaign acceptance status, not claims that all legacy code is absent.

## Witness-backed direct skin restoration checkpoint — 2026-09-26

The current implementation adds a bounded direct-Prefab skin path alongside the existing model-instance and explicitly confirmed topology-edit paths. Serialized Renderer candidates are carried to Unity; the source FBX witness and public persistent IDs must resolve exactly one. Source/target bone slots, root and hierarchy are checked by authoritative identities. Original bindposes are compared with edited bindposes; bind-time matrices are not replaced by current bone transforms. Recognized source FBX unit conventions (1 or 100, with Blender scene unit scale 1) are preserved using the native exporter. Other conventions remain explicitly unsupported.

**PROVEN:** repository-parent Python **335 tests PASS**, zero failures/errors; compileall and diff checks PASS. Independent read-only scope review PASS. Blender 5.2.1 direct synthetic import/edit/rename/save/reopen/export, two corrupted-receipt rejection controls, and register/unregister PASS, exit 0. Fresh Unity 2022.3.22f1 direct restoration PASS: 24 vertices, two bones, real vertex delta approximately 0.002, original source/bones/root/materials preserved, linked Prefab Variant and unchanged second application. An incorrect serialized Renderer candidate and an extra Variant component are both rejected without changing the saved Variant; test inputs are restored. The existing two-skin model-instance regression also passes, including preservation of its sibling Renderer and second-application/negative-control checks.

**Real-data milestone PROVEN:** the representative avatar's selected native skin was edited, renamed, saved/reopened and exported through the actual operator, then restored in a newly created official VPM Avatar project using Unity 2022.3.22f1 and VRChat SDK 3.10.5. The fresh Unity probe passes all acceptance fields: 3,139 vertices, 176 bones, intended vertex delta 0.00014675874, exact edited Mesh assignment, linked Prefab Variant, unchanged original assets, retained target bones/root/materials, and 25 preserved sibling Renderers. Second application is byte-idempotent. Wrong Renderer identity and an added Variant component are rejected without modifying the Variant; negative-control inputs are restored. Compilation has zero C# errors. Console cleanliness is evaluated separately from the two expected rejection messages. This establishes one real selected-skin roundtrip, not complete Avatar/VRC usability or multiple-private-case Core completion.

**Additional real-data finding:** case D's authoritative source Renderer has 160 bone slots, while its imported native rig has 227 receipt-backed bones. Unedited staging actually produces a Unity skin with 227 slots, one Renderer and 474 vertices. Consequently, filtering only a validation count would conceal a real output difference. Diagnose source skin membership and native exporter behavior before changing this boundary. Private assets, source IDs and identity tables remain outside Git.

**Next action:** reproduce and repair case D's source-skin bone-membership difference with a public synthetic fixture, then recheck that different real package. Multiple-private-case Core roundtrip, broader editing and final Unity/VRC usability remain incomplete.

## Installed ZIP export support checkpoint — 2026-09-26

The distribution builder omitted the three first-party Unity C# helpers consumed by package export. Source-checkout tests therefore did not establish that an installed add-on could export. The builder now includes exactly those three runtime support files; tests, tools and private data remain excluded.

**PROVEN:** the new packaging regression failed before the change and passes afterward. A candidate ZIP containing the current committed runtime was extracted into an isolated temporary installation. Blender 5.2.1 imported the add-on from that installation, imported the synthetic two-skin package, edited one skin, renamed it, saved/reopened, rejected two corrupted receipt controls, and exported through the actual UnityPackage operator: PASS, exit 0. Register/unregister PASS. Repository-parent Python: **328 tests PASS**, zero failures/errors; compileall and diff checks PASS. Independent read-only scope review PASS; no additional changes requested.

This is an intermediate installed-runtime export check, not final product delivery or private Core roundtrip completion. The representative-avatar Oracle remains in its first import; exact target bone/rest and edited source-layout comparisons are still UNKNOWN. The separate D source witness also passes raw/meta restoration and per-ID parity, with one exact native receipt join; no full D package or VRC usability claim follows from it.

**Next action:** finish the representative-avatar Oracle import or establish its concrete startup blocker, then verify the selected skin's exact target bone identities/rest matrices and edited layout before implementing deferred direct-skin restoration.

## Real-avatar skin frame diagnosis — 2026-09-26

The representative-avatar Oracle now completes. Its former long wait was a probe lifecycle failure: the revised continuation helper on disk had not been compiled into the headless Editor. A controlled restart of only the owned isolated batch process preserved its Library and pending phase, avoiding a repeat package import.

**PROVEN:** one exact target Renderer/source Mesh relation; all 176 serialized bone IDs and root correspondence match public Unity API identities, with no null/duplicate bones or missing scripts. Source and Prefab relative bone matrices are exactly equal. A 0.006568499 difference between bindposes and current bone matrices already exists in the untouched source, so requiring those two representations to be identical incorrectly rejects this source. Bind-time and current transforms must not be conflated.

The actual edited export retains 3,139 Unity vertices, triangle indices, one submesh, zero blendshapes and 176 bindposes. Independent source, edited and unedited-control witnesses uniquely join all 176 bone slots through FBX UID and realization receipts. All 3,315 per-vertex weights (at most two influences) and UV/color channels agree in the unedited control. These are identity and staging observations, not a completed Unity restoration.

The roughly 1.105 local-coordinate difference is explained by FBX unit representation: original UnitScaleFactor is 100, staged export is 1. Public renderer matrices convert the unedited control into the original Mesh frame with maximum vertex error 2.85e-7; the frame is a positive uniform scale of approximately 100. Edit/control matrices and bindposes are identical; only two imported split vertices carry the intended change, approximately 0.000146759. Normal and tangent conversion differences remain measured separately (maximum normalized-vector distances approximately 6.21e-5 and 8.09e-4); do not claim exact shading parity.

**Public-safe reproduction:** `tests/blender_skin_package_test.py --prepare-fbx --source-units-in-fbx` prepares a synthetic source using the native exporter's FBX_SCALE_ALL option. After the existing `VapbSkinRoundtripProbe.Prepare`, `tests/blender_skin_frame_test.py` imports that package and creates untouched/edited staged FBXs. `VapbSkinFrameProbe.Run` then reproduces the local-frame change while checking normalized unchanged geometry and the real edit. Blender 5.2.1 and Unity 2022.3.22f1 PASS, exit 0: 24 vertices, two bones, approximately 100 scale conversion, unchanged-control error 3.77e-7 and edited delta 0.002000034. The probe requires the frame difference to be present and reports failure with a nonzero process exit.

The smaller counterfactual now passes: exporting the original untouched selection with native FBX_SCALE_ALL preserves its source UnitScaleFactor of 100. Unity local vertex positions and indices match the source exactly; weights also match. Renderer matrix error is 2.38e-7, aligned bindpose error 0.00031636, and normal/tangent component differences approximately 6.11e-5/4.18e-5. This avoids introducing a separate frame-normalization Mesh artifact. Independent scope review requested an explicit approximately-100 factor assertion in the synthetic regression; adopted. compileall/diff checks PASS. The Python baseline remains the last verified 328 PASS; these focused Blender/Unity regression files do not change that test population.

**Next action:** implement the bounded witness-backed direct-skin Variant path and preserve recognized source FBX unit conventions during staging, then run the synthetic and real-avatar package restoration. No production correction is claimed complete at this checkpoint. Multiple-private-case Core roundtrip and final Unity/VRC usability remain incomplete.

## Requirements and acceptance tracking

All detailed constraints and modes remain binding in PRODUCT_SPEC.md, sections 0–22. Each row groups those clauses; grouped rows cannot be marked complete with an omitted sub-clause.

| ID / spec sections | Requirement / user operation | Existing or intended implementation boundary | Acceptance / required evidence | Development | Input coverage / result / remaining work |
|---|---|---|---|---|---|
| IN-01 / 4 | GUI import one/multiple packages, choose Composition | operators/import_unitypackage.py, package_reader | No Unity dependency; supported user paths work from installed ZIP | 実装中 | Partial; legacy paths exist; final product flow unverified |
| IN-02 / 4 | Prefab/Variant/nested/inherited occurrences | effective_prefab, semantic_contract | Enumerate actual model children without overrides or artificial cross-product | 実装中 | Partial; Stage 1A gap; production adapter pending |
| IN-03 / 4 | Cross-package providers, collisions, bounded discovery | package_identity, asset_database, sibling_discovery | Exact provider evidence; ambiguous choice UI; missing/cycle/corrupt input diagnostics | 実装中 | Partial; campaign multi-package matrix pending |
| ID-01 / 5 | Package/revision/source/occurrence/realization/export identities | provenance_model, identity, semantic_contract | Scope retained, signed IDs, no name/order join; insufficient evidence stays unresolved | 実装中 | Partial; conversion boundaries pending |
| ID-02 / 5,6 | RAW preservation and persistent source storage | source_store, importer, Scene package registry | Save/reopen and temporary-directory loss do not erase required source | 検証済み | Supported local immutable original archive; static-package export consumes verified source cache; cross-PC relocation UI pending |
| BL-01 / 6 | Separate editable instances with safe sharing | importer, hierarchy_builder, fbx_receipt | Independent transform/material and explicit shared/individual edit scope | 実装中 | Partial; repeated source and shared-data runtime matrix pending |
| BL-02 / 6 | Renderer occurrence -> semantic Object -> skin/Armature/slots | occurrence_projection, renderer_binding, material_builder | Authoritative persisted edge survives rename/save/reopen; ambiguity rejected | 実装中 | Partial: direct serialized Prefab + USER_CONFIRMED native skin/armature/material link PASS; nested realization and automatic binary-model mapping pending |
| BL-03 / 6 | Mesh/bone/weight/UV/normal/shape/animation/image/material/hierarchy edits | native Blender + edit/export adapters | Rename/duplicate/delete/join/split/merge tracked with actual edits | 未着手 | Partial native editing; complete export continuity unverified |
| ST-01 / 7 | Shader identity/properties/keywords/queue/texture preservation | material_parser/model, export | Approximate preview cannot overwrite Unity source; provider reported | 実装中 | Partial; complete roundtrip pending |
| ST-02 / 7 | Prefab source/override and generic serialized state preservation | parser, source snapshot, Finalizer | Capture/reference restore/behavior results separated; unknown state retained | 未着手 | Unknown; restoration pending |
| ST-03 / 7 | Avatar Descriptor/view/lipsync/eyes/playable layers | snapshot and Finalizer | Edits rebind exact renderer/bone/shape targets, report missing/ambiguous | 未着手 | Unknown |
| ST-04 / 7 | Expressions/parameters/menus/controller/clips/masks/bindings | graph, snapshot and Finalizer | Reachable assets included; changed target references restored | 未着手 | Unknown |
| ST-05 / 7 | PhysBone/collider/contact/constraint state | physbone_parser, graph, Finalizer | Preserved source and edited-reference restoration; no preview substitution | 実装中 | Partial capture; full requested restore pending |
| ST-06 / 7 | MA/NDMF/other MonoBehaviour/ScriptableObject | source preservation and dependency declarations | Concrete preserved state/dependency/unsupported reasons; no arbitrary execution | 未着手 | Unknown |
| EX-01 / 8 | Edit delta and reachability from final Composition | export/semantic_graph, asset_plan | All specified operations distinguished, unknown references protected | 実装中 | Partial planning; Blender extraction not closed |
| EX-02 / 8 | GUID continuity/remap/collision handling | asset_plan, manifest | Preserve logical identity; new/duplicate/split/merge refs explicit | 実装中 | Partial; production allocation/remap pending |
| EX-03 / 8 | Export actual self-contained unitypackage | staging, package_writer, export operator | Atomic success, scene/source untouched, declared external deps, fresh import | 実装中 | Partial: direct-static and existing-bone skin GUI package export/fresh Unity restore PASS; general skin/nested/multi-package remaining |
| EX-04 / 8 | Idempotent Unity Finalizer and MRUS | unity_editor/Editor | Public API post-import identity; exact mesh/material/skin/Prefab/VRC rebind | 実装中 | Partial: direct static and existing-bone skin restoration/idempotence PASS; general Prefab/VRC MRUS remaining |
| CL-01 / 9 | Export Cleanup of unused Bone/Material | semantic_cleanup + FBX export staging | Exclude only proven unused; exported skin/references valid; scene unchanged | 実装中 | Partial: optional native FBX copy cleanup, parsed bone/material reduction and source unchanged PASS; full UnityPackage cleanup and Unity/VRC closure pending |
| CL-02 / 9 | Edit Cleanup preview/apply | Blender operator/UI | Scope/reasons/unknown visible, Undo/recovery, shared users protected | 実装中 | Partial: selected native Mesh/Armature, Japanese reasons, unused slots/leaf bones, Undo/rollback PASS; unresolved imported state protected |
| WT-01 / 10 | Explicit Weight Transfer source/armature/target/preview/apply | operators/weight_transfer, ui/weight_transfer_panel, blender/weight_transfer | Different topology; REPLACE/MERGE/FILL_MISSING with declared rules | 検証済み | Supported synthetic original-mesh surface, ALL/SELECTED range; private quality and installed ZIP flow pending |
| WT-02 / 10 | Transfer protections and quality feedback | transfer core | B-only/locked weights preserved, grounded distance indicators, deformation/Undo | 実装中 | Partial: distance/locks/shared data, user-declared rig-local X=0 crossing protection and selection, actual Undo/rollback and posed deformation PASS; private quality and installed ZIP flow pending |
| BM-01 / 11 | Explicit Semantic Bone Merge mapping/classification | Blender operator/UI + remap core | EQUIVALENT/B_ONLY/AMBIGUOUS; provenance or confirmed mapping | 実装中 | Partial: explicit per-bone confirmation, A Bone selector and persistent UUID/source identity remap; unresolved mappings protected |
| BM-02 / 11 | Rest/skin/reference-preserving transplant and remap | bone transform, reference graph, Finalizer | Roll/rest/world transform, all listed refs, collisions/sharing; verified deletion | 実装中 | Partial: supported native B-only chain rest/pose, Mesh and bone-parent rebind, evaluated deformation/Undo/rollback PASS; B retained; Unity/VRC/animation/special rig references protected pending restoration |
| UI-01 / 12 | Japanese GUI for all operations | ui, operators | No console/GUID entry in normal flow; targets/progress/outcomes explained | 実装中 | Partial legacy GUI; new editing/export controls pending |
| UI-02 / 12 | Recovery and independent operation selection | operators, docs | Undo/retry/reopen, no unselected destructive operation chains | 未着手 | Unknown |
| QA-01 / 13–15 | Python/Blender/Unity integrated synthetic matrix | tests, tools, public API Oracle | Identity/rename/reopen/multi-instance/sharing/ambiguity and actual deformation | 実装中 | Current Python/Blender/static Unity roundtrip PASS; full product matrix pending |
| QA-02 / 14,15 | Representative private regression | external corpus/catalog | Read-only originals, bounded safe copies; publish only synthetic findings | 実装中 | Partial: four real Import/save-reopen smokes; Material bug reproduced synthetically and fixed; Unity structural equivalence and real roundtrip remain UNKNOWN |
| PK-01 / 1,21 | Build/install/use final addon ZIP | tools/build_distribution_zip.py | Exact commit/hash; clean Blender GUI install and all major user operations | 実装中 | Legacy builder exists; final artifact unbuilt |
| GH-01 / 17,18,21 | GitHub reproducible checkpoints/handoff | this document, PRODUCT_SPEC, tests | All needed helpers tracked; fresh checkout; remote SHA verified; no private data | 実装中 | Remote access restored; checkpoint pending |

## Multiple skins in one model: causal regression — 2026-09-26

The private model population exposed a missing discrimination step: matching only the ordered Prefab instance edges cannot choose among several Renderers inside the same FBX. A public synthetic source with two skin Mesh Objects in one model reproduced `OCCURRENCE_AMBIGUOUS` after successful Blender import/edit/save-reopen/export. This is a production selection defect, separate from private B's missing external script dependency.

The finalizer now first completes the full source/no-op/witness/restored identity check. It derives the selected source Renderer and Mesh public IDs from the exact FBX Model UID, verifies membership in the original per-ID snapshot, then selects by both the ordered instance edges and the leaf Renderer ID. It does not use names or list order to assign identity.

Fresh Unity 2022.3.22f1 validation after the fix: PASS, exit 0; one selected skin changed, one sibling Renderer preserved, 24 edited vertices/two bones, original assets/materials/root/bones preserved, idempotent second application and unrelated-Component negative control PASS. The package carries the tested current helper source. compileall/diff checks PASS. Independent read-only scope review PASS. The existing Python count remains 327; this follow-up changes C# selection and Blender/Unity fixture setup only.

Private B's SDK-qualified Oracle public-API diagnosis confirms three missing MonoBehaviours on each of its two loaded Prefabs. Three serialized references point to one script absent from Assets, embedded VRChat packages and PackageCache; the other sixteen script references resolve. Its publisher/package is not identified from bounded local evidence. Do not remove those components or install a guessed dependency.

Representative private A has 459 native skin Mesh Objects across fourteen contexts, without model-instance edge metadata. Of 170 direct SkinnedRenderer records, 151 have exact serialized skin/material data and distinct per-context Mesh references. An isolated source witness passes for one selected record: 26 source Renderers/skins/Meshes and 204 Transforms, with full no-op/witness/restored parity and original raw/meta restoration. The selected serialized Mesh GUID/localID maps to exactly one source Renderer, one witnessed FBX Model/Geometry pair and one of 26 native candidates in that root. Both source and declared skin arrays have 176 bone slots with the root at the same index. Individual target bone Transform identities and rest-pose correspondence still require public-API verification; matching counts alone is not that proof. Neither A nor B is yet a completed real roundtrip.

The uniquely joined private A skin has now been edited in a separate working copy: 1,794 vertices, 176 bone receipts, no Shape Keys on this selected Mesh. A minimal vertex change, rename, save/reopen, receipt persistence and unchanged hashes of all other Mesh geometry PASS. Native staged FBX export also passes; this is not yet UnityPackage export or Unity restoration. The original saved import and corpus package are retained. The full SDK-qualified A Oracle is performing its initial asset/shader import before bone/rest and re-export layout validation.

Another concrete private B boundary is recorded: the task carries 117 rig-bone receipts while each source skin uses 90 bone slots. The current finalizer requires all declared mappings to participate in the selected skin/root and will not silently omit the extra receipts. Supporting that subset requires an exact selected-source-skin mapping derived after the witness, not a name/order guess. The missing external script dependency currently stops B earlier.

**Next action:** verify the representative-avatar direct skin's exact public bone identities and rest matrices in an isolated SDK-qualified Oracle before implementing its deferred restoration path, while keeping B's unknown external dependency explicitly unresolved.

## Model-instance skin export checkpoint — 2026-09-26

The model-instance export operator now preserves the original package and emits an edited FBX, two source witnesses, and one deferred Unity restoration task. Object/data receipts and the selected root/ordered instance edges must agree. Unity checks source/no-op/witness equivalence and exact public identities before creating a new Prefab Variant. Only the selected skin Mesh/bone binding is overridden; source assets, materials and other components are retained. Failed new-Variant verification rolls back the new asset; an occupied Variant with unrelated changes is rejected without overwriting it.

**PROVEN:** synthetic model -> Variant import, real Blender vertex edit, rename, save/reopen, GUI package export, fresh Unity 2022.3.22f1 import/finalization and idempotent second application PASS. The 24-vertex/two-bone result preserves materials, source assets and bone/root relations. A deliberate extra Component on the generated Variant is rejected unchanged; the probe restores its own negative-control bytes. Unity measured the intended vertex change as 0.0000200001523 after unit conversion. The probe initially used an excessive absolute threshold; it now reports both measured change and a scale-aware threshold (0.0000001 for this case).

The edited private B working copy also exports through the actual operator with save/reopen and both receipt-corruption controls passing. A separate official VPM Avatar Oracle uses Unity 2022.3.22f1, VRChat Base/Avatars 3.10.5 and VPM resolver 0.1.29. Package import completed, but finalization correctly rejected `PREFAB_UNAVAILABLE_OR_MISSING_SCRIPT`. Its required external script dependencies remain under diagnosis. This is **not** a completed private roundtrip.

Repository-parent Python suite: 327 tests, exit 0; compileall PASS. Existing direct skin regression also passes Blender export and fresh Unity restoration: 54 edited vertices, weight changes, original bone/material/state preservation, expected deformation with zero measured error, idempotence and invalid-mapping rejection. An initial regression invocation lacked its required SourceInfo.json fixture; supplying the existing matching fixture resolved that invocation error. Independent read-only scope review found and resolved post-save rollback and unrelated-override acceptance gaps; the second scoped review passed. Source witnesses are first-party helpers factored from the existing verified synthetic probe.

**UNKNOWN / LIMITED:** general topology or shape-layout changes, skeleton edits, edited Material restoration, cross-package model skin restoration, repeated exports to an already occupied generated identity, full VRC usability, and multiple-real-case roundtrip acceptance remain incomplete. Current model path is a bounded geometry/weight edit path and does not narrow PRODUCT_SPEC.md. No private assets or identity tables are included in Git.

**Exact next action:** identify the unresolved public script dependencies in private B's isolated VRC Oracle, then re-run its real edited-skin restoration with legitimate dependencies present; inspect the representative avatar case in parallel for the next heterogeneous real roundtrip.

## Exact occurrence and first private edit checkpoint — 2026-09-26

The public Unity API occurrence gate passes. At each Renderer source level, the persistent GUID and signed ID of GetPrefabInstanceHandle match the containing Prefab's class1001 document, and its source GUID matches the next public source object. Ordered edges plus the leaf Renderer identity distinguish instances without names or order.

- Synthetic Base/Variant/repeated model/RepeatedVariant: 4 Prefabs, 6 Renderers, 9 matched edge visits; repeated instances distinct, unresolved/ambiguous counts zero. Missing-edge and wrong-source controls reject matches.
- Private B: 2 Prefabs, 62 Renderers (46 Skin), 93 matched edge visits; all occurrences unique. The repeated_distinct flag is only evaluated by PrepareSynthetic, not generic Run.
- Saved Blender receipts, per-object source SHA, Model UID and ordered serialized edges join all 46 native Skin Objects to the exact Unity occurrences. Transform/Material override fidelity and VRC restoration remain unproven.
- Private C rerun after the model fix: Import/save-reopen PASS, source unchanged; 23 Mesh Objects / 2 Mesh datablocks / 0 Armatures / 0 Skin modifiers / 2 projected Renderer records. Counts include templates and do not prove Unity equivalence.

Actual private edit: in a separate B working copy, selected a receipt-qualified 4,160-vertex Skin Mesh, made its Mesh data single-user, renamed the Object and moved vertex 0 in local X by 0.0005 of maximum mesh extent. Save/reopen PASS; other Mesh/shape-coordinate hashes unchanged; selected occurrence/creation metadata retained. Selection by mesh size is a test choice, never identity evidence. Original imported .blend and source assets remain intact. Edited .blend and private selection details remain outside Git. **Real edited UnityPackage export and fresh Unity restoration have not run.**

Independent scope_guard contract review of the new test probe: PASS with bounded findings adopted. PrepareSynthetic now checks existing Prefab .meta and input JSON before writing; exception handlers explicitly set failure. Occupied preparation exits 1 with SYNTHETIC_PATH_OCCUPIED and input unchanged. Final synthetic/private Run exits 0. Parser scope is signed handle plus source GUID, not every source-reference field or arbitrary YAML.

Reproduction: put tests/unity_model_occurrence_probe/Editor/VapbModelOccurrenceProbe.cs under a disposable project's Assets/Editor. PrepareSynthetic requires the existing synthetic model fixture's Base/Variant/Input assets and refuses occupied outputs. Run reads ModelOccurrenceInput.json with a prefabs array at project root. Private detailed output stays outside Git. Production mapper code is unchanged.

Exact next action: extend existing package export/finalizer with a bounded deferred model-Skin task. Preserve source RAW; create a new edited Prefab Variant with the selected Renderer Mesh override. Resolve ModelUID and ordered edges in Unity, check bone/rest/shape compatibility and inherited state before saving. Prove repeated/Variant controls, then use the edited real B copy in an SDK-qualified fresh Oracle. The structure-only Oracle has missing VRC components, so it cannot establish VRC usability. Full Core and full product remain incomplete.

## Real-source FBX witness checkpoint — 2026-09-26

**PROVEN, test-only:** a working copy of the model used by private case B was re-encoded using installed Blender FBX APIs, with a decimal source Model UID property on each Model. Original bytes remain untouched. Reparsing verifies unchanged FBX semantics except the documented encoder header fields and added witness property. No third-party implementation or private fixture was added to Git.

Unity 2022.3.22f1 compared source, noop, witness and restored imports using documented public APIs. The synthetic case passes (5 Transforms, 1 Mesh, 1 skin, 2 bone references); real B passes (142 Transforms, 23 Meshes, 23 SkinnedMeshRenderers, 2,070 bone references, 141 unique marker callbacks). Both exit 0 with compiler error count 0. Existing per-ID Transform, Mesh geometry/topology/UV/normal/tangent/color/shape/skin values and Material **slot identities** match. This does not check every generated Material shader property or texture value.

Readability was enabled on each disposable imported model for full geometry capture. Noop/witness/restored comparisons therefore use that explicit comparison setting; supplied original meta and original raw FBX are restored byte-for-byte afterward. Separately, real B's Renderer ID set matches the prior Oracle observation under the original importer setting. This is not a general proof that all importer setting changes are harmless.

The real mapping's 141 Model UIDs were explicitly compared with all source FBX Model UIDs: exact set match. The generic Unity probe only guarantees imported marker/Renderer coverage; unsupported importer configurations may drop other source nodes and must not inherit this real-case set-equality claim. Blender creation receipts from the saved real case join **46 native skin occurrences across two scoped model edges to 23 source Renderer IDs**, without names or ordering. Raw FBX SHA and source GUID agree. Nested Prefab edge-ID resolution, effective override fidelity and saving/restoring those occurrences are not proven by this join.

Negative control: replacing the synthetic noop FBX with a different synthetic model returns `NOOP_DRIFT`, exit 1, no mapping output, and restored original raw/meta. An earlier setup invocation used a wrong input path and did not run the probe; it is not counted as negative-control evidence. The corrected invocation produced the stated fail-closed result.

Reproduce external source encoding with Blender `--factory-startup --background --python-exit-code 1 --python tests/blender_fbx_source_witness.py -- <external-folder>` containing Source.fbx. It refuses existing Noop/Witness outputs and repository-local evidence. Copy the existing `tests/unity_bone_witness_probe` first-party scripts into a disposable Unity project (Editor script under Assets/Editor), place Source/Noop/Witness.fbx plus optional original Source.fbx.meta at project root, and run `VapbBoneWitnessProbe.Run` in batchmode. Detailed mapping and private runtime evidence stay outside Git. Material dependencies must be present for meaningful referenced-slot observations.

Independent scope review of the witness files used the other agent's read-only scope_guard context because dedicated reviewer sessions were unavailable; PASS with the Model-UID coverage and Material-content limitations above explicitly adopted. Production mapper code was not added. Current public Python suite remains **323 PASS**; compileall PASS.

**Exact next action:** implement the smallest supported deferred model-instance export/restore path using source FBX receipts, serialized instance edges and public Unity API witness mapping, first proving the occurrence edge on the synthetic nested/Variant fixture, then exercising an actual private Mesh edit and fresh Unity restoration. Keep source assets and VRC state intact; refuse ambiguous identity. Full real Core roundtrip remains incomplete.

## Explicit cross-package Material confirmation checkpoint — 2026-09-26

The repaired split-package group probe exposed an actual confirmation blocker: authored Material references retain the Prefab package as their source context, while the real Material provider belongs to another package. Confirmation previously required that authored package to own the Material. A missing native slot before explicit confirmation is expected, not itself an import regression.

The minimal correction resolves exact Material GUID plus signed local fileID among scoped providers, prefers the authored package when available, then accepts a unique cross-package provider. Missing/wrong-ID/ambiguous candidates are rejected before mutation. It does not infer a Renderer-to-Mesh edge, replace authored provenance or introduce automatic native binding. Actual provider metadata remains on the selected Material datablock and survives .blend save/reopen.

Verification: real Blender group import/explicit confirmation PASS, including wrong-fileID and ambiguous-provider rejection without mutation, local preference, deliberate single-user Mesh copy, unchanged source template, Material/Texture assignments and provider persistence after reopen. Focused Python binding **11 PASS**, full repository-parent Python **323 PASS**. The earlier group-probe failure recorded at 121cca3 is now resolved for this explicit-confirmation path. Cross-package UnityPackage export is still unsupported by the existing exporter and is not claimed here.

Independent read-only scope review: PASS. The dedicated reviewer launch and old reviewer reuse were unavailable because the agent thread limit was reached; an existing independent agent performed the scope_guard contract on the other agent's changes, with no self-review or extra edits.

## Model-backed real Import checkpoint — 2026-09-26

**PROVEN:** dependency extraction now uses the existing selected-candidate source closure. Model-backed Prefab/Variant members are retained even without directly serialized Renderer documents. Each serialized model instance edge receives independent native Objects, with source receipts retained; shared source templates are hidden only after all copies. Material override references do not create extra direct copies. A genuine direct Mesh reference to the same model is still retained. No Unity Renderer identity is inferred from names, list order or unique object counts.

Four fully synthetic Blender cases pass: repeated model edges, nested model edges, two AUTO members sharing a model, and direct plus instanced use of the same model. An unrelated FBX stays excluded; source templates are hidden and occurrence copies remain visible in viewport/render. Correct repository-parent Python suite: **323 PASS / 0 FAIL / 0 ERROR**; compileall PASS. Existing integration and synthetic skin-package probes PASS. The final four-case model probe was rerun after removing an unjustified identity inference and exits 0. Scope review completed in two rounds: source hiding order was corrected; final review PASS.

Private case B was imported and saved/reopened again. It now has **62 visible Mesh Objects, two members each with 31 Mesh / 23 Skin**, plus 27 hidden source Mesh templates. The per-member populations match the Unity public-API observation. This does not establish exact Renderer correspondence, Transform/override fidelity, Material equivalence or VRC behavior. Private inputs and detailed identity evidence remain outside Git.

**KNOWN FAIL:** the old split-package group probe also fails on immutable pre-change HEAD 92724b8, because it assumes native Mesh and semantic occurrence are one object. Its synthetic GameObject component list and role selection are now repaired without weakening its Material/Texture assertions. It reaches a further failure: the selected native Mesh has no Material slot. That cross-package binding path remains unresolved. Unique native/serialized counts are not accepted as identity evidence, and no production identity guess was retained to make the probe pass.

**UNKNOWN:** generated Unity Renderer/local IDs for binary model children, deep instance Transform/override application, cross-package Material binding, real edits/export/fresh Unity restoration and VRC usability. Model transforms are explicitly marked UNRESOLVED; deeper containers describe edge structure only. Real Core roundtrip is not complete.

**Exact next action:** establish the smallest authoritative Renderer/material bridge using existing creation receipts and public Unity source-witness evidence; reproduce the cross-package Material gap without guessing identity, then return to actual private edit/export/restore.

## Execution sequence and current block

1. Close the in-progress skin roundtrip at a verified atomic checkpoint and push it.
2. Select multiple heterogeneous private packages and run Import smoke; compare Unity/Blender hierarchy, occurrences, Mesh, Armature and Materials. Fix actual input failures using public-safe synthetic regressions.
3. Preserve identity through save/reopen and actual edits; export packages, import into fresh Unity and restore required Mesh/Material/Skin/Bone/Prefab/VRC state. Repeat across the representative private cases throughout Core development.
4. Complete remaining Cleanup, Weight Transfer and Bone Merge functionality on top of the working Core, with protected references, preview and recovery.
5. Verify the entire original specification and a commit-bound distributable ZIP. Real-data Core success and full product completion remain separate acceptance claims.

Current block: model-backed private geometry populations now match the observed per-Prefab Unity counts for case B. Deep transforms/overrides and real model-instance export/restore remain unresolved; explicit cross-package Material confirmation is repaired. See the model checkpoint above. The native editing, receipt and static export gates are passed only for their recorded synthetic scope. Do not infer Unity localID from names/FBX UID. Preserve the full product goal.

## Existing-bone skin package checkpoint — 2026-09-26

**PROVEN (bounded synthetic):** the real Blender import/confirmation/edit/export operators retain an explicit prefab Transform-ID to native Bone receipt mapping across bone/Mesh renames and .blend save/reopen. The fixture changes topology and weights, stages an edited FBX under a new identity and keeps original source assets byte-for-byte. Fresh Unity 2022.3.22f1 imports the generated package and restores the edited skin using public APIs. The imported skin has 2 bones and 54 vertices; all 54 weighted vertices move by the expected maximum 0.15 with measured maximum error 0. Original bone IDs, materials, source FBX and unrelated prefab state survive. A second apply changes nothing; an invalid mapping is rejected without prefab changes. Packaged first-party C# helper bytes match the tested repository source.

**Verification:** repository-parent Python discovery 321 PASS / 0 FAIL / 0 ERROR; compileall PASS. Blender 5.2.1 skin GUI pipeline including register/unregister PASS exit 0; static package operator regression PASS. Fresh Unity validation PASS exit 0. The first deformation assertion failed because the probe omitted renderer scale from BakeMesh; using public BakeMesh(mesh, true) made observed and expected values agree. An initial validation setup also preloaded helper scripts at paths different from their package paths; the final fresh project uses exact Assets/VAPBExport paths and compiles successfully.

**Review adopted:** exported mapping row order must not serve as identity. The finalizer resolves each edited bone marker through an explicit dictionary and constructs the target array in edited Mesh slot order. The source bone array order remains a check of serialized source slots only. Root-bone mapping is separate when root is outside the weighted bone array. Python boundary tests cover shuffled mapping rows and a separate root; those two variants have not yet been exercised by a Unity runtime fixture. No broad identity guarantee follows from the 2-bone case.

**UNKNOWN / remaining:** real private Avatar validity, general model/nested occurrence realization, multiple Renderer/package export, new/removed/merged bones, Unity hierarchy/rest edits, VRC/custom state restoration and final installed ZIP. Unknown serialized state/dependencies stay protected. Cleanup/Weight Transfer/Bone Merge expansion is deferred behind real-data Core work.

Reproduce using tests/blender_skin_package_test.py with --prepare-fbx, then Unity VapbSkinRoundtripProbe.Prepare to produce a synthetic Source.unitypackage, then the same Blender script without --prepare-fbx to generate Output.unitypackage. A fresh Unity project should preload first-party helpers at their package destinations (Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs and Assets/VAPBExport/VapbRealizationMarker.cs), plus tests/unity_skin_roundtrip_probe/Editor/VapbSkinRoundtripProbe.cs under Assets/Editor. Put only generated Output.unitypackage and SourceInfo.json at its root, then run VapbSkinRoundtripProbe.Validate in batchmode without -quit; it writes a bounded result and exits 0/1.

**Exact next action:** bounded Import smoke of heterogeneous private packages selected from the existing 24-package catalog, including the authorized representative Avatar, then fix observed Core defects through public-safe synthetic regressions. Original private inputs remain outside Git and read-only.

## First private Core Import checkpoint — 2026-09-26

Selected four distinct package contents from the existing catalog, including the authorized representative Avatar and structurally different skinned/nested/Variant candidates. Reused catalog hashes and checked bounded working copies; no full-corpus rescan or private original edit. All four originals still match their catalog hashes. Selected inputs contain no C# or DLL according to the catalog; Unity execution requires its own bounded content/dependency check.

Initial result: two packages imported and reopened; two failed in Material creation. Repository-frame exception tracing isolated integer Math socket indexes being passed to the string-key `bpy_prop_collection.get()` API. Both the smoothness-inversion and alpha-cutout paths had the same bug. A fully synthetic two-case Blender regression reproduces both errors (exit 1), and changing only those two call sites to indexed socket access gives 2 PASS (exit 0). The two failing real inputs then import and reopen successfully. Scope review: PASS for the correction; the smoke runner review also identified unchecked save/open operator results, which are now explicitly checked before reporting PASS.

The following are **process/metadata observations, not Unity structural equivalence or Core completion**:

| Anonymous case | Source Prefabs / PrefabInstance documents | Imported Mesh Objects / Armatures | Recorded Renderer occurrences | Import / save-reopen |
|---|---|---|---|---|
| A | 15 / 12 | 459 / 18 | 170 | PASS / PASS |
| B | 2 / 8 | 4 / 0 | 0 | PASS / PASS |
| C | 20 / 19 | 4 / 0 | 2 | PASS / PASS |
| D | 4 / 4 | 102 / 3 | 54 | PASS / PASS |

Source document counts are serialized-document observations, not resolved occurrence counts. In particular, B has only inherited/model Prefab structure and no directly serialized Renderer documents; zero projected Renderer occurrences is a significant unresolved Core boundary. A contains 176 serialized skin Renderer documents across the archive, while the chosen automatic composition records 170 occurrences and exposes 459 Mesh Objects. These different populations must be reconciled by source/instance identity rather than equating aggregate counts or treating the difference as proven duplication.

For A, the saved .blend has 19 images referenced by used Material nodes; all 19 are packed and decode after reopen. Other unused/unreferenced Image datablocks lack external files, so `images_loaded` or total Image counts alone do not prove texture loss or preservation. Appearance equivalence, required source Renderer coverage, readable composition structure, actual edits, package export and fresh Unity/VRC usability remain **UNKNOWN / NOT RUN** for all four real cases. Private logs, source identifiers, working packages and .blend files remain outside Git; only this aggregate finding and synthetic regression are public.

Verification: Python 321 PASS; compileall PASS; synthetic Material regression 2 PASS; four bounded private Import/save-reopen successes after the correction. Private validation is now an active development layer, not deferred final QA.

**Exact next action:** use Unity 2022.3.22f1 public APIs in a dedicated private Oracle to resolve case B's inherited/model Prefab structure and compare authoritative source/occurrence relations with Blender's zero recorded Renderer occurrences. Fix confirmed Core gaps through public-safe synthetic regressions before auxiliary-feature expansion.

### Case B public-API comparison: real Import defect confirmed

Dedicated fresh Unity 2022.3.22f1 import and structure observation exited 0 with no compiler errors. Each of the two prefab assets contains **31 Renderers / 23 SkinnedMeshRenderers**. One has a one-hop Renderer source relation to models; the other resolves through a Prefab then to models. The four standalone FBX roots contain 27 Renderers / 23 skins in total. Do not add standalone model assets to prefab-instance populations when comparing compositions. Persistent GUID/signed local IDs and source chains were obtained through public APIs and kept only in private local evidence. The no-SDK observation project has 38 missing components; component/VRC behavior is not proven by the structural result.

Blender's 4 Mesh Objects / 0 Armatures for this package is a confirmed Core Import defect. Code tracing identifies independent boundaries: selective extraction and member assembly consume direct Mesh/material-override FBX references but omit model-backed `m_SourcePrefab` closure; AUTO selection also excludes candidates whose Renderer count is only inherited/model-backed. Existing candidate analysis already tracks transitive visual dependency GUIDs, which can be reused. Separately, Renderer occurrence projection stops at a binary model source, because current metadata does not supply Unity-generated local IDs. Fixing geometry inclusion must not fabricate those IDs or claim the identity boundary is solved.

**Current next action:** reproduce the model-instance and inherited-Variant paths using a Unity-generated public-safe synthetic package, correct bounded dependency extraction/attachment, then recheck private B. Keep exact Unity Renderer identity coverage and missing VRC dependencies explicitly unresolved until independently proven.

Public repro fixture is now committed in `tests/unity_model_instance_fixture/Editor/VapbModelInstanceFixture.cs`: it preserves a nested FBX Model Prefab in a base Prefab and a true Variant, and includes an unrelated second FBX so the old single-FBX fallback cannot mask selection errors. Unity 2022.3.22f1 confirms one Renderer/one skin/two bones per Prefab, source-chain depths one/two, one class1001 document and zero directly serialized Renderers per Prefab. Source package contains only the two Prefabs and two synthetic FBXs, no executable assets. This proves the source fixture, not the pending Blender correction.

The generic public-API observer is `tests/unity_private_structure_probe/Editor/VapbPrivateStructureProbe.cs`. In a dedicated project with an already-reviewed `Input.unitypackage`, run `VapbPrivateStructureProbe.Run` in batchmode without -quit. Its summary separates model and Prefab asset counts; detailed source/occurrence IDs are written at the local project root and must remain outside Git. Both new helpers passed read-only scope review; both were compiled/executed in Unity with exit 0. A separate Blender run during in-progress dependency changes is not recorded as an immutable before/after result.

## Checkpoint: observed FBX Object-copy lineage

- Change: production composition-member copies now call `copy_with_receipt`. A validated same-session source receipt is explicitly transferred to the observed copy, with a fresh persistent realization ID and its source realization ID. Shared Mesh/source metadata is untouched. Unobserved copies lose inherited receipt authority; Renderer occurrence bindings are never copied across Objects.
- Scope: closes only the observed source-Object -> member-Object edge. Does not prove Unity Renderer -> FBX primitive, package/root scope, or arbitrary duplicate/reopen continuity. Session UID is a transient check, not persistent identity.
- Python 3.14.6: from repository parent, `python -m unittest discover -s unitypackage_blender_importer/tests -p 'test_*.py' -t . -q`: **241 PASS**, 0 FAIL/ERROR, three new receipt tests. Initial focused test failed because copy API was absent; implemented API passed 7 focused tests.
- Blender 5.2.1 LTS: `blender --factory-startup --background --python-exit-code 1 --python tests/blender_integration_test.py`: exit 0; integration PASS, receipt rename/save/reopen PASS, addon register/unregister completed. `OCCURRENCE_SKIN_LINK=LINK_NOT_YET_PROVEN` remains explicit.
- Negative control: execute `_run_fail_closed` with a synthetic AssertionError through Blender `--python-expr`: exit 1 (without relying on `--python-exit-code`).
- Compileall for blender/unity/operators/ui/export/validation PASS. Independent scope_guard: PASS, no unnecessary implementation found; accepted with no production revisions requested.
- Runtime evidence is under ignored `artifacts/campaign/`. Required tests and code are tracked; no private input was used.

## Checkpoint: atomic UnityPackage publication

- `export/package_writer.py` now stages a complete, closed archive beside the output, publishes it with an atomic non-overwriting hard link, and removes its temporary file. Serialization failure exposes no final filename; an existing or racing output remains unchanged. Filesystems without hard-link support fail closed (export to a supported local filesystem); no unsafe fallback.
- Tests initially reproduced both final-name visibility during writing and leftover partial output on simulated disk failure. Focused materialization suite: 20 PASS (three new writer regressions, including competing output protection), Python 3.14.6 from repository parent.
- Scope_guard review PASS. This is export storage correctness, not proof of Blender editing or Unity reimport. End-to-end EX-03 remains incomplete.
- HEAD-only clean checkout of code `a358bf070a35346d645d09bbbfdb12e76ad3e08d`: full Python suite **244 PASS**, 0 FAIL/ERROR, same repository-parent discovery command. No untracked helper was needed.

## Checkpoint: retain serialized modification scope

- `PrefabModification` now retains its containing signed PrefabInstance fileID. Material override records retain that instance ID and the actual referenced Material fileID, separate from the targeted Renderer fileID. Display-name lookup is scoped by instance and source GUID, so repeated source renderers cannot leak names across instances.
- This preserves serialized evidence needed by production occurrence traversal. It does not turn the existing source-key-only effective resolver into an occurrence resolver.
- Regression first failed on missing fields; parser and Stage 1A suites then **18 PASS** on Python 3.14.6. Command from repository parent: `python -m unittest unitypackage_blender_importer.tests.test_prefab_parser unitypackage_blender_importer.tests.test_stage1a_synthetic_projection -q`. Scope_guard PASS. An earlier combined invocation named a nonexistent Stage 1B test module and failed discovery; the corrected invocation above is the recorded result.

## Checkpoint: actual static-Mesh package roundtrip

**Supported boundary:** one directly serialized MeshRenderer in a Prefab, one native mesh in its continued FBX asset, confirmed occurrence binding, preserved source archive, known complete dependency set. The Blender export menu creates a real unitypackage; the included first-party Unity finalizer restores exact Mesh/material references by signed source component identity and imported realization marker. Geometry and material assignments are exported; original Unity shader state and Prefab transforms stay unchanged. Whole-source closure is conservative, not Cleanup. Skin, nested/model child references, arbitrary state and cross-package export remain required work and are explicitly rejected by this intermediate route.

**Evidence on working changes above `d50dc37`:**

- Python 3.14.6 from repository parent: `python -m unittest discover -s unitypackage_blender_importer/tests -p "test_*.py"`: **299 PASS**, no failures/errors.
- Blender 5.2.1 factory/background `tests/blender_package_roundtrip_test.py -- <source-oracle>`: actual import -> confirmed binding -> rename -> 1.25x vertex geometry edit -> save/reopen -> production export operator; exit 0, `BLENDER_PACKAGE_ROUNDTRIP_PASS`. Staging Scene/Object counts and edited geometry remain unchanged after export. Register/unregister included.
- Unity 2022.3.22f1 `VapbRoundtripProbe.Prepare` creates the source package using public APIs. `VapbRoundtripProbe.Validate` runs in a separate fresh project with no original asset package, only its generated output and the probe support scripts: exit 0, report `pass=true`.
- Fresh output has 24 vertices; all-axis bounds extents change from approximately 0.01 to 0.0125 as requested; center remains 0. Mesh from the edited model, exact Material identity, original hierarchy/transforms, second Apply byte equality, and invalid target rejection without Prefab mutation all PASS. The intentional invalid-ID control emits one expected finalizer error; this is not a zero-error whole-log claim.
- Raw Prefab source and restored Prefab both name the saved root `Avatar`. The earlier probe expected the pre-save constructor name `AvatarRoot`; that test assumption was corrected from actual source evidence.
- Unity `ImportPackage` completes asynchronously: the probe waits for its public completion event and has an explicit failure/cancel/timeout result. `LoadPrefabContents` exposed no matching source IDs in this runtime. Production instead resolves the persistent prefab asset directly through `AssetDatabase.TryGetGUIDAndLocalFileIdentifier` and saves through `PrefabUtility.SavePrefabAsset`; no name/order join.
- Before mutation, model bytes are hash-checked, targets/materials are fully resolved, needed Prefab changes require the archived source hash, and dirty existing Prefab components are rejected. Rollback covers property writes and save failure; writer publication remains atomic/no-overwrite.

**Reproduction:** use separate synthetic source/fresh Unity 2022.3.22f1 projects. Place `unity_editor/VapbRealizationMarker.cs` and `unity_editor/Editor/VapbReferenceFinalizer.cs` under `Assets/VAPBExport` with the same relative Editor folder; put `tests/unity_roundtrip_probe/Editor/VapbRoundtripProbe.cs` under an Editor folder. Run Blender `--factory-startup --background --python-exit-code 1 --python tests/blender_package_roundtrip_test.py -- <source-project> --prepare-fbx`; then Unity `-batchmode -projectPath <source-project> -executeMethod VapbRoundtripProbe.Prepare -logFile <log>` (no `-quit`; the probe exits explicitly). Run the same Blender script without `--prepare-fbx` to produce `Output.unitypackage`. `--output <new-name.unitypackage>` permits a new result without overwriting existing output.

For automated fresh validation copy `SourceInfo.json` and the generated output as `Output.unitypackage` to the fresh project root. Preload only the two exact first-party C# payloads **and their meta files from the output package**, plus the probe C# script, so the running validation method is available before Import. No source FBX/Prefab/Material is preloaded. Run Unity `-batchmode -projectPath <fresh-project> -executeMethod VapbRoundtripProbe.Validate -logFile <log>`. Success requires process exit 0 and `VapbRoundtripResult.json` pass=true. These generated assets/logs remain outside Git. Normal user import simply lets Unity compile the included scripts and uses the menu.

Fresh committed checkout of `5635fc3c65a5a2cf395d1598c1c2fd7fdad54f00`: Python **299 PASS**, clean worktree; live remote SHA matched. Final bounded scope review PASS. One authorized earned reset has now been consumed through the documented official app-server API; two remain. Delayed window refresh was confirmed after consumption; detailed account values and the idempotency record are kept outside Git.

**Next action:** extend the verified reference path to Skin/bone correspondence, then the mandatory Cleanup/Bone Merge and VRC state restoration. This is an intermediate result, not requested-spec completion.

## Checkpoint: source-preserving model package materialization

`export/model_package.py` connects the existing semantic graph, asset plan, staging tree, export manifest and atomic writer. It validates the archived package and original model SHA256, rejects duplicate tar fields and provider/path collisions, preserves continued FBX GUID/meta/path, and marks changed model bytes as MODIFY with post-import rebind required. Other original assets are retained verbatim as a **conservative whole-source closure**, not a minimal reachability claim. Folder assets retain their metadata without invented payloads.

Python focused validation: `test_model_package` plus `test_export_materialization`: **24 PASS**. Read-only scope review found no production scope issue. This adapter alone does not prove a Unity roundtrip. The pending GUI/finalizer integration targets direct static MeshRenderer first; skin/nested/VRC restoration remains required later. First Unity fresh-import attempt exposed asynchronous ImportPackage completion in the probe; after correcting that, the current integration gate is resolving loaded Prefab contents back to signed source component IDs using documented public APIs. No name/order mapping is accepted.

## Checkpoint: declared Weight Transfer boundary

The optional boundary guard treats reference Armature local X=0 as a user-declared plane, with 1e-5 local-unit tolerance. It protects cross-plane hits and includes them in explicit warning selection; it does not infer anatomical identity. A rotated-rig fixture proves that the check uses rig-local rather than world X.

Validation on top of code `3a19a71`: Python 3.14.6 `python -m unittest discover -s unitypackage_blender_importer/tests -p "test_*.py"` from repository parent: **289 PASS, 0 FAIL, 0 ERROR**. Blender 5.2.1 factory-background `tests/blender_weight_transfer_test.py`: exit 0 and `WEIGHT_TRANSFER_RUNTIME_PASS`, including guard on/off, preview unchanged, protected weights, selection and existing rollback/Undo. Read-only scope review: PASS. Full product remains incomplete; next action is production UnityPackage export and public-API reference restoration.

## Checkpoint: explicit surface Weight Transfer

- Added numerical interpolation, three declared modes, Japanese sidebar and explicit preview/apply; integrated addon registration. Confirmed group mappings clear when A/rig/B changes and confirmation clears on mapping edit. No automatic transfer and no claimed bone identity from names.
- Original-mesh world-space triangles support different topology. ALL/SELECTED scope, distance limit, locked/unmapped weights and shared Object/Mesh protection. Preview does not alter weights/geometry; a separate explicit button isolates B and selects unresolved vertices. No normalization/pruning or armature mutation.
- Numeric suite: 3 PASS, including a regression initially reproducing zero division on a degenerate triangle. Blender 5.2.1 background probe PASS/exit 0 verifies modes, selected range, locks/B-only weights, source preservation, shared mesh/scene rejection, confirmation invalidation, real posed deformation, injected apply failure rollback, and actual Blender Undo with explicit scripted undo boundaries.
- `blender --factory-startup --background --python-exit-code 1 --python tests/blender_weight_transfer_test.py` emits `WEIGHT_TRANSFER_RUNTIME_PASS`. Full addon integration still PASS including register/unregister, receipt rename/save/reopen and existing fail-closed entrypoint. Compileall PASS. Scope_guard PASS; accepted without extra abstraction.
- First working-tree full discovery encountered the concurrently developing occurrence test before its module existed (248 passing tests plus one discovery error). This is not recorded as full-suite PASS; commit-only full suite is the checkpoint criterion.
- Remaining WT coverage: left/right caution visualization, representative private fitting quality, final installed GUI use. Original mesh only, not evaluated pose/modifier surface. Instructions in README.
- Code `238f80cabfb46c69e22fd2646f7354aa55605f50` only, clean checkout: **248 PASS**, 0 FAIL/ERROR. Remote branch live query matched this SHA after push.

## Checkpoint: actual occurrences and confirmed native skin binding

- Production traversal follows actual serialized PrefabInstance documents, including signed instance edges, source package/member/revision and Renderer owner membership. Repeated nested instances remain distinct. Missing/cyclic/binary/duplicate sources and incomplete material overrides are diagnostics, not inferred renderers. No reference-adapter Cartesian product.
- Import persists this projection on each root and identifies directly realized semantic owners. A small Japanese GUI explicitly confirms one scoped Renderer -> unique native mesh receipt -> Armature relationship. Root/source revision, package, GUID, signed IDs and receipt lineage must agree. Confirmation is persisted as USER_CONFIRMED; it is not automatic Unity model localID -> FBX UID proof. Ordinary duplicate metadata is rejected.
- Material localID is parsed from its class-21 document; absent/multiple documents remain unproven. Material assignments use the exact package/GUID/fileID, all slots validated before writing, OBJECT links preserve shared Mesh values. A shared mesh needing additional slots requires explicit single-user action. Undo/rollback supported. The old Renderer-fileID == GameObject-fileID override join is disabled; deferred dependencies cannot bypass occurrence confirmation.
- Legacy FBX export reads effective Object material slots and validates persisted Renderer links before writing; the sidecar carries confirmed provenance. No new claim of Unity rebind/restore is made.
- Focused tests: occurrence traversal 19 PASS; binding core 11 PASS; material parser 8 PASS; material manifest 4 PASS. Material parser and Object-slot regressions initially failed and then passed. Full working-tree discovery passed 280 checkpoint tests but exposed a separate uncommitted source-storage test failure; that source-storage WIP is excluded from this checkpoint and is being corrected.
- Blender 5.2.1: full addon integration exit 0, `OCCURRENCE_SKIN_LINK=USER_CONFIRMED_PASS`, `CONFIRMED_BINDING_RENAME_SAVE_RELOAD=PASS`, `BLENDER_INTEGRATION_OK`. Probe explicitly makes its test mesh single-user, confirms via the real operator, verifies unchanged original shared mesh, duplicate rejection, exact material and preserved sidecar evidence. Initial integration found invalid Blender collection membership syntax in the new operator; corrected and rerun. Shared-member material probe PASS for untouched shared values, independent Object slots, save/reload and false identity rejection. Compileall PASS.
- Still incomplete: semantic owner realization for nested/model children, automatic source evidence, cross-package provider selection in this bridge, Unity finalizer/MRUS, full unitypackage export and final installed/private workflows. No input coverage was generalized from this synthetic success.

## Decisions / evidence / next action (current)

## Checkpoint: durable original package storage

- Import now retains exact source UnityPackage bytes at the user-selected directory or Blender DATAFILES/vapb/sources. Complete SHA-256 filenames, streaming copy and verification, same-directory atomic non-overwriting publication, corrupt-existing refusal and failure cleanup. Originals are not edited; identical verified snapshots are reused. Parent/child package imports retain the same configured archive directory.
- Existing Scene package registry stores each original archive path independently of temporary extraction. Synthetic Blender probe deletes only its generated incoming package after import and confirms cached bytes survive extraction removal and .blend reopen. Other-PC relocation still requires preserving the external archive directory; do not call the .blend self-contained.
- Source-store suite **8 PASS**. Initial full-suite failure was traced to Windows `fstat` vs `Path.stat` creation-time drift, not different bytes. The final comparison retains file identity/size/mtime and SHA-256; creation time is not a content signal. A synthetic 300-attempt reproduction went from 42 false rejections to zero after correction; a focused regression covers that drift. No private input used.
- Full Python 3.14.6 repository-parent discovery: **288 PASS**, 0 FAIL/ERROR. Blender 5.2.1 integrated synthetic import/confirm/export/save/reopen PASS, exit0. Scope_guard PASS.
- Prior committed binding checkpoint `aef6e60af2eb0895aa4953b53a4e043879f6ca74`: fresh HEAD-only checkout **280 PASS**, live remote query matched after push. Binding review scope_guard PASS.

## Checkpoint: Unity public-API marker persistence gate

- Added only public synthetic probe sources: Blender skin fixture generator plus Unity runtime marker component and Editor probe. A fresh dedicated Unity **2022.3.22f1** project was created outside the VAPB repository. Private/commercial data and existing Oracle projects were not used or changed.
- Blender **5.2.1** exports the explicitly generated Mesh's `_vapb_fbx_realization_id` custom property. Unity's documented `OnPostprocessGameObjectWithUserProperties` callback observes it and attaches a marker component. After model import, the probe retrieves the marked GameObject and its directly attached Renderer/Mesh, then calls public `AssetDatabase.TryGetGUIDAndLocalFileIdentifier` with signed `long` IDs. No name/path/order selects the Renderer; the known asset path selects only the test resource.
- Actual Unity result: **PASS, process exit0**, version2022.3.22f1, callback observed twice, marker count1 in both imports, Renderer/Mesh and nonempty geometry observed, GameObject/Renderer/Mesh IDs available and stable across two unchanged forced imports. During the probe Run: **0 error logs, 0 warnings**. This is not a whole-Editor historical Console count or proof IDs survive arbitrary edits.
- Initial Blender generator accessed an EditBone handle after leaving Edit Mode; fixed. Scope_guard identified an unused bone marker, which was removed; final exact fixture/probe rerun PASS. No production identity fallback was introduced. This establishes one required public-API observation mechanism, not completed Unity finalizer/MRUS.
- Reproduce in an empty synthetic project: copy `tests/unity_marker_probe/VapbSyntheticMarker.cs` to `Assets/VapbProbe/`, and `tests/unity_marker_probe/Editor/VapbMarkerProbe.cs` to `Assets/VapbProbe/Editor/`. Generate the FBX with `blender --factory-startup --background --python-exit-code 1 --python tests/blender_unity_marker_fixture.py -- <project>/Assets/VapbProbe/Synthetic.fbx`. Then run Unity2022.3.22f1 `-batchmode -projectPath <project> -executeMethod VapbMarkerProbe.Run -logFile <local-log>`. Do not reuse a private project. The fixed-enum/boolean/count report is `<project>/VapbMarkerProbeResult.json`; failures exit1.
- Public API references: [user-properties callback](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetPostprocessor.OnPostprocessGameObjectWithUserProperties.html), [signed localID observation](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html).

## Decisions / evidence / next action (latest)

- DERIVED: contract adapter is reference-only; do not rebuild it or call it production-complete.
- UNKNOWN: input-independent authoritative Unity Renderer -> FBX primitive mapping. Resolve from production code and supported serialized evidence; unsupported roots cannot silently succeed.
- First remote probe failed due absent Git username; existing GitHub CLI authentication succeeded through command-scoped helper. No persistent Git configuration change.
- Resource policy: use official shared-account usage readings; protect final-window 30% remaining. Three earned resets confirmed available at campaign start, zero used. Do not purchase credits or change plan. Detailed account values stay outside the repository.
- NEXT ACTION: integrate verified durable RAW-source storage, then connect scoped edit/export semantics to a fresh Unity public-API roundtrip. Continue the remaining mandatory requirements afterward.

---

# Historical investigation (superseded where current checkpoint differs)

# VAPB 現在地点から最終目的までの完了工程

この文書は、会話履歴を読まなくても VAPB の目的、現在の実装状態、観測事実、未確定事項、次の一手を理解できるようにした公開安全な handoff 文書である。

作成時点の調査対象ブランチは `feature/multi-package-identity`。この文書の作成では production code、schema、runtime behavior、Unity/Blender の実データを変更していない。

## 1. 最終目的

VAPB の最終目的は、次の往復を identity-safe、fail-closed、検証可能な形で成立させることである。

```text
one or more UnityPackage files
    -> semantic analysis and dependency closure
    -> Blender realization
    -> Blender editing / merge
    -> self-contained UnityPackage
    -> Unity public-API reimport observation
    -> deterministic identity rebind and state restore
    -> validated final Unity / VRChat avatar state
```

ここでいう「完成」は、見た目が Blender で表示できることだけではない。Unity の source identity、Prefab occurrence、Renderer、Material slot、Texture、Bone、Shape Key、Component、依存関係を、編集前後で追跡できることが必要である。Unity や VRChat の挙動をオフラインで推測して完成扱いにしない。

## 2. 調査時点のリポジトリ状態

### OBSERVED FACT

- Branch: `feature/multi-package-identity`
- HEAD at the previous handoff: `aa4cd4a2ab585fefe68ce7830c4b937b818f1a46`.
- `origin/feature/multi-package-identity` は同じ HEAD を指している。
- 作業ツリーには、今回以前からの未コミット変更がある。Importer、Prefab parser、Material builder、provenance bridge、export 関連の追加ファイルなどが含まれる。
- したがって、未コミットの exporter/provenance 実装は「現行HEADの完成機能」ではなく、検証前の作業ツリー状態として扱う。
- 今回追加するのは本 handoff 文書だけであり、既存の dirty file は commit 対象にしない。

### DECISION

未コミット変更を reset、checkout、stash で消去しない。今回の commit は `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md` のみを対象にする。

## 3. VAPB の現在 architecture と不変条件

### 現在の pipeline

```text
UnityPackage
  -> Package Reader
  -> Asset Index
  -> Dependency Resolver
  -> Semantic / Identity Layer
  -> Blender FBX / hierarchy / material realization
  -> Blender scene editing
  -> Bridge planning / staging
  -> UnityPackage or Unity project
  -> Unity Finalizer
  -> Final Prefab / VRChat validation
```

### 現在の invariants

1. **名前は identity ではない。** Blender object name、Prefab name、Material name は表示・診断用であり、解決キーに使わない。
2. **fileID 単独は identity ではない。** 宣言元 asset の GUID または scoped path と組み合わせる。
3. **occurrence と resource を分ける。** 同じ source Renderer declaration が複数の Prefab occurrence で使われる場合、各 occurrence を別記録にする。
4. **source identity と Blender realization identity を分ける。** Blender で生成された object/material slot が source component と一対一とは限らない。
5. **export identity と Unity post-import identity を分ける。** Blender が出した FBX の bytes や object names から、Unity が生成する model subasset localID を推測しない。
6. **ambiguity は自動採用しない。** 0件は `UNRESOLVED`、複数候補は `AMBIGUOUS` として停止または明示選択へ送る。
7. **unknown state は削除しない。** 未対応 Component や serialized state は preserve、unsupported、または explicit error として記録する。
8. **Unity/VRC の観測は public API のみ。** Unity Editor の documented public API による observation を正本とし、内部実装の逆解析や decompilation は行わない。
9. **出力は self-contained を証明する。** 外部絶対パス、未収録依存、曖昧な provider、未検証 sidecar を黙って残さない。

## 4. 実装済み・部分実装・未証明

| 領域 | 現在状態 | 境界 |
|---|---|---|
| UnityPackage reader / pathname / GUID index | IMPLEMENTED | tar.gz 読み取りと選択的抽出。全形式の互換性は別途検証が必要 |
| Prefab / Material / Texture source parsing | PARTIAL | Unity YAML の有用部分と明示参照を扱う。全 Component の意味保存ではない |
| package-scoped identity / collision | PARTIAL to STRONGLY SUPPORTED | scoped registry と collision report はある。全 occurrence closure は未完了 |
| sibling / transitive visual discovery | IMPLEMENTED for covered synthetic policies | 完全性判定と境界は fixture で検証。任意 package の完全性は未保証 |
| ambiguity-safe grouped import | IMPLEMENTED for covered paths | ambiguous provider の自動採用はしない |
| Blender FBX import | IMPLEMENTED | Blender native importer を使用。Unity post-import localID の保持は保証しない |
| hierarchy / material / texture realization | PARTIAL | supported geometry/material path はあるが occurrence receipt が未閉鎖 |
| PhysBone source capture / preview | PARTIAL | source snapshot と限定 preview。VRChat runtime parity / restore ではない |
| progress / foreground import UX | IMPLEMENTED for covered path | real UI surface と arbitrary environment は別検証対象 |
| bridge exporter | PARTIAL | FBX と material map sidecar の既存境界。UnityPackage repack ではない |
| deterministic UnityPackage writer | UNPROVEN / NOT RELEASED | 作業ツリーに prototype modules はあるが、実 Unity round-trip 未証明 |
| Unity Finalizer | PARTIAL | 既存 material restore path はある。generated model identity と Final Prefab は未完了 |
| MRUS state snapshot / restore | PLANNED | capture / rebind / restore / validation の契約が未実装 |
| complete Unity / VRChat parity | NOT A CURRENT CLAIM | shader exactness、third-party component、Animator/Expressions/Contacts の全面 parity は未証明 |

## 5. 最新 selected-avatar 調査の要点

以下は同一 run の selected-root と package-wide Effective graph を分けて読んだ結果である。実 asset の GUID、fileID、絶対 path は公開文書へ記録しない。

### OBSERVED FACT

- Unity の selected completed avatar root の母集団: **26 Renderer occurrences / 41 Material slots**。
- 同じ selected-root scope の VAPB Effective graph: **4 Renderer occurrences / 5 slots**。
- 差分: **22 Renderer occurrences が Effective graph に未到達**。
- raw FBX graph join: **26/26 exact**。raw FBX 側の source graph 不足ではない。
- Material の比較可能な行: **7**。
- 比較可能な valid Material mismatch: **0**。
- Material slot count mismatch: **2**。これは未到達 Renderer に属する slot の影響を含み、Material parser の値 mismatch と同一視しない。
- package-wide Effective graph: **257 Renderer occurrences / 394 non-null material slots / 14 prefab roots**。
- package-wide の数字を selected avatar root の数字として扱ってはならない。

### DERIVED

- 4 exact rows が正しいことと、selected root 全体が完成していることは別である。
- raw FBX join が 26/26 exact なのに Effective が 4 なので、主因は raw FBX 読み取りより上流の Effective semantic enumeration、Prefab inheritance/Variant 展開、root/occurrence attribution のどこかにある。
- 22件を閉じない限り、selected-root の semantic freeze、全 slot の receipt、Finalizer の全体 rebind を完了扱いにできない。

### HYPOTHESIS（未確定）

- 最有力は Variant / inherited renderer の occurrence expansion 漏れ。
- wrong-root attribution、Prefab chain attribution、identity collision もまだ排除しない。
- 22件の実体を確定する次の調査は、source renderer localID の offline reverse lookup と、Effective root/source kind/occurrence path/Prefab chain/omission reason の行列化である。

## 6. LUNA / SOL / Astra の調査結果

### LUNA の統合判断

- 22件は selected-root semantic completeness の一次 blocker。
- 26/26 raw FBX join と valid Material mismatch 0 から、先に Material shader を一括修正する根拠はない。
- package-wide 257件を selected avatar として export してはならない。
- 4件だけで完成 schema を固定するのも危険。限定 vertical slice には使えるが、全体完成の根拠にはしない。
- 次の作業は occurrence provenance 行列の確定と、無変更 round-trip baseline の準備である。

### SOL review の要点

- 現在判定は `HOLD`。順序修正が必要。
- 22件は semantic freeze の primary blockerだが、4 exact occurrence を使った限定 vertical slice まで禁止する blocker ではない。
- semantic freeze は一枚岩にせず、まず最小 semantic contract v0 を定義し、無変更 package round-trip と Unity reimport measurement を通した後に freeze する。
- 編集前に「無変更 preserve/repack -> fresh Unity reimport -> semantic diff」を通すことが必須。
- MRUS の完全 restore は後段でよいが、実 Unity import 前に capture/restore の安全契約だけは定義する。

### Astra independent review の要点

- occurrence/provenance -> semantic freeze -> Blender receipt -> minimal edit delta -> round-trip -> reimport identity -> Finalizer が主経路。
- 22件は source graph 不足ではなく、Effective 側の identity/inheritance/root representation 問題である可能性が高い。
- 22件を閉じないまま exporter schema や receipt を固定すると、欠落を正しい仕様として永続化する危険がある。
- no-op round-trip、fresh import、dependency closure、意図しない semantic diff を stop condition にする。

### Agreement / disagreement

**Agreement**

- 22件の selected-root occurrence 欠落が一次 blocker。
- raw FBX 26/26 exact と Material mismatch 0 を根拠に、別系統の一括 material 修正を急がない。
- 未コミット exporter modules は verified product capability ではない。
- names、単独 fileID、sidecar だけで generated model identity を代替しない。
- exact model-backed round-trip には Unity post-import observation または Finalizer が必要。

**Difference**

- LUNA の初期案は semantic freeze 後に exporter vertical slice を置く順序だった。
- SOL は、より安全な設計として「最小 semantic contract v0」の直後に無変更 preserve/repack と reimport baseline を前倒しするよう修正した。
- 採用判断は SOL 案。実際の Unity reimport drift を先に測ることで、semantic gap と exporter gap を混同しないためである。

## 7. 採用・棄却した仮説

### 採用した仮説

1. `OCCURRENCE_IDENTITY / PROVENANCE` が現時点の最優先問題である。
2. 22件の第一候補は Variant/inheritance 展開または root attribution の欠落である。
3. exporter は raw-preserve + typed patch + explicit Unity observation の hybrid が安全である。
4. Unity の generated model identity は offline で決めず、post-import observation に委ねる。

### 現時点で棄却した仮説

1. 22件の主因を「raw FBX が壊れている」とする仮説。26/26 exact join と矛盾する。
2. valid Material mismatch を主因とする仮説。比較可能範囲で mismatch 0。
3. package-wide Effective 257件が selected avatar root の正しい母集団だとする仮説。
4. object / material name の fuzzy match で occurrence identity を復元できるとする仮説。
5. Blender FBX export bytes から Unity model subasset localID を再現できるとする仮説。

## 8. 最終完了までの critical path

下表の `CRITICAL PATH` は、後工程の正しさを直接左右する工程を示す。

| Stage | 分類 | 目的 / なぜ必要か | 現在 | 不足 | 依存 | 実装・検証 | Human / Unity / Blender gate | DONE / stop condition |
|---|---|---|---|---|---|---|---|---|
| 0. Occurrence provenance closure | CRITICAL PATH | 26 occurrences を occurrence-aware に説明し、4/22差分を分類する | 4 exact、22 missing | source-localID reverse lookup、root/Variant/occurrence path、omission reason | 既存 parser / Effective graph | production変更前に診断行列を作る | Unity再実行は offline で足りない事実だけ Human Gate | 26/26 が EXACT、明示的 AMBIGUOUS、または理由付き MISSING。silent omission 0 |
| 1. Semantic contract v0 | CRITICAL PATH | source / occurrence / realization / unknown を固定する | identity基礎はある | occurrence schema、version、status vocabulary、slot scope | Stage 0 | synthetic repeated occurrence / inheritance fixture | Unity public observationで selected scope を照合 | 1 occurrence = 1 stable record、名前解決 0 |
| 2. No-op preserve/repack baseline | CRITICAL PATH | 編集差分なしで package writer と Unity import の問題を分離する | writer は未検証 prototype | self-contained staging、meta/GUID/path/dependency closure | Stage 1 | typed reachability、deterministic staging/writer、no-op manifest | Unity import は隔離 project で Human Gate | fresh project に self-contained import、欠落依存 0 |
| 3. Unity reimport identity measurement | CRITICAL PATH | generated / preserved asset の post-import identity drift を実測する | source observation はある | exact output hash、GUID/localID、Renderer/slot semantic diff | Stage 2 | Unity public APIで post-import sidecar を出す | `AssetDatabase`、`TryGetGUIDAndLocalFileIdentifier`、`GlobalObjectId` を使用 | identity drift が保持/remap/unsupported に分類される |
| 4. Blender realization receipt closure | CRITICAL PATH | Unity occurrence -> Blender object/slot -> export record を逆追跡する | Blender identityはpartial | receipt、mesh/material/texture mapping、unsupported preservation | Stage 1/3 | Blender 5.2.1 integration、save/reload、receipt validation | Blender real scene gate | 対象 occurrence の receipt coverage 100%、ambiguous は停止 |
| 5. Minimal edit-delta vertical slice | CRITICAL PATH | 最小編集1件で exporter の意味を検証する | design only | typed delta grammar、before/after hash、non-target invariants | Stage 2/3/4 | 1 avatar、1 prefab、1 model、1 material/texture edit | Blender実機で編集、Unityでは未変更 baselineと比較 | 宣言差分以外の semantic diff 0 |
| 6. Edited self-contained UnityPackage | CRITICAL PATH | 実際に配布可能な output を作る | package repack 未実装 | raw preserve、typed patch、collision/path checks、deterministic tar.gz | Stage 5 | package writer、manifest、testzip、external path scan | Unity isolated import | output が自己完結し、未収録依存 0 |
| 7. Minimal Unity Finalizer | CRITICAL PATH | offlineで決まらない generated identity を public API で再結合する | material restore はpartial | idempotent rebind、dry-run、validation report | Stage 3/6 | selected supported component のみ実装 | Unity Editor public APIs only | rerunで同じ結果、AMBIGUOUS/MISSING は fail closed |
| 8. MRUS capture / restore | CRITICAL PATH | Unity/VRC component state を失わずに戻す | planned | state snapshot、component refs、restore policy、validation | Stage 7 | Avatar/Animator/Expressions/PhysBone 等を supported/unsupported 分類 | Unity + available VRC public SDK observation | restored/rebound/partial/missing/unsupported を全件報告 |
| 9. Multi-package full closure | REQUIRED BUT PARALLELIZABLE | 複数 package の provider/namespace/collision を広げる | synthetic covered、real broad proof partial | export-side multi-package reachabilityとmerge | Stage 1/6後 | package-scoped graph、provider ambiguity、group export | real packageはHuman Gate | cross-package identityとself-contained outputが再現可能 |
| 10. Release UX / distribution | LATER | installable addon、progress、reports、ZIPを整える | importer distribution pathはある | exporter UX、release E2E、docs | Stage 6/7/8 | extracted ZIP register/unregister、public hygiene | Human visual retest | exact HEAD ZIP、testzip None、register/unregister PASS |
| 11. Shader / third-party / full VRChat parity | OPTIONAL / OUTSIDE CORE | 近似でなく完全再現を目指す場合のみ | not claimed | per-shader/per-SDK contracts | Stage 8 | feature-specific acceptance | SDK-specific Human Gate | support matrixが明示されるまで自動完成扱いしない |

## 9. Importer Semantic Freeze Gate

semantic freeze は「コードを二度と変えない」という意味ではなく、以後の exporter が依存する semantic contract を固定する gate である。

### 必須条件

- selected root scope と package-wide scope が明示的に分離されている。
- 26 occurrences と 41 slots が occurrence-aware に列挙される。
- 22件は unresolved のままでもよいが、理由・種類・次の観測が明示されている。silent omission は不可。
- source asset、source component、occurrence、Blender realization、material slot、texture role の identity schema が versioned である。
- exact / ambiguous / missing / unsupported の status が保存される。
- cross-package provider 解決と selected-avatar の single-package path を同じ母集団として混ぜない。

### Gate fail

occurrence の重複、wrong root、name-only resolution、package-wide混入、unknown state の削除があれば freeze を止める。

## 10. Export Prototype Gate

最初の export は「最終 exporter」ではなく、以下の minimum round-trip vertical slice とする。

### Minimum Round-trip Vertical Slice

1. synthetic または承認済み test fixture の単一 package。
2. 1 Prefab、1 model asset、1 Armature/mesh、1 Material、1 Texture。
3. Blender で宣言済みの編集を1件だけ行う。
4. unchanged assets は raw preserve。
5. changed asset は typed patch または明示 `CREATE/MODIFY`。
6. deterministic manifest と UnityPackage staging を生成。
7. Unity 2022.3 の隔離 project へ public API / 通常 import で取り込む。
8. post-import GUID/localID/Renderer/Material slot を capture。
9. expected delta と unexpected diff を分離する。

### Prototype gate fail

generated FBX の localID を推測する、未収録依存を暗黙に許す、meta/GUIDを省く、source packageを破壊する、または Unity reimport の結果を取らずに PASS とする場合は失敗。

## 11. Unity Reimport Gate

Unity の公式公開 API は asset GUID/path/local file identifier、Prefab source、GlobalObjectId、Renderer/Material 等の観測に使う。UnityPackage は `.unitypackage` 圧縮 asset package として import/export されるため、UnityPackage の bytes と post-import state を別レイヤーで記録する。

### Gate output

- output package hash と import observation id
- preserved asset の GUID/path/metadata
- generated model の post-import asset/subasset identity
- Renderer occurrence、mesh、material slot、texture reference の diff
- missing dependency、ambiguous candidate、unsupported component
- Finalizer を実行した場合の idempotence と validation result

### Stop

fresh project import が自己完結しない、unintended semantic diff がある、または generated identity が未観測なら Finalizer/round-trip を完成扱いにしない。

## 12. Finalizer Gate

Finalizer は「不足を推測で埋める処理」ではない。Unity が import した結果を public API で観測し、manifest の typed rebind task を deterministic に適用する境界である。

### 必須性

- preserved source assets の no-op round-tripだけなら、Finalizerなしで成立する場合がある。
- generated model/FBX の exact identity rebind、Prefab reference survival、Unity SDK object rebind が offlineで証明できない場合は、Finalizerまたは Unity semantic sidecar が必要。
- Finalizerは idempotent、dry-run可能、AMBIGUOUS/MISSINGで停止、raw private APIなしとする。

## 13. MRUS Gate

MRUS は Blender が Unity を完全再現する機能ではなく、Unity/VRC state を可能な範囲で capture -> rebind -> restore する契約である。

### 先に定義する state

- Avatar root / source Prefab chain
- Renderer / Material / Texture references
- Bone / Shape Key / animation path
- Animator / Expression / Avatar Descriptor
- PhysBone / Collider / Contacts
- third-party MonoBehaviour / script GUID / serialized references

各 state は `RESTORED`、`REBOUND`、`PARTIAL`、`MISSING_TARGET`、`MISSING_DEPENDENCY`、`AMBIGUOUS`、`UNSUPPORTED`、`ERROR` のいずれかで終える。未対応を成功扱いにしない。

## 14. 今やらなくてよいこと

- 22 occurrence が閉じる前の全体 exporter の拡張。
- package-wide 257件を対象にした export 完成主張。
- object name / Material name による fuzzy fallback。
- generated FBX の Unity localID の offline 推測。
- 全 shader family の完全 parity。
- 全 third-party component の YAML 再実装。
- MRUS 全項目の一括 restore。
- UnityPackage Export の release ZIP、tag、Release、main merge。
- private commercial asset、raw Oracle JSON、GUID/fileID一覧の commit。

## 15. 次に実行すべき Action（1つだけ）

**次の一手は、selected-root の22件について offline provenance matrix を生成すること。**

行キーは name ではなく、source renderer declaration の scoped identity とする。各行に次を持たせる。

```text
source_asset_kind
source_asset_identity
renderer_declaration_identity
expected_occurrence_scope
effective_root_scope
effective_source_kind
occurrence_path_token
prefab_chain_status
raw_fbx_join_status
material_slot_count
omission_reason
classification: EXPANSION_MISSING | WRONG_ROOT | IDENTITY_COLLISION | OTHER
```

この action を先に行う根拠は、raw FBX 26/26 exact、Material mismatch 0、Effective selected-root 4/26 という三つの事実を同じ表で結べるからである。ここで22件が分類できれば semantic contract v0 を確定でき、分類できなければその一点だけを Human Gate または Unity public observationへ持ち込める。次の action を exporter 実装にするのは順序が逆である。

## 16. Web / 公開仕様で重要だった外部仕様

以下は一次資料のみを参照した。URLは将来の再確認用である。

- Unity `AssetDatabase.TryGetGUIDAndLocalFileIdentifier`: GUID と local file ID は serialized asset reference の構成要素であり、Prefab等では64-bit local IDを扱う必要がある。
  https://docs.unity3d.com/ja/2022.3/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html
- Unity `GlobalObjectId`: Prefab、Scene、ScriptableObject等の Unity Object を project-scoped に識別する public Editor API。Prefab instance source と instance の区別を含む。
  https://docs.unity3d.com/ja/2022.3/ScriptReference/GlobalObjectId.html
- Unity Asset Packages: `.unitypackage` は圧縮 asset package で、Assetsへ importされ、metadata と asset links を含む。
  https://docs.unity3d.com/ja/current/Manual/AssetPackages.html
- Unity `PrefabUtility.GetCorrespondingObjectFromSource`: instance object から Prefab source object を public API で取得する境界。
  https://docs.unity3d.com/ja/2021.1/ScriptReference/PrefabUtility.GetCorrespondingObjectFromSource.html
- Blender FBX export API: FBX export settings、custom properties、animation、leaf bones等を明示指定できるが、Unity generated localID の保持を保証する仕様ではない。
  https://docs.blender.org/api/main/bpy.ops.export_scene.html
- VRChat PhysBones: avatar dynamics と collider/state の公式仕様。Blender previewをVRChat runtime parityと同一視しない根拠。
  https://creators.vrchat.com/common-components/physbones/
- VRChat avatar components: PhysBones、Contacts、Constraints等の公式 component 範囲。
  https://creators.vrchat.com/avatars/avatar-components/

## 17. 関連する repository paths

### Architecture / product

- `ARCHITECTURE.md`
- `PRODUCT_SPEC.md`
- `TEST_STRATEGY.md`
- `TEST_RESULTS.md`
- `docs/PACKAGE_COMPOSITION.md`

### Current identity / importer

- `unity/package_reader.py`
- `unity/asset_database.py`
- `unity/prefab_parser.py`
- `unity/effective_prefab.py`
- `unity/provenance_model.py`
- `unity/prefab_candidate_analyzer.py`
- `unity/material_parser.py`
- `unity/material_mapping.py`
- `blender/fbx_importer.py`
- `blender/fbx_receipt.py`
- `blender/provenance_bridge.py`
- `blender/hierarchy_builder.py`
- `blender/material_builder.py`
- `blender/identity_registry.py`

### Export design and prototype boundary

- `docs/EXPORT_ARCHITECTURE_DECISION.md`
- `docs/EXPORT_IDENTITY_MODEL.md`
- `docs/EXPORT_RESEARCH_CORRECTIONS.md`
- `docs/EXPORT_UNKNOWN_MATRIX.md`
- `export/semantic_graph.py`
- `export/asset_plan.py`
- `export/manifest.py`
- `export/staging.py`
- `export/package_writer.py`
- `export/fbx_export.py`
- `export/material_export.py`
- `export/texture_export.py`
- `export/raw_assets.py`

### Relevant tests

- `tests/test_package_reader.py`
- `tests/test_prefab_parser.py`
- `tests/test_prefab_candidate_analyzer.py`
- `tests/test_multi_package_identity.py`
- `tests/test_renderer_provenance_bridge.py`
- `tests/test_fbx_receipt.py`
- `tests/test_export_semantics.py`
- `tests/test_export_materialization.py`
- `tests/blender_cross_package_dependency_test.py`
- `tests/blender_multi_package_identity_test.py`
- `tests/blender_multi_package_visual_test.py`
- `tests/blender_real_identity_verify.py`

## 18. 検証結果と限界

### 今回実行した検証

- repository branch / HEAD / remote / dirty state: 確認済み。
- targeted `pytest`: 実行環境に pytest module がなく起動不能。これは production failure ではなく test runner availability failure。
- `python -m compileall -q export blender unity`: PASS。
- repository parent からの unittest discovery: **228 tests PASS**。
- remote branch HEAD: local HEADと一致。
- Unity/Blenderの実機再実行、real package import、exported package reimport: 今回は実施していない。

### 未検証事項

- uncommitted exporter/provenance modules の production integration。
- generated FBXを含む self-contained UnityPackage の Unity 2022.3 fresh import。
- edit delta後の semantic diff と Finalizer idempotence。
- MRUS state restore。
- real cross-package visual resultと、selected-avatarの22 occurrence分類の最終確定。

## 19. Handoff summary

### なぜ今この作業をしているのか

VAPBは単なる extractor/importerではなく、Blender編集を経た Unity/VRC state の安全な往復を目指している。そのため、見た目の import 成功より先に、source occurrence と Blender realization と Unity post-import identity の分離を確定する必要がある。

### 何が観測事実で、何が仮説か

- **OBSERVED FACT:** Unity selected root 26/41、Effective selected root 4/5、22 missing、raw FBX 26/26 exact、valid Material mismatch 0。
- **DERIVED:** primary blocker は occurrence/provenance closure。
- **HYPOTHESIS:** Variant/inheritance expansion または wrong-root attribution が22件の主因。
- **UNKNOWN:** generated FBX subasset identity、任意 packageの完全な reimport survival、全面的な VRC component restore。

### 次に何をすればよいのか

selected-root 22件の offline provenance matrix を一度作り、26 occurrences がどこで失われるかを分類する。その結果を semantic contract v0 と no-op preserve/repack baselineへ接続する。

## 20. Public-safety declaration

この文書は aggregate / sanitized な研究結果だけを含む。commercial UnityPackage本体、FBX、Texture、Material、Prefab YAML、raw Unity Oracle JSON、実 asset のGUID/fileID一覧、不要な private absolute path、スクリーンショットは含めていない。

## 21. Stage 0 provenance closure addendum (latest)

### OBSERVED FACT

The previously open 22-row selected-root gap is now classified using a private local provenance matrix. The 26 selected Unity Renderer occurrences divide into **4 EXACT_EFFECTIVE_OCCURRENCE** and **22 SELECTED_ROOT_REPRESENTATION_GAP**. All 22 have one or more package-wide Effective candidates under other roots; package-wide absence is 0 and selected-root ambiguity is 0. Other-root candidate multiplicity is 1 row with one candidate, 3 rows with two, and 18 rows with three.

The raw FBX graph remains 26/26 exact and comparable valid Material mismatch remains 0. The 22-row result is therefore not evidence of raw FBX graph loss or a Material value mismatch.

### DERIVED

The first observed missing stage is selected-root Effective assignment / occurrence projection. The current VAPB graph can emit the same model-source identities under other root evaluations, but does not yet prove the selected Unity instance's complete occurrence scope. This is a representation diagnosis, not proof of an incorrect Unity parent.

### UNKNOWN / STOP CONDITION

The current snapshot does not capture complete Unity Variant ancestry or a per-function runtime trace. The deeper distinction between model-child expansion loss, root attribution loss, and Variant/inheritance projection loss remains open. Production changes must wait for an occurrence-aware public Unity source/instance-chain observation.

### CURRENT NEXT ACTION

The next action is one public-API Unity observation of the selected root that records Prefab source/instance chain for all 26 Renderer occurrences. The standalone public-safe closure is documented in `docs/CASE_A.md`.

## 22. Stage 0.5 Unity source-chain observation (latest)

### OBSERVED FACT

The selected-root public-API observation completed with **26 Renderer occurrences / 41 Material slots**, immediate source resolved **26/26**, original source resolved **26/26**, and FBX model asset resolved **26/26**. Every row was a Connected Prefab instance with `PrefabAssetType.Variant` and a three-level observed chain: Scene Renderer -> selected Prefab source -> original FBX Renderer. Console errors were 0.

### DERIVED

The 4 exact and 22 gap rows share the same Unity chain. Therefore the loss boundary is proven after Unity source/original/model resolution and at VAPB selected-root Effective occurrence projection. Sol review classifies the 22 rows most strongly as `VAPB_ROOT_ATTRIBUTION_GAP` with medium confidence: they are emitted under other package-wide roots but not the selected root. Model-child expansion and Variant projection remain possible mechanisms, not isolated causes.

### DECISION

The final classification for all 22 is `VAPB_ROOT_ATTRIBUTION_GAP` (medium confidence), with mechanism assessment `SELECTED_ROOT_ATTRIBUTION_MISMATCH_MODEL_CHILD_AND_VARIANT_MECHANISM_UNRESOLVED`. Semantic Contract v0 design may proceed; full selected-root semantic freeze remains HOLD. Details are in `docs/CASE_A.md`.
+## 23. Stage 1A synthetic occurrence projection isolation (latest)

### OBSERVED / PROVEN

Stage 1A added only public synthetic fixtures. At the current `EffectivePrefabResolver` boundary:

- A Prefab that explicitly references a synthetic model with three source Renderer records, but has no Renderer material override, produces 0 Effective Renderers.
- Addressing one source Renderer by override produces 1 Effective Renderer; addressing all three produces 3.
- A serialized base Prefab containing three Renderer components remains 3 through the tested Variant and nested no-extra-override chain.
- Changing between the two tested non-empty synthetic Material GUIDs on the same override does not change the fixture's Renderer occurrence count.
- `OccurrenceKey` distinguishes the same source Renderer under different synthetic root/instance paths, but `EffectivePrefabResolver.resolve()` has no selected-root or instance-edge context parameter.
- Full Python unittest discovery: **233 tests PASS**.
- Relevant Stage 1A/parser/provenance tests: **26 tests PASS**.
- `python -m compileall -q blender unity operators ui export tests`: **PASS**.

The synthetic test and public-safe interpretation are stored in
`tests/test_stage1a_synthetic_projection.py` and
`docs/CASE_A.md`.

### DERIVED

- The result is reproducible as a general occurrence-projection limitation, not a CASE_A hack or rule.
- A source Renderer identity alone does not represent a selected-root occurrence; root context and instance-edge path are separate semantic data.
- An Effective semantic contract needs root context, instance path, source Renderer identity, owner/mesh identity, and ambiguity status.
- The synthetic run narrows the code boundary but does not prove that one mechanism alone explains the private real-asset gap.

### UNKNOWN

- Whether the final production correction belongs directly in `EffectivePrefabResolver`.
- Whether an occurrence projection layer should be introduced separately.
- Where model-child expansion and selected-root context should be integrated.
- Whether the observed variant identity-scope risk is present in every real Unity serialization shape.

### DECISION

- **Production behavior fix: HOLD.** No production logic was changed in Stage 1A.
- **Semantic Contract v0 design: proceed.** Define the contract from the synthetic fixture and the Stage 0/0.5 evidence before implementation.
- **Full semantic freeze: HOLD.** The selected-root projection mechanism is not yet fully proven.

### NEXT ACTION

Define Semantic Contract v0 with a synthetic occurrence-projection adapter test that emits all model-child Renderers under two selected-root/instance-edge contexts, preserving shared source identity while producing distinct occurrence keys. Do not implement the production correction until that contract boundary is reviewed.


## 24. Stage 1B Semantic Contract v0 (latest)

### OBSERVED / PROVEN

- `SourceComponentKey` represents reusable source identity using source kind,
  source asset GUID, and Renderer file ID.
- `OccurrenceKey` adds selected-root context and ordered instance-edge path,
  so the same source Renderer can be represented as multiple occurrences.
- `RendererOccurrenceContract` carries occurrence identity, expected owner,
  expected mesh, material overrides, and explicit contract version `v0`.
- Material override values preserve occurrence identity in the synthetic contract.
- Conflicting source relations fail closed as ambiguous.
- Serialization is identity-based and contains no object-name join.
- Stage 1B contract tests: **5 PASS**.
- Stage 1A synthetic tests: **5 PASS**.
- Production behavior changed: **NO**.

### DERIVED

- Source component identity and selected-root occurrence identity are separate
  at the synthetic contract boundary. Preservation through Importer, Blender
  realization, Exporter, and Unity rebind remains unverified.
- Root context and ordered instance-edge path are mandatory occurrence scope;
  source GUID/fileID alone is insufficient.
- The adapter boundary can be specified independently of the current resolver,
  allowing production integration to be reviewed separately.

### UNKNOWN

- Whether production correction belongs directly in
  `EffectivePrefabResolver`.
- Whether a separate occurrence projection layer should be introduced.
- Where model-child expansion and root context should be integrated.
- How Unity-generated ModelImporter local IDs will be supplied to production
  without guessing.

### DECISION

- Semantic Contract v0 is defined in
  `docs/SEMANTIC_CONTRACT_V0.md`.
- The synthetic adapter is a contract oracle only; it is not wired into import.
- Production behavior fix remains **HOLD**.
- Full semantic freeze remains **HOLD**.

### NEXT ACTION

Keep the production behavior fix on HOLD until the contract boundary is
reviewed against the existing package-to-Blender projection path. No
`EffectivePrefabResolver` change is authorized by Stage 1B.

## 25. PCA dirty-worktree recovery and public handoff (latest)

### OBSERVED FACT

- PCA branch: `feature/multi-package-identity`.
- Recovery started from remote HEAD `42c0358` and completed at a later
  feature-branch HEAD.
- The PCA working tree contained 11 modified tracked files and 30 untracked
  files. No destructive cleanup operation was performed.
- The committed HEAD-only clone had 172 passing pure-Python tests. The PCA
  working tree had 238 passing tests.
- The difference is five additional test files containing 58 test cases,
  plus 8 cases added to two already-committed test files: 172 + 58 + 8 = 238.

### HIDDEN DEPENDENCY FINDING

The first recovery commit restored `unity/effective_prefab.py` and
`unity/provenance_model.py`. A correct HEAD-only clone then exposed one more
required dependency: `unity/effective_prefab.py` imports
`PrefabModification` and related semantic APIs from the modified
`unity/prefab_parser.py`. That parser dependency was recovered in a second
commit. This is the canonical example of why local PASS is not handoff
complete.

### PUBLIC RECOVERY DECISION

Recovered public-safe source, tests, exporter prototype code, validation
tooling, architecture documents, and this handoff update were separated from
private or unclassified local material. No commercial asset, raw Oracle
output, real private GUID/fileID table, credential, or machine-specific
secret was committed.

The following remained outside the recovery commits: private/local diagnostic
outputs if present, the internal `docs/superpowers/` planning material, and
any unrelated dirty worktree changes not required by the committed test or
public implementation graph.

### REPRODUCIBILITY RULE

The required handoff acceptance condition is now explicit:

```text
GitHub feature-branch HEAD
  -> clean clone with the repository package path configured
  -> committed source imports successfully
  -> committed pure-Python tests pass
  -> compileall passes
```

The recovered HEAD-only clone passed the committed test population and
compileall. Blender and Unity acceptance remain separate gates and are not
claimed by this Python-only recovery.

### NEXT ACTION

Use the recovered public branch as the source of truth for the next review;
audit any remaining PCA dirty item as a separate atomic change before
committing it.

## Bone receipt and synthetic Unity source witness checkpoint (2026-09-26)

Native Blender 5.2.1 import now records source FBX Model UID, source GUID/SHA, deterministic receipt identity and unique realization identity on the EditBone returned by the official importer. The corresponding PoseBone receives the same values only after its Bone creation receipt matches. Names are not used as source identity. Native FBX export carries those PoseBone properties on the Model node. Unsupported bone-hook signatures leave existing Mesh receipt capture available.

Verification: Python **300 PASS**, compileall PASS. The focused Blender probe verifies two same-named source bones with distinct UIDs, rename/save/reload, actual parsed FBX Model properties, compatible Mesh capture with unsupported bone API, and hook restoration after success/failure. Scope review identified accidental Mesh/bone API coupling; the correction was adopted and verified.

A separate, test-only Unity 2022.3.22f1 experiment checks a fully synthetic FBX before/after official Blender FBX re-encoding and injected source-UID custom properties. Parsed FBX semantics match except the official writer's root FileId/CreationTime fields. Original source bytes remain untouched. Public Unity API snapshots compare each persistent Transform/Mesh/Renderer ID, parent/rest state, geometry/bindposes/weights/shapes and skin references; they do not equate FBX UID with Unity file ID.

Actual Unity result: PASS; 5 transforms, 1 mesh, 1 SkinnedMeshRenderer, 2 skin bones; 4 unique marker callbacks, no duplicates or missing skin-bone marker. No-op, marker-added and restored-source snapshots match, and meta stays byte-identical after the baseline readable setting. This is evidence for this fixture and importer configuration only. General model identity mapping, skin package export and general Unity/VRC reference restoration remain incomplete.

Reproduction: use Blender with `--factory-startup --background --python-exit-code 1 --python tests/blender_bone_receipt_test.py`. For the independent witness experiment, run `tests/blender_fbx_witness_fixture.py -- <fixture-folder>`, create a fresh Unity 2022.3.22f1 project, put the three generated FBX files at its root, and copy `tests/unity_bone_witness_probe` scripts into its Assets tree preserving Editor placement. Run `-batchmode -executeMethod VapbBoneWitnessProbe.Run` without `-quit`; the probe exits 0/1 and writes `VapbBoneWitnessResult.json` at project root. No private corpus or third-party source copy was used.

## Native Cleanup / Bone Merge checkpoint (2026-09-26)

Both mandatory editing entrances now exist in the VAPB sidebar. This is a supported native-Blender checkpoint, not completion of the full Unity/VRC restoration requirement.

- Edit Cleanup: explicit Mesh/Armature selection, Japanese candidate/keep/unresolved reasons, unused material slots and verified unreferenced leaf bones only. Weight, used ancestors, bone parenting, constraints, envelopes, animation/drivers, opaque saved state and shared users protect affected resources. No global Material purge. Actual Undo and rollback are verified.
- Export Cleanup: optional independent flags in the FBX + Material Map exporter; analysis uses original references, mutation uses private scene/data copies. Actual parsed FBX contains 2 retained bones and 1 material from the 3-bone/2-slot fixture. Source data, parent/modifier links, selection and scene stay unchanged; an injected failure leaves no leaked staged objects/data. Explicit object/selection context overrides are necessary in Blender 5.2.1; scene/view-layer override alone was experimentally insufficient.
- Bone Merge: explicit A/B and per-bone confirmed EQUIVALENT/B_ONLY choices; unresolved choices and unsupported state stop before mutation. B-only rest/roll/pose chain transplantation, Mesh modifier/group and bone-parent updates are checked against evaluated world vertices. Stable local UUIDs and observed FBX source identities persist the remap across renames. B is retained. No automatic Weight Transfer, animation or Unity/VRC reference restoration is claimed.
- Scope review found one high-severity rollback bug: target-only existing groups could be renamed even if the forward operation never renamed them. Adopted the minimal fix: record only actual group renames and undo that list in reverse. Before-write and after-write failure controls preserve the existing target-only group's name and weight. No unrelated feature was added in response to review.

Verification: correct repository-parent Python discovery **309 PASS / 0 FAIL / 0 ERROR**; compileall PASS; Blender 5.2.1 cleanup runtime 11 checks including real Undo PASS; actual cleanup export PASS; Bone Merge pose/chain/parenting/UUID/rollback/Undo controls PASS; existing Blender import integration and register/unregister PASS. One invocation from the repository root produced 16 import errors because the package parent was absent; the exact repository-parent command below passed. This was an invocation error, not a Python-version compatibility finding.

Canonical Python command, run from the repository parent:
`python -m unittest discover -s unitypackage_blender_importer/tests -p 'test_*.py'`

Blender probes use `--factory-startup --background --python-exit-code 1 --python` with `tests/blender_semantic_cleanup_test.py`, `tests/blender_cleanup_export_test.py`, `tests/blender_bone_merge_test.py` and `tests/blender_integration_test.py`.

Next action: connect the actual skinned-Mesh package roundtrip, initially retaining the original source FBX/skeleton and validating the edited Mesh's skin compatibility with public Unity APIs before any sharedMesh rebind. This geometry-preserving-bone route does not replace the remaining general bone/weight/Unity/VRC reference-restoration work. Do not promote the synthetic source-witness experiment to a general identity guarantee. Private corpus and final distribution validation remain pending.
