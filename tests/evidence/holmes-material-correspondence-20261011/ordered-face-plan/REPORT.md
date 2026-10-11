# HOLMES-20261011-02 result

**The ordered-pair candidate matched all six faces and their exact receiver Material references. A diagnostic Blender copy reproduced those references with four Object-linked slots; original snapshots stayed unchanged. Standard product restoration remains unimplemented.**

## Instruction, scope and saved source

- Instruction ID `HOLMES-20261011-02`, status at retrieval `READY`; instruction commit `02c51d6cda52bb912a0afc2c2f804e9ca09a8ac5`, blob `8b47a2e9624c51ccac1b2b4cf595ef9fa92cea63`. [Fixed instruction](https://github.com/UkkyaGuiyo/vapb/blob/02c51d6cda52bb912a0afc2c2f804e9ca09a8ac5/HOLMES_TO_WATSON.md).
- Project VAPB, canonical repository `UkkyaGuiyo/vapb`, branch `feature/holmes-ordered-face-plan-20261011`, start SHA `e09c2ee31b83e22a8fc77dd850961e9fe1be7c76`. Isolated checkout root name `vapb-material-audit`; public evidence root is this directory.
- Source/fixture/result commit [51877222c8b8b5b93b5436415af5bb2495c80729](https://github.com/UkkyaGuiyo/vapb/commit/51877222c8b8b5b93b5436415af5bb2495c80729). Reporting is a separate subsequent commit. Local commit is not a remote-persistence claim; final task response supplies verified remote links.
- Common AGENTS SHA256 `9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`; actual common/repo instructions and relevant PRODUCT_SPEC material/final-state clauses were reread. Existing relevant Atlas lessons were read; parent restriction kept the Atlas read-only.
- Previous HOLMES OFF/ON measurements and reviews were not rerun. OnlyYou coordination is excluded by the latest human direction. No product code, guards, witness schema, specs, AGENTS, main/dev or Release changed.

## Input-only implementation and freeze

[candidates.py](candidates.py) uses first appearance of `(actual Material UID, declared effective topology)` within the decoded Model/Geometry. Repeated pairs reuse an ordinal; UID alone is not a group identity. Keep Quads OFF preserves raw quads but predicts effective Triangles without predicting diagonals/index order. Missing/invalid settings, references, unsupported polygon/index/fingerprint scope are refused.

[freeze_input.py](freeze_input.py) reuses the existing official FBX parser/decoder, Prefab YAML parser, direct occurrence projection and canonical PackageIdentity. Receiver refs keep package/GUID/signed fileID, provider revisions, FBX/meta revisions, and actual Mesh/Renderer/occurrence identity separately. Receiver length/null/provider/scope/revision errors remain explicit. The output stays `CANDIDATE`, `ready_to_apply=false`, and source binding `UNPROVEN` even after this experiment.

One newly exported self-authored six-face input retained raw order `[3,4,4,3,3,4]`, UIDs `[26834720,505943850,26834720,505943850,26834720,505943850]`, Model UID `768679554`, Geometry UID `799089120`. All 21 UV corners are unique small binary fractions. Scope is disconnected, axis-aligned planar convex faces, one static Model/Geometry, unique Material connections and active Layer0. No purchased/third-party assets are included. Fixture UV rules are diagnostic conditions, not a product input requirement.

Creation used actual Mesh and asset identities to build one direct Prefab with four author-fixed distinct external refs. It did not query native faces, indices, topology, submesh count or group order to choose the array. Six assets and their twelve asset/meta payloads were frozen with predictions at **08:59:36.797163 UTC**, before native face capture began **09:00:24.6449477 UTC**. See [creation.json](creation.json), [input-and-predictions.json](input-and-predictions.json), [OrderedSix.unitypackage](OrderedSix.unitypackage).

| Frozen input | SHA256 |
|---|---|
| FBX | `d9b6b443af0aafbd175b7ed05ab804f78c76f589378d5b83e1c7af26b562c506` |
| FBX meta | `abe596e605b91137f4f86eb5e5826a276b338c83e52e88cfb902d769af145c96` |
| Receiver Prefab | `80d1362d24b338645a77fa475b00c9e7dea4afa63b54dc5b699c63fdadcbe104` |
| UnityPackage | `5492475a7231ba21d6f4c20308e2db84865df7e08770aa5c4bd9fd84f7064dcf` |
| Candidate source | `d4c0312ea59f570d0bf721340a3e8cf15eb947b183966d57eae1f5863e75aebd` |

All provider/meta and final/actually executed source hashes are in [run-summary.json](run-summary.json). Frozen prediction code hashes describe the pre-holdout versions; final code and original executed Capture/apply sources are retained separately. Thirty source/frozen Git blob hashes were checked against recorded hashes before source commit, with zero mismatches. Unity-generated trailing spaces and exact CRLF bytes were preserved rather than rewriting frozen inputs.

## Independent native judgment

Unity **2022.3.22f1**, Keep Quads ON only; full effective importer policy, all topology/indices/baseVertex, UV, vertices/normals, Model and Prefab refs are retained in [native.json](native.json). `GetIndices(true)` was crosschecked against unadjusted indices plus baseVertex. Native group order was not rearranged. The independent judge reuses immutable exact corner/edge cover and membership functions; it never imports the prediction function as an oracle.

| Hypothesis | Fixed prediction | Classification |
|---|---|---|
| PAIR_FIRST | 4 groups A/T, B/Q, A/Q, B/T; repeats return to first pair | **SUPPORTED_IN_THIS_FIXTURE**: all six group/topology/ref rows match |
| PAIR_RUN | 6 groups; faces 4/5 start new groups | **FALSIFIED**: faces 4/5 and group count differ |
| UID_FIRST | 4 groups A/T, A/Q, B/Q, B/T | **FALSIFIED**: faces 1/2/5 differ despite equal count |

All references below use package `sha256:5492475a7231ba21d6f4c20308e2db84865df7e08770aa5c4bd9fd84f7064dcf` and fileID `2100000`. Names R0–R3 are explanatory labels; judgment uses identities.

| Ref | Actual Material GUID |
|---|---|
| R0 | `afd253dd071f7e5469e24392cdbf181c` |
| R1 | `70c1cb3bd3a723141a677eca237e252c` |
| R2 | `242d369718abeb942873ec054737cf94` |
| R3 | `4d7af3be41387054c9f86b68e180d9e7` |

| Raw face | Raw UID / topology | Candidate group | Actual group | Actual receiver ref | Copy actual ref |
|---|---|---:|---:|---|---|
| p0 | 26834720 / Triangles | 0 | 0 | R0 | R0 |
| p1 | 505943850 / Quads | 1 | 1 | R1 | R1 |
| p2 | 26834720 / Quads | 2 | 2 | R2 | R2 |
| p3 | 505943850 / Triangles | 3 | 3 | R3 | R3 |
| p4 | 26834720 / Triangles | 0 | 0 | R0 | R0 |
| p5 | 505943850 / Quads | 1 | 1 | R1 | R1 |

Membership and exact reference comparison **PASS**. All six winding comparisons are **−1**, reported separately. Position equality and render **NOT_RUN**. No general importer-algorithm guarantee or standard product PASS is claimed. Full comparisons: [judgment.json](judgment.json).

The review identified missing contemporaneous receiver-Mesh and Material/meta hash capture. One **metadata-only** supplemental run at **09:02:52–09:03:08 UTC** verified twelve frozen hashes, actual receiver Mesh, fixed references and full policy against the earlier frame. It queried no face/index/topology information. These revisions are evidence from the later verification interval; Material-byte/render fidelity during the initial face interval is not claimed. The package's twelve unique payloads independently matched the frozen assets. See [supplement.json](supplement.json).

Actual model/receiver Mesh: GUID `d6f28bcc59f94dbeba9883a9c79a0e03`, signed fileID `-7487798873075540560`. Model Renderer signed fileID `-7511558181221131132`. Receiver Prefab GUID `983dd9d36c5824d488269d7d6d6f0434`, Renderer fileID `9090392177786753814`.

## Explicit Blender copy

Blender **5.2.1 LTS** normal UnityPackage Import **PASS**. The first attempt stopped before copy mutation: the experimental selector omitted receiver root context and did not obtain a unique receipt-selected realization. Its exact code and [NOT_RUN record](apply-first-attempt.json) remain preserved; candidate count was not logged and is not reconstructed as a fact. Reading the product source confirmed it retains source templates and receipt-bearing member copies. A focused RED→GREEN control protects selection using the actual occurrence root context, rejects zero/duplicate scoped candidates, and distinguishes an unscoped template from the actual member.

One corrected attempt resolved the actual receiver occurrence first, then uniquely selected its real package/hash/GUID/Model/Geometry receipt. All four real Material datablocks had exact package/GUID/fileID and provider byte revisions. The diagnostic UV exact-cover join connected source raw faces to actual Blender faces. A new Object and independent Mesh received four OBJECT-linked slots and face material indices `[0,1,2,3,0,1]`; every actual face provider matched the independent native result. Thus one raw A UID yielded R0 on triangles and R2 on quads, rather than a two-slot reorder.

Copy application **PASS / DIAGNOSTIC_ONLY**. Original Object/Mesh geometry, UV, indices, slot links, custom metadata, Material states and extracted source files stayed unchanged. Original before/after digest: `5f9eaf11a80323fb9172176a9188a0c6af407e15f4e0704eaa87d44d707bd987`. See [apply.json](apply.json). Copied `_vapb_` claims were stripped; no new EXACT receipt or product binding was fabricated. Source binding remains `UNPROVEN_FOR_PRODUCT`. Standard Confirm, export, saved GUI scene and render **NOT_RUN**.

## Verification, preservation and review

- Focused controls **7/7 PASS**: noncontiguous pair reuse, mixed topology per UID, invalid settings/reference/index/topology, array length/null/provider/scope/revision, same-count group/ref swaps, missing/duplicate native faces, supplemental hash/Mesh mismatch, root-scoped receipt uniqueness. Input-only code executes with no observation files in its test directory.
- One fixture generation and **one native face capture**, one metadata-only supplement, two copy attempts (first NOT_RUN; unfinished stage corrected once). No new input was generated to fit a hypothesis.
- Every owned Unity phase exited normally with code 0 and preserved **3041 preexisting files**, changed=0, unexpected=0. Leases and shared mutex were released; no other Editor was stopped or lock deleted. Both owned Blender attempts exited 0 with no owned child and mutex released. Private logs/host paths were not published.
- Independent generation/prediction and native judgment review contexts used **GPT-6.1 SOL / medium**, KEEP. Native reviewer also read the narrow root-context correction and successful result: KEEP. Actual primary model/reasoning was unavailable. [Review record](REVIEW.md).
- No blocked required stage remains for this instruction. Formal usage was 98% remaining at final check; no reset was used.

## Minimum next product connection

Native correct assignment exists, the input-only candidate matches, and explicit diagnostic application works. **Standard VAPB automatic restoration is a separate unimplemented step.**

The smallest subsequent product patch is to feed a bounded ordered partition candidate into the existing `_material_plan`/slot application path only when actual Mesh/occurrence/provider identity, source revision, accepted importer-policy scope and source-to-realized-face connection are proven. Reuse existing receipt creation to retain the actual imported face/corner relation needed by that path; do not make this fixture's unique UV fingerprints a universal user requirement. Keep the current refusal for missing/conflicting policy/revision/face evidence. The raw UID may need multiple final slots, so the patch must assign polygon material indices on an independent/Object-linked realization rather than only reorder source slots. This report authorizes no guard removal or product patch and requires no new resolver/witness framework or exhaustive all-input proof.
