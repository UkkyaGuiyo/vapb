# Worker Template

The worker template is a public, package-free Unity `2022.3.62f3` project.
It contains only the Oracle Editor harness, `Packages`, and relevant
`ProjectSettings`. It must not contain `Library`, `Temp`, `Obj`, `Logs`,
`UserSettings`, commercial assets, or prior observations.

`worker_template.py prepare` creates a new copy and an external manifest.
`worker_template.py check` verifies the template id, Unity version, file list,
sizes, and SHA-256-derived template hash. A worker attempt always copies this
template into a new workspace; no worker reuses another worker's project or
Library. The Supervisor checks the trusted template manifest before every
allocation and rejects drift or cache directories before creating the worker.
