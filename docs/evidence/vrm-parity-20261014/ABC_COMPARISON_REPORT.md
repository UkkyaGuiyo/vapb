# VAPB / VRM comparison — preparation checkpoint r2

Date: 2026-10-14 UTC. **INCOMPLETE: no comparison run has occurred.**

## Authority and preservation

Request: measure VAPB and VRM using the same first-party input and the same edits; assess the original goal of avoiding opening Unity, exporting VRM, then importing into Blender. Final acceptance needs control before edits, saved/reopened Blender state and Unity reimport, independent correspondence judgment, and separate installation/repeat UX timings.

The owner's 2026-10-14 11:51 UTC clarification is current evaluation authority. Intended final acceptance: only intended edits appear in Unity; no unintended changes. Blender final state is authoritative for geometry/topology/UV/normals/tangents/bones/transforms/weights/shapes/material slots and face assignment, plus explicitly supported edits. Original Unity state is authoritative for unedited Material/Shader properties, Texture references/settings, PhysBone/Collider, Contacts, Descriptor, Animation/FX/Playable Layers, Expression Menu/Parameters, Constraints, MA/NDMF and Prefab/Variant/Nested serialized state. Preserve and prove correspondence/ownership/dependencies/GUID/signed fileID; prefer original asset reuse. Unresolved correspondence is `UNRESOLVED`; no name-similarity repair and no unconditional component copying. Incompatibility must be refused with a reason.

Principled BSDF, simplified motion/animation and hidden gimmicks may be approximate Blender previews; they must never become restoration truth. Do not derive Shader or PhysBone state from preview approximations. A has no Unity-feature Blender-emulation success condition. B shader appearance is reference-only, while original native Material/properties/textures and face/slot correspondence are mandatory. C does not require PhysBone→SpringBone→PhysBone approximate equivalence. The owner reports a prior VRM hair-motion over-amplification experience; this is user-reported motivation, not reproduced evidence or a verdict on pinned tools.

Canonical remote: <https://github.com/UkkyaGuiyo/vapb>. Isolated clone, branch `research/vrm-parity-20261014`; base `b18e5e66bbcc0e22e9309ef9744f069b7f94fcbf` from `feature/connected-bone-action-20261012`. Remote branch readback matched on 2026-10-14. Initial checked-out branch was clean. No instruction branch is a base. Original UnityProject, Prefab, UnityPackage and Blend files are not modified. No product code changes, installs, Unity/Blender launches, uploads or VRChat client runs occurred.

Global AGENTS and base AGENTS, PRODUCT_SPEC and START_HERE were read. Local checkout has no `.agents`/`.codex` SKILL.md or `.failure-atlas/INDEX.md`; Failure Atlas consultation remains unavailable. Existing broader autonomous development records do not expand this specific comparison task. Primary model is inherited GPT-6, configured reasoning not exposed; independent design reviewer settings are recorded separately.

## Blocking condition

The parent has not allocated a fresh Unity/Blender slot or authorized a new isolated project. Latest update: owner confirmed Editor shutdown and parent requested safe shutdown by its current task owner, but actual termination and slot return are not confirmed. Existing Editor stays protected. Old PID is never used for operations. A read-only CIM inventory was denied by the sandbox, so current PID/start time/project, RAM, mutex, lease and project lock are **UNVERIFIED**. No inference that resources are free is made. A parent-thread message attempt returned `thread not found`; final platform handoff is the reliable delivery path.

Requested allocation: one isolated Unity 2022.3.22f1 Linear project, plus one Blender 5.2.1 LTS process, sequentially. Need a new project because the authorized existing Editor belongs to another task, both paths need equivalent pristine source and separate return destinations, and R requires different importer dependencies. Do not clone a private project. Before creating it, parent assigns owner and slot; verify fresh process command lines/start times, lock/lease/mutex, available RAM and protection set. Snapshot originals read-only; stage only first-party synthetic inputs under owned paths; release only newly owned processes and locks. Source and return runs should be sequential; protect source assets and compare hashes before/after. No slot acquisition implementation is added here.

## Minimum common input

Existing suitable building blocks at the base revision:

| Candidate | Useful feature | Why not already a complete common fixture |
| --- | --- | --- |
| `tests/blender_shape_identity_fixture.py` | First-party asymmetric mesh, Hips/Spine weights, three distinct shape channels | Only two bones; no verified valid Humanoid |
| `tests/blender_geometry_abcd_fixtures.py` | Material partitions, small positive weights, UVs, degenerate-face control | Separate small generic cases; no complete avatar |
| `tests/evidence/holmes-material-correspondence-20261011/PLAN.md` | Existing ThreeSlotSource: 12 independently identifiable UV faces, 2/4/6 material partition; raw/native separation | Material oracle, not verified Humanoid; cannot substitute past findings for R measurement |
| `tests/unity_skin_roundtrip_probe/Editor/VapbSkinRoundtripProbe.cs` | Source/ref/component capture helpers | No Humanoid builder found in searched tracked test C#/Python |

Selection is provisional: reuse ThreeSlotSource face/corner design and shape/weight patterns in **one** self-authored, valid Humanoid synthetic avatar. A small adaptation is needed; no fixture was generated and no Unity project was created. Confirm Unity `Avatar.isValid`/`isHuman` and exporter eligibility before the comparison. Include minimum Humanoid bones, one extra child, one skinned mesh, unique UV signatures, a deliberate UV seam, two nonzero shape channels, at least three material partitions, and some small positive influences. Keep a first-party prefab plus variant and explicit SDK component/reference objects for C. Additional shader feature cases are individual material configurations of this same input, not a large fixture matrix. Declare provider dependencies separately from first-party authored content. Third-party purchased assets are excluded.

Planned bone roles: Hips→Spine→Chest→Neck→Head; Chest→Left/RightUpperArm→LowerArm→Hand; Hips→Left/RightUpperLeg→LowerLeg→Foot. Add one uniquely offset extra child under one hand. Author a symmetric T-pose with explicit rest matrices. At runtime enumerate `HumanTrait.BoneName` and `HumanTrait.RequiredBone(index)` in Unity 2022.3.22f1 and verify every required role has a mapping; the proposed list is not eligibility proof. Record actual `Avatar.isValid`, `Avatar.isHuman`, mappings, hierarchy and SoulFlame eligibility before either run. Bone correspondence uses human roles plus captured hierarchy/rest relations; the extra child uses its unique structural/rest relation, not its name. Shape channels have distinct source delta patterns and stable independent unaffected anchors; edited values alone cannot define channel identity.

Pin generator revision/parameters and input file hashes once available. Source Unity avatar and its UnityPackage must come from that single immutable input. Both paths must observe identical enabled objects, expression values and pose; use a frozen Play Mode capture state for R. Record normalized rest/pose state independently: an R capture that bakes a live expression is not an unchanged-rest control. Preserve a control run with all shape values zero and no live animation.

## Experiment sequence

1. Record actual executable/add-on/package versions, SHAs, importer options, Unity Linear setting, VAPB ZIP/source hash and input hashes. Record source native data using existing probes; first evaluate dependencies/eligibility.
2. V0: UnityPackage → normal VAPB Import → no edit → save/reopen → VAPB Export → isolated Unity import and explicit Finalizer Apply → save/reopen Unity and capture. Record any guard refusal without bypassing it.
3. R0: same source Unity avatar → SoulFlame 0.6.1 frozen Play Mode capture → VRM1.0 → Blender VRM Add-on → no edit → save/reopen → VRM1.0 → UniVRM Unity import → save/reopen and capture. Capture each boundary so first loss can be located.
4. Only after V0/R0 records exist: start fresh copies from their imported controls; apply the same predeclared edit. Begin with one uniquely mapped vertex displacement in source local coordinates (convert frames explicitly). Then independent small edits to UV corner, positive weight distribution, shape delta, existing bone rest matrix, and face-material binding as needed for each feature judgment. Each isolated edit starts from its own control copy; do not confound all edits in one output. Record unsupported edit separately. Never select a vertex by output ordinal or name alone.
5. Use the independent judge contract in the loss matrix. Archive edited state, Blender save/reopen capture and Unity reimport capture with actual timing. A helper embedded in output is not an independent native consumer observation.
6. If desired C state is missing after UniVRM, evaluate a pinned VRChatConverter only after verifying that exact version accepts VRM1.0. Record before/after separately; do not silently add VRM0 conversion. Newly generated SDK components are not retained original components. Client/upload remain forbidden.

For C capture three distinct conditions: C1 immutable original avatar; C2 VRM roundtrip/regenerated return; C3 edited Mesh with original Unity serialized settings restored/reconnected. C3 is a controlled comparison condition, not authorization for a new product implementation or a claim that existing VAPB supports it. Use existing supported restore paths where available; if proof is missing, record BLOCKED/UNRESOLVED rather than inventing automatic reconnection. Compare original parameter values separately from bone/root/collider/renderer/binding correspondence and separately from observed Editor motion. Bone/weight/rest edits can change motion even if parameters are unchanged. Motion needs identical pose/animation/initial state/time steps and recorded displacement amplitudes; SpringBone dynamics and source PhysBone dynamics remain distinct. VRChat behavior is NOT_MEASURED because client/upload are forbidden.

For animation, preserve unedited Clip/Controller/layer/state/transition/parameter data separately from explicitly edited animation transport. Renamed/reparented/transformed bones and renamed shapes require proven binding remaps; similarity-based matching is prohibited. Validate bone existence, Transform/Renderer/Material relations, animation and Variant references, dependencies and original asset preservation before any Apply.

Spec reconciliation: PRODUCT_SPEC core final-state/semantic-recipe separation aligns with the clarification. Older approximate-preview/MRUS and historical bounded pass reports are not proof of all requested restored state. The owner clarification makes unchanged source semantic data and edit-aware reconnection explicit across a wider list; unsupported/unverified portions stay separate. Existing source code and previous evidence remain unchanged. VRM/glTF for 3D transport plus existing Manifest/Recipe for Unity-specific state is a design candidate only. A VRM-format omission is not automatically a whole-route defect if separately preserved data can demonstrably compensate.

## Results at this checkpoint

| Run | A | B | C | save/reopen | Unity readback | Cause |
| --- | --- | --- | --- | --- | --- | --- |
| V0 / R0 | BLOCKED | BLOCKED | BLOCKED | NOT_MEASURED | NOT_MEASURED | No allocated runtime/project; common Humanoid input not yet generated |
| V-edit / R-edit | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | Controls must precede edits |
| C1 / C2 / C3 | NOT_MEASURED | NOT_MEASURED | BLOCKED | NOT_MEASURED | NOT_MEASURED | No allocated common source or return runtime |

No PASS, FAIL, LOSSY_ACCEPTABLE or UNSUPPORTED comparison conclusion is supported yet. Existing VAPB historical evidence is contextual only. Source packaging acquisition is verified, which does not establish runtime compatibility.

## UX measurement contract

Measure first installation separately from second/subsequent use. For each path, record: startup until usable UI; discrete user actions (click/menu command/drag/shortcut, consistent definition); conversion wall time; manual repair actions/time; total elapsed time including waits. Capture separate `operator=AI` and `operator=owner` measurements. No owner measurements exist here. Don't substitute CLI timings for human UX or count AI deliberation as conversion time. Record machine/resources and warm/cold state. First-use total includes installing providers; repeat starts with installed tools and identical closed-app state. Also report the already-open-Unity scenario separately without mixing it into the original package-entry goal. Timer rows currently all **NOT_MEASURED**, not zero.

Original goal has two separate judgments: does the route require Unity before Blender, and how much measured work is avoided? R's documented entry uses Unity Play Mode; VAPB PRODUCT_SPEC defines package-to-Blender entry without a user Unity preprocessing step. This workflow distinction is documented, but a speed advantage and owner preference remain unmeasured.

## Next minimum

Independent read-only review of this fixture/judge proposal, then parent allocation of a fresh slot/project. Generate only the one common synthetic input and run V0/R0. Detailed SoulFlame/NDMF implementation analysis waits until actual ABC results are saved; this preparation checkpoint does not satisfy that gate.

Independent review completed in a separate GPT-6.1 SOL / medium context: KEEP with bounded pre-execution corrections, applied to this preparation revision. Corrections define runtime Humanoid eligibility, concrete anchors, full influence capture, route-specific representation proof, and adaptation of the correspondence method rather than unchanged reuse of the old judge. Reviewer found no public-safety issue in these authored documents; no runtime work or file edits by reviewer. Final revised judge implementation still requires independent review if newly written. No additional fixture framework requested.

The 11:51 clarification was applied after that initial review. The same independent reviewer performed a bounded read-only follow-up of the changed r2 contract and public safety: KEEP, no blocking corrections. Review did not independently rehash downloaded archives or establish runtime success. No prior completed experiment is canceled or rerun by this amendment.
