from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def ingest_raw(source: str | Path, vault: str | Path) -> dict[str, Any]:
    source = Path(source)
    data = source.read_bytes()
    json.loads(data.decode("utf-8"))
    digest = hashlib.sha256(data).hexdigest()
    target = Path(vault) / "raw" / "sha256" / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != data:
        raise ValueError("INPUT_INVALID: content-addressed target differs")
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
    return {"rawSha256": digest, "vaultPath": str(target), "sourceBytes": len(data)}
