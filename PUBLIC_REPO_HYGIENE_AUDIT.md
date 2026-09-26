# Public repository hygiene audit

## Scope and status

This report supersedes the earlier current-tree-only assessment. That assessment did not establish that the reachable Git history was suitable for public release. The original private repository contained historical workstation paths, real asset identities and a binary fixture requiring a provenance decision.

The publication candidate is a separate reconstruction of all 110 source commits and 11 branch heads, starting at a new root. The original repository and a complete verified bundle remain private and unchanged. See [migration details](docs/PUBLIC_HISTORY_MIGRATION.md).

**Publication gate: PASS for the reviewed scope on 2026-09-26.** A scan with no credential-pattern matches is not a universal absence-of-secrets proof.

## Review categories

- All reachable commit trees, messages, author/committer metadata and branch names.
- Workstation paths, personal identifiers, private asset names/identity tables and raw structure dumps.
- Known real-package GUID/hash denylist and identifying prefixes; public shader and synthetic fixture IDs are assessed separately.
- Tracked binary assets, embedded binary data and uncertain redistribution provenance.
- Third-party implementation, attribution, copyright and the first-party GPL/MIT boundary.
- Production behavior preservation and synthetic fixture validity after path sanitization.

Private matched values and raw scan inputs are stored outside the public repository. Only aggregate findings and safe locations are published. Public Windows font defaults and synthetic path-rejection inputs are intentional path literals, not developer-machine dependencies.

## Ongoing policy

Keep private/commercial UnityPackages, extracted assets, exact identity tables and raw corpus dumps outside Git. Derive public synthetic regressions from generalized failures. Generic real-data probes accept an external path/environment variable and emit only approved aggregates for publication. Historical archive branches document earlier development; they are not supported releases or current product claims.

## Recorded final evidence

- Reconstructed history: 110/110 original commits retained; 111 commits including the license/migration preparation commit at `d01cd774cd49dc277ab2c4016f8f7be7f15f089d`.
- Independent graph check: zero changed parent relationships or author/committer date pairs, zero original commit objects reachable, 11 branch heads, zero public tags.
- Final fresh clone: 871 reachable blobs inspected by inventory; no credential-pattern matches, personal home paths or tracked binary asset extensions. Three absolute-path blob versions are intentional Windows font defaults or the synthetic `C:/outside.fbx` rejection input.
- Known corpus identifiers: zero confirmed private labels, known asset GUID/full hashes or checked eight-character prefix residues. Public/synthetic GUID references remain. `CaseA` is an intentional neutral pseudonym.
- Independent contextual review covered historical documents, source, commit messages, raw-record reductions and attribution, then verified the final reconstruction delta. Raw evidence and denylist values stay private.
- Historical syntax: 489 distinct Python blobs and eight PowerShell blobs parse. A sanitizer-induced historical regex break was found and repaired before publication.
- Ninety mapped runtime source files exactly match the last private checkpoint; latest changes are GPL/MIT notices, author attribution, license packaging and migration documentation. Four Unity helper files remain token-equivalent after comment headers.
- Fresh clone: 340 Python tests PASS, compileall PASS, Git fsck PASS; Blender 5.2.1 integration and register/unregister PASS with exit code 0. Receipt/binding rename/save/reopen assertions PASS.
- Distribution ZIP: all three license/scope files included, all three packaged helper sources carry complete MIT notices; 98 members. This validates packaging, not completion of every product acceptance criterion.

This is a scoped evidence-backed publication review. It cannot certify unknown facts outside the inspected history and supplied provenance. The owner attested the legacy helper's pre-Git first-party origin; no concrete contrary copy/derivation evidence was found.
