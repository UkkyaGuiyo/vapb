# Previous Corpus Run Classification

The earlier multi-package run is classified as `MERGED_CORPUS / COLLISION_CONTEXT`, not `ISOLATED_PACKAGE`.

It remains useful as private evidence for cumulative AssetDatabase behavior, GUID reassignment, overwrite behavior, and package-order experiments. It must not be used as independent per-package semantics, identity ground truth, dependency-completeness evidence, clustering/training evidence, or automatic prefab evidence.

The analysis suite propagates observation context and marks merged/collision analysis as `CONTAMINATED_CONTEXT`. CLI validation and analysis fail closed by default unless the observation context is isolated and the package baseline/package hash are explicitly attested. Merged analysis requires the explicit `--allow-contaminated` research switch.
