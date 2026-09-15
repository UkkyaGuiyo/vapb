from __future__ import annotations

import io
from pathlib import Path
import shutil
import tarfile
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor
from queue import SimpleQueue
from threading import Event
from types import SimpleNamespace

import bpy


REPO_ROOT = Path(r"<LOCAL_PATH>")
import sys

sys.path.insert(0, str(REPO_ROOT))

from unitypackage_blender_importer.blender.performance import PerformanceTimer
from unitypackage_blender_importer.operators.import_unitypackage import UNITYPACKAGE_OT_import


class FakeWindowManager:
    def event_timer_add(self, _interval, window=None):
        return object()

    def event_timer_remove(self, _timer):
        return None


class FakeContext:
    window_manager = FakeWindowManager()
    window = object()


def make_package(path: Path) -> None:
    with tarfile.open(path, "w:gz") as archive:
        payload = b"minimal fbx payload"
        for name, data in (("asset", payload), ("pathname", b"Assets/Avatar.fbx")):
            info = tarfile.TarInfo(f"{'a' * 32}/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


with tempfile.TemporaryDirectory() as temp:
    package = Path(temp) / "smoke.unitypackage"
    make_package(package)
    operator = SimpleNamespace(
        _performance=None,
        _prepared_package_key=None,
        _extraction_dir=None,
        _extraction=None,
        _asset_db=None,
        _fbx_paths=[],
        _prefab_paths=[],
        _prepare_executor=None,
        _prepare_future=None,
        _prepare_timer=None,
        _prepare_window_manager=None,
        _prepare_cancel=Event(),
        _prepare_events=SimpleQueue(),
        _progress_active=False,
        report=lambda *_args, **_kwargs: None,
    )
    operator._prepare_worker = UNITYPACKAGE_OT_import._prepare_worker.__get__(operator)
    operator._set_phase = lambda *_args, **_kwargs: None
    operator._start_async_prepare = UNITYPACKAGE_OT_import._start_async_prepare.__get__(operator)
    operator._stop_async_prepare = UNITYPACKAGE_OT_import._stop_async_prepare.__get__(operator)
    operator._performance = PerformanceTimer()
    started = time.perf_counter()
    operator._start_async_prepare(FakeContext(), package)
    start_latency = time.perf_counter() - started
    prepared = operator._prepare_future.result(timeout=30)
    operator._stop_async_prepare()
    if start_latency >= 1.0:
        raise RuntimeError(f"async preparation start blocked for {start_latency:.3f}s")
    if prepared.extraction is None or not prepared.fbx_paths:
        raise RuntimeError("async preparation did not return the prepared asset index")
    if prepared.extraction_dir is not None:
        shutil.rmtree(prepared.extraction_dir, ignore_errors=True)
    print(f"ASYNC_PREPARE_START_LATENCY={start_latency:.3f}s")
    print("ASYNC_PREPARE_WORKER_OK")

bpy.ops.wm.quit_blender()
