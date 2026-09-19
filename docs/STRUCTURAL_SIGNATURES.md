# Structural Signatures

Structural signatures are versioned and deterministic. Prefab signatures include component-type counts, avatar evidence, skinned-renderer counts, material-slot counts, mesh counts, blendshape counts, bone references, and root-bone evidence. Skeleton and mesh signatures are separate because their coverage and confidence differ.

Signatures are comparison evidence, not proof of semantic equivalence. A tie is reported as `MULTIPLE_VALID_VARIANTS`; distinct classes are `USER_CHOICE_REQUIRED`.
