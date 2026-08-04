"""Resource usage snapshot APIs (internal, no UI)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.config import ROOT

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    gpu_memory_free_gb: float | None = None
    gpu_memory_total_gb: float | None = None
    ram_percent: float | None = None
    cpu_percent: float | None = None
    vector_db_bytes: int = 0
    model_name: str = ""
    plugin_count: int = 0
    task_count: int = 0
    memory_count: int = 0
    history_bytes: int = 0
    extra: dict[str, float | int | str] = field(default_factory=dict)


def capture_resource_snapshot() -> ResourceSnapshot:
    snap = ResourceSnapshot()
    try:
        import torch

        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            snap.gpu_memory_free_gb = free / (1024**3)
            snap.gpu_memory_total_gb = total / (1024**3)
    except Exception:
        pass

    try:
        import psutil

        snap.cpu_percent = psutil.cpu_percent(interval=0.05)
        snap.ram_percent = psutil.virtual_memory().percent
    except Exception:
        pass

    try:
        from core.chroma import get_chroma_path

        chroma_path = Path(get_chroma_path())
        if chroma_path.is_dir():
            snap.vector_db_bytes = sum(
                f.stat().st_size for f in chroma_path.rglob("*") if f.is_file()
            )
    except Exception:
        pass

    try:
        from core.config import load_settings

        snap.model_name = load_settings().get("MODEL_NAME", "")
    except Exception:
        pass

    try:
        from plugins.manager import list_plugin_status

        snap.plugin_count = len(list_plugin_status())
    except Exception:
        pass

    try:
        from agents.tasks.task_manager import _global_tracker

        snap.task_count = 0 if _global_tracker.idle else 1
    except Exception:
        pass

    try:
        from core.index_status import COLLECTION_MEMORY
        from core.chroma import collection_count

        snap.memory_count = collection_count(COLLECTION_MEMORY)
    except Exception:
        pass

    history = ROOT / "data" / "history" / "chat.jsonl"
    if history.is_file():
        snap.history_bytes = history.stat().st_size

    return snap
