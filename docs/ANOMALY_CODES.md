# Analysis Anomaly Codes

`IDENTITY_COLLISION` means incompatible observed objects share an identity token.

`MAT_SLOT_EMPTY` means a renderer material slot was observed without a material reference.

`MAT_TEXTURE_REFERENCE_UNRESOLVED` means a material texture property was observed without a resolvable texture identity.

`PROPERTY_REFERENCE_UNRESOLVED` means a prefab property modification was not resolved by the public Unity observation API.

Codes describe evidence and do not silently convert unknowns into failures.
