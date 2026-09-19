# Missing Dependency Classifier

Dependency evidence is classified by role: `STRUCTURAL_HARD`, `MATERIAL_BINDING`, `TEXTURE_VISUAL`, `SHADER_PROVIDER`, `SOURCE_IDENTITY`, or `UNKNOWN`. Resolution states remain `OBSERVED_RESOLVED` or `OBSERVED_UNRESOLVED` unless a later observation provides stronger evidence.

The analysis suite does not infer a commercial package provider from names, paths, numeric GUID order, or heuristics. Unknown and ambiguous cases generate a proposed next experiment.
