# Public repository hygiene audit

## Scope and status

This report supersedes the earlier current-tree-only assessment. That assessment did not establish that the reachable Git history was suitable for public release. The original private repository contained historical workstation paths, real asset identities and a binary fixture requiring a provenance decision.

The publication candidate is a separate reconstruction of all 110 source commits and 11 branch heads, starting at a new root. The original repository and a complete verified bundle remain private and unchanged. See [migration details](docs/PUBLIC_HISTORY_MIGRATION.md).

**Publication gate: PENDING independent final review and fresh-clone verification.** A scan with no credential-pattern matches is not a universal absence-of-secrets proof.

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
