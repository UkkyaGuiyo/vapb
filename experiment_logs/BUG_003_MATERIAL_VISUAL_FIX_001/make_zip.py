import os
import zipfile
from pathlib import Path

root = Path(r"<LOCAL_PATH>")
out = Path(r"<LOCAL_PATH>")
tmp = Path(str(out) + ".tmp")
files = [p for p in root.rglob("*") if p.is_file() and "experiment_logs" not in p.relative_to(root).parts and "__pycache__" not in p.relative_to(root).parts and p.suffix.lower() != ".pyc"]
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, Path(root.name) / path.relative_to(root))
os.replace(tmp, out)
with zipfile.ZipFile(out) as archive:
    print(len(archive.namelist()), archive.testzip(), all(name.startswith(root.name + "/") for name in archive.namelist()))
