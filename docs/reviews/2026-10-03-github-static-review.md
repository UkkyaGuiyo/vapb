# VAPB GitHub static code review — 2026-10-03

## Scope and status

- Reviewed source: `7c4c4e70d151b7ad7c6e91235a1726001a3e0a27`, branch `feature/multi-package-identity`.
- Method: read-only inspection of public GitHub source, producer/consumer paths, relevant tests, product decisions, and Failure Atlas guidance.
- Status: **REVIEW FINDINGS OPEN — NO FIXES APPLIED**.
- This document records a review; it does not authorize implementation, campaign resumption, merge, or release.
- No Unity/Blender runtime, fresh end-to-end reproduction, or full regression suite was run for this review. Historical 571 PASS is not a result of this review.
- Coverage focused on package extraction/indexing, downstream import, Python export/staging, and Unity finalizers. This is not a complete audit of every repository file or a guarantee of security/correctness.
- No private corpus, private identities, machine paths, purchased assets, or raw private logs are included.

Severity is review prioritization: P1 = address before relying on the affected workflow; P2 = concrete correctness/recovery defect with narrower triggers. All findings below need focused regression reproduction before implementation.

## R1 — P1: Rejected archive paths re-enter the import pipeline through the asset index

**Evidence:** [asset_database.py lines 47–70](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity/asset_database.py#L47-L70), [import preparation lines 578–609](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/operators/import_unitypackage.py#L578-L609), [selected database construction lines 1232–1243](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/operators/import_unitypackage.py#L1232-L1243).

The extractor rejects absolute/traversal pathnames, but `AssetDatabase.from_package_index` falls back to `Path(root) / record.unity_path` when there is no extracted asset. It does not apply the extractor's containment validation. `add` registers an existing file into suffix caches.

Trigger: an archive record names a readable, pre-existing supported file outside the extraction root. A rejected Prefab can reach candidate parsing during preparation. RAW_FBX selection and the final database similarly allow an external FBX path to reach the import wrapper.

**Impact:** unintended local file reading/import outside the extraction boundary. This review does **not** establish external transmission, external file overwrite, or code execution. It requires an existing readable file at a known or predictable path.

**Correction direction:** validate index paths before they can become filesystem entries; retain rejected/missing records only as non-readable unresolved metadata. Do not let extraction warnings recreate readable external entries.

**Regression:** create an outside-root synthetic Prefab/FBX and an archive pathname pointing to it; build the index, perform selective extraction, construct the database, and prove no downstream reader/importer receives that file. Existing [extraction tests](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/tests/test_package_reader.py#L103-L120) stop at extraction rejection and do not test index-to-database fallback.

## R2 — P1: Final-state material restoration assumes native submesh order equals Blender slot order

**Evidence:** [recipe slot indices](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/export/final_state_package.py#L228-L229), [Finalizer length check and assignment](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity_editor/Editor/VapbFinalStateFinalizer.cs#L321-L345).

The final-state route records Blender slot indices, exports original material handles without transport labels, checks the imported material-array length, and then assigns materials in the original slot order. Equal lengths do not establish the same face-to-material correspondence.

Trigger: native import permutes submesh/material order. The repository already contains a relevant unskinned control: [fixture](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/tests/blender_geometry_abcd_fixtures.py#L45-L55) uses three face slots (0,2,1); [checked-in measurements](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/tests/unity_geometry_abcd_probe/production_triangle_measurements.json#L1357-L1386) report numeric SUBMESH_TOPOLOGY_MISMATCH while material_identity_partitions is EXACT. This is evidence that index order and material identity can diverge, **not a fresh end-to-end reproduction of this final-state defect**.

**Impact:** when that permutation occurs, replacing the correctly associated imported materials with the source-order array can attach materials to the wrong faces while reporting completion. Single-material or order-preserving cases are not affected by this particular trigger.

**Correction direction:** carry exact material identity labels through disposable export copies and resolve actual imported submesh correspondence before assigning preserved materials. Use existing model-skin transport handling as a reference, not as proof the final-state route already does this.

**Regression:** adapt the existing static three-material control to final-state package plus Finalizer; assert face-to-material identity after first and repeated Apply, not just material count.

## R3 — P2: Rollback verification can prevent restoration of original importer metadata

**Evidence:** [RunWitness cleanup](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity_editor/Editor/VapbModelSkinFinalizer.cs#L808-L872), especially lines 855–870.

RunWitness can enable `isReadable` and save/reimport a source FBX. In cleanup it restores source bytes and comparison metadata, then calls ImportAsset/Capture/metadata reads before restoring `originalMeta`. If one of those operations throws, the catch rejects immediately and skips the original metadata write.

**Impact:** a rejected operation can leave source importer metadata at the temporary readable configuration even though the source payload bytes were restored. This is a concrete exception-path ordering defect; no Unity exception-injection run was performed here.

**Correction direction:** ensure restoration of original source bytes and original metadata is attempted in an independent guaranteed cleanup path; keep restoration attempts separate from semantic verification failures and report both.

**Regression:** inject a failure between intermediate restore import and the final original-meta write. Assert byte-for-byte restoration of both source FBX and .meta, including a source initially marked unreadable.

## R4 — P2: Duplicate archive destination paths silently overwrite and alias distinct GUIDs

**Evidence:** [extraction publication loop](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity/package_reader.py#L279-L312).

Distinct GUID records targeting the same output pathname are not preflighted for collisions. Sorted GUID publication calls `os.replace`, overwriting the earlier payload, and returns both assets. Both GUID entries can then point to the final payload. If the overwriting entry has no metadata, payload/metadata pairing can also become inconsistent.

**Trigger/impact:** malformed or conflicting package entries can silently substitute one asset for another rather than failing clearly. This does not imply ordinary valid packages always collide.

**Correction direction:** preflight canonical destination identity before publishing any records; reject duplicate destinations and relevant file/directory or metadata-path conflicts explicitly. Do not silently choose a winner.

**Regression:** use two distinct GUIDs and payloads with one output path; require an explicit collision result and no successful aliased asset records. Include platform case-normalization and asset/.meta conflicts as additional boundary tests.

## Additional smaller finding — R5, P2: Uppercase GUID directories fail selective extraction

[build_index](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity/package_reader.py#L168-L171) and [selective selection](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity/package_reader.py#L338-L346) normalize GUID keys to lowercase, while [stream lookup](https://github.com/UkkyaGuiyo/vapb/blob/7c4c4e70d151b7ad7c6e91235a1726001a3e0a27/unity/package_reader.py#L250-L255) uses the archive GUID unchanged.

An accepted uppercase A–F GUID directory therefore indexes successfully but misses its extraction state, yielding missing pathname/omitted asset. Full extraction and selective extraction behave differently.

Normalize consistently at the stream boundary and add uppercase/mixed-case GUID regression cases. This is an extra smaller finding beyond the four principal issues summarized in the user report.

## Deliberately not counted as new bugs

- Documented STOPPED / INCOMPLETE campaign state, known Finalizer topology/layout refusal, and unmeasured real target parity.
- Intentional unsupported-input rejection.
- Legacy ReferenceFinalizer Cloth concern: its producer rejects Cloth/unsupported component classes, so no supported-route defect was established.
- Passing historical tests do not invalidate these findings, but these findings likewise do not prove the entire product is broken.

## Next review gate

Reproduce each finding with public synthetic cases, distinguish code defect from intended rejection, implement only after authorization, and verify the final revision. Preserve source identity and Bone/Cloth guards. Continue keeping private/commercial evidence outside this public repository.
