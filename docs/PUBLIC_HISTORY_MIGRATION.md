# Public history migration

## Authority and preservation

The owner authorized `UkkyaGuiyo/vapb` as the public development authority. The former `UkkyaGuiyo/unitypackage_blender_importer` remains private, preserving the complete original history, private development records and recovery source. No reset, history rewrite, deletion or force push was performed against it.

The last private checkpoint is `600d498ece6f9e87d9aa177a236269ad53574192`. A separate complete `git bundle --all` was created and verified before migration; its private storage and raw audit records are not published. The bundle SHA-256 is `4e5c10cf251052f11b4dda8a46f205d42b232d9f369521fe36d0de814b6a7795`.

## History retained

- Earliest source commit: `dbfdc0f88e8c0f17c732f4e14c373a45b1b672ce`.
- New public root: `3d9c418887560b4a8c0534059014c5643c963f79`. No original commit is an ancestor.
- Reconstructed checkpoint before licensing and migration documentation: `0ec1f247c588c22d9f0e5beca487c3620bea5119`.
- **110 of 110 original commits retained**, including side branches and empty historical commits; no whole-history squash.
- Parent relationships and author/committer dates are retained through the old-to-new mapping. Six commit messages were rewritten to remove private case wording while retaining their technical intent.
- Two original author/committer identities use stable contributor aliases. The private alias mapping is retained only with the archive.
- Ten historical branch heads are retained under `archive/`; current development remains `feature/multi-package-identity`.
- No tag or Release was created. The original annotated tag remains in the private archive; its target commit is already included through retained branches.
- [Commit correspondence](PUBLIC_HISTORY_COMMIT_MAP.csv) records only commit hashes, without private asset identifiers.

## Sanitization and exclusions

Historical developer paths and private case labels were replaced with portable configuration or neutral labels. Source helper inputs that formerly used workstation paths now require explicit environment variables. Public platform defaults and synthetic absolute-path rejection inputs are retained where needed to preserve behavior.

Narrative design, failures, fixes and test transitions remain in chronological history. Raw experiment records were reduced to safe aggregates where the original included real asset identities or structure. Twelve paths were excluded: eleven raw experiment/identity JSON files and one historical FBX binary whose source provenance was not sufficiently established for redistribution. No original commit was removed solely because one of its files needed sanitization.

Known private GUIDs/hash values and their identifying prefixes were removed. Public shader identifiers and synthetic fixture identifiers were retained. Five ambiguous historical build digest values were omitted from published records; the complete evidence remains in the private archive. Their absence does not change test logic or production behavior.

Historical sanitized reports are evidence summaries, not independently reproducible private fixtures. They do not include the private input data, raw identity tables or original machine layout.

## Licenses and attribution

The owner selected **GPL-3.0-or-later** for the Blender/Python project and **MIT** for independent first-party `unity_editor/` helpers. See [LICENSES.md](../LICENSES.md). The owner confirmed that the legacy Material Restore helper was newly implemented with AI assistance for VAPB before the first Git commit. The code/history independence and third-party attribution audit passed before publication; contrary concrete evidence must stop MIT application to the affected code.

## Publication gate and validation

Independent all-ref source/license and private-data reviews passed, including the corrected historical regex and final delta review. A separate fresh clone passed 340 Python tests, compileall, Git fsck and Blender 5.2.1 integration (exit 0, including register/unregister and rename/save/reopen receipt checks). Its distribution ZIP includes three license/scope files and full MIT notices in all three packaged helpers. The tested preparation commit is `d01cd774cd49dc277ab2c4016f8f7be7f15f089d`. See the [scoped audit](../PUBLIC_REPO_HYGIENE_AUDIT.md). Publication completed at https://github.com/UkkyaGuiyo/vapb. GitHub reports PUBLIC visibility and default branch `feature/multi-package-identity`. All 11 remote branch heads matched the audited local branches at the first published checkpoint `58993a3cbc4711572f97c04e886568bedf725bc6`; an unauthenticated Git read also returned all 11 heads. The original private repository was independently confirmed PRIVATE at unchanged checkpoint `600d498ece6f9e87d9aa177a236269ad53574192`. No force push, tag, Release or main merge was performed.

The pre-migration private checkpoint has 340 Python tests passing, compileall passing, synthetic file-backed/packed Texture edit/save/reopen/export and fresh Unity public-API restoration passing. Migration introduces no production behavior change. The distribution builder includes the license texts and scope notice; helper source includes the complete MIT notice in generated UnityPackages. These earlier results must not substitute for tests of the reconstructed checkout.

## Exact Core resumption point

After publication, use the public repository to verify an authorized real Avatar's selected, bound Texture edit through save/reopen, UnityPackage export and fresh Unity restoration, while preserving the original corpus archive. Then continue the multiple-real-package Core roundtrip priorities in PRODUCT_SPEC.md. Private/commercial files, raw dumps and identity tables remain outside Git. Avatar-wide roundtrip and VRChat build/runtime acceptance remain incomplete.

## Continuing development

Normal development now uses **[UkkyaGuiyo/vapb](https://github.com/UkkyaGuiyo/vapb)** on `feature/multi-package-identity`. The original private repository is an intact historical archive and recovery source. Work resumes from the tested working-Texture export implementation, with an actual authorized Avatar Texture edit/save/reopen/export/fresh-Unity check next. No private corpus file was imported into this public repository by the migration.
