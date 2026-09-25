"""Texture materialization helpers with an explicit no-transcode default."""

from __future__ import annotations

from .staging import StagedUnityAsset, normalize_guid


def materialize_texture(
    *,
    guid: str,
    pathname: str,
    asset_bytes: bytes,
    meta_bytes: bytes,
    strategy: str = "PRESERVE_VERBATIM",
) -> StagedUnityAsset:
    """Create a staged texture without changing its encoded payload.

    Texture decoding/transcoding is intentionally outside this helper.  A
    caller that wants an edited texture must provide the resulting bytes and
    choose an explicit strategy; the default is exact raw preservation.
    """
    normalized_guid = normalize_guid(guid)
    if strategy not in {"PRESERVE_VERBATIM", "GENERATE_EXPLICIT"}:
        raise ValueError(f"unsupported texture materialization strategy: {strategy}")
    return StagedUnityAsset(
        guid=normalized_guid,
        pathname=pathname,
        asset_bytes=asset_bytes,
        meta_bytes=meta_bytes,
        asset_type="Texture2D",
        operation="PRESERVE" if strategy == "PRESERVE_VERBATIM" else "CREATE",
        strategy=strategy,
    )
