# Identity Model

Canonical entities are typed (`prefab`, `object`, `mesh`, `material`, `texture`, and source assets). Edges preserve containment, material binding, texture reference, mesh use, source identity, and original-source identity separately.

Observed identity is retained only in private evidence. Derived structural signatures never use names, paths, GUID values, or input ordering as classification signals. Missing identity is represented as unknown rather than guessed.
