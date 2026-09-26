"""Deterministic UnityPackage tar.gz writer."""

from __future__ import annotations

from pathlib import Path
import gzip
import io
import os
import tempfile
import re
import tarfile

from .staging import StagingTree


class UnityPackageWriter:
    """Serialize only an already validated StagingTree; no Blender semantics."""

    _ENTRY_ORDER = ("asset", "asset.meta", "pathname", "preview.png")

    def write(self, tree: StagingTree, output_path: Path) -> Path:
        output_path = Path(output_path)
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite UnityPackage: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Publish only a closed archive. Linking in the same directory is
        # atomic and refuses an existing destination, including a racing writer.
        # Filesystems without hard-link support fail closed instead of falling
        # back to an overwrite or exposing incomplete final output.
        descriptor, name = tempfile.mkstemp(prefix=".vapb-", suffix=".tmp", dir=output_path.parent)
        os.close(descriptor)
        temporary = Path(name)
        try:
            with temporary.open("wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                        for entry in tree.entries:
                            is_folder = bool(re.search(rb"(?m)^folderAsset:\s*yes\s*$", entry.meta_bytes))
                            payloads = {
                                "asset.meta": entry.meta_bytes,
                                "pathname": entry.pathname.encode("utf-8"),
                            }
                            if not is_folder:
                                payloads["asset"] = entry.asset_bytes
                            if entry.preview_bytes is not None:
                                payloads["preview.png"] = bytes(entry.preview_bytes)
                            for name in self._ENTRY_ORDER:
                                payload = payloads.get(name)
                                if payload is None:
                                    continue
                                info = tarfile.TarInfo(f"{entry.guid}/{name}")
                                info.size = len(payload)
                                info.mode = 0o644
                                info.mtime = 0
                                info.uid = 0
                                info.gid = 0
                                info.uname = ""
                                info.gname = ""
                                archive.addfile(info, io.BytesIO(payload))
            os.link(temporary, output_path)
        finally:
            temporary.unlink(missing_ok=True)
        return output_path
