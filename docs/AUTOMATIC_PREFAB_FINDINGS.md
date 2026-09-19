# Automatic Prefab Findings

The previous automatic-restore evidence showed that selecting a helper prefab
and importing every FBX can produce a misleading success. It does not prove
semantic correctness. The new investigation records effective instantiated
structure and renderer coverage through public Unity APIs; it does not use
filename, object name, GUID order, first candidate, or all-FBX rules.

Automatic selection remains `UNVERIFIED` until the human-run corpus includes
candidate-order/name/GUID invariance and explicit ambiguity cases.

The first compliant smoke observation contained 15 Prefabs, 3041 observed
components, 311 SkinnedMeshRenderers, 102 unique mesh identities, and eight
coarse structural signatures. This is sufficient to begin structural-family
analysis, but not sufficient to select an avatar: the old observation lacked
compact Avatar validity, blendshape/bone/rootBone, nested-Prefab, and texture
property facts. The next probe adds those facts without using names or product
labels as predictive features.
