# Automatic Prefab Findings

The previous automatic-restore evidence showed that selecting a helper prefab
and importing every FBX can produce a misleading success. It does not prove
semantic correctness. The new investigation records effective instantiated
structure and renderer coverage through public Unity APIs; it does not use
filename, object name, GUID order, first candidate, or all-FBX rules.

Automatic selection remains `UNVERIFIED` until the human-run corpus includes
candidate-order/name/GUID invariance and explicit ambiguity cases.
