"""Production health checks for doctor and monitoring."""

from __future__ import annotations

import logging
import platform
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from core.config import ROOT, load_settings
from deployment.config import get_config

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    details: list[str] = field(default_factory=list)


def _check_memory_db() -> HealthCheckResult:
    details: list[str] = []
    status = HealthStatus.HEALTHY
    try:
        from core.chroma import get_chroma_path, collection_count
        from core.index_status import COLLECTION_MEMORY

        path = get_chroma_path()
        details.append(f"path={path}")
        count = collection_count(COLLECTION_MEMORY)
        details.append(f"memories={count}")
    except Exception as exc:
        status = HealthStatus.DEGRADED
        details.append(str(exc))
    return HealthCheckResult("memory_db", status, details)


def _check_vector_db() -> HealthCheckResult:
    try:
        from core.chroma import get_chroma_path

        get_chroma_path()
        return HealthCheckResult("vector_db", HealthStatus.HEALTHY, ["Chroma reachable"])
    except Exception as exc:
        return HealthCheckResult("vector_db", HealthStatus.UNHEALTHY, [str(exc)])


def _check_models() -> HealthCheckResult:
    model = load_settings().get("MODEL_NAME", "").strip()
    if model:
        return HealthCheckResult("models", HealthStatus.HEALTHY, [model])
    return HealthCheckResult("models", HealthStatus.DEGRADED, ["MODEL_NAME not set"])


def _check_plugins() -> HealthCheckResult:
    try:
        from plugins.manager import list_plugin_status

        rows = list_plugin_status()
        enabled = sum(1 for r in rows if r.enabled)
        return HealthCheckResult("plugins", HealthStatus.HEALTHY, [f"registered={len(rows)}", f"enabled={enabled}"])
    except Exception as exc:
        return HealthCheckResult("plugins", HealthStatus.DEGRADED, [str(exc)])


def _check_voice() -> HealthCheckResult:
    try:
        from voice.deps import voice_capture_available, voice_stt_available, voice_tts_available

        parts = [
            f"capture={voice_capture_available()}",
            f"stt={voice_stt_available()}",
            f"tts={voice_tts_available()}",
        ]
        return HealthCheckResult("voice", HealthStatus.HEALTHY, parts)
    except Exception as exc:
        return HealthCheckResult("voice", HealthStatus.UNKNOWN, [str(exc)])


def _check_desktop() -> HealthCheckResult:
    try:
        import PySide6  # noqa: F401

        return HealthCheckResult("desktop", HealthStatus.HEALTHY, ["PySide6 available"])
    except Exception:
        return HealthCheckResult("desktop", HealthStatus.DEGRADED, ["PySide6 not installed"])


def _check_task_engine() -> HealthCheckResult:
    try:
        from agents.tasks.task_manager import get_idle_status

        status = get_idle_status()
        return HealthCheckResult("task_engine", HealthStatus.HEALTHY, [status])
    except Exception as exc:
        return HealthCheckResult("task_engine", HealthStatus.UNKNOWN, [str(exc)])


def _check_supervisor() -> HealthCheckResult:
    try:
        from agents.supervisor import should_use_supervisor

        return HealthCheckResult(
            "supervisor",
            HealthStatus.HEALTHY,
            [f"available={callable(should_use_supervisor)}"],
        )
    except Exception as exc:
        return HealthCheckResult("supervisor", HealthStatus.DEGRADED, [str(exc)])


def _check_memory_intelligence() -> HealthCheckResult:
    try:
        from memory.intelligence.profile_builder import build_user_profile

        profile = build_user_profile([])
        return HealthCheckResult(
            "memory_intelligence",
            HealthStatus.HEALTHY,
            [f"profile_empty={profile.is_empty()}"],
        )
    except Exception as exc:
        return HealthCheckResult("memory_intelligence", HealthStatus.DEGRADED, [str(exc)])


def _check_cpu_ram_disk() -> HealthCheckResult:
    details = [f"platform={platform.system()}"]
    status = HealthStatus.HEALTHY
    try:
        import psutil

        details.append(f"cpu_percent={psutil.cpu_percent(interval=0.1):.1f}")
        mem = psutil.virtual_memory()
        details.append(f"ram_percent={mem.percent:.1f}")
        disk = shutil.disk_usage(ROOT)
        details.append(f"disk_free_gb={disk.free / (1024**3):.2f}")
    except ImportError:
        total, used, free = shutil.disk_usage(ROOT)
        details.append(f"disk_free_gb={free / (1024**3):.2f}")
        details.append("psutil not installed (optional)")
    except Exception as exc:
        status = HealthStatus.DEGRADED
        details.append(str(exc))
    return HealthCheckResult("resources", status, details)


def _check_gpu() -> HealthCheckResult:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.mem_get_info()
            free_gb = mem[0] / (1024**3)
            total_gb = mem[1] / (1024**3)
            return HealthCheckResult(
                "gpu",
                HealthStatus.HEALTHY,
                [name, f"vram_free_gb={free_gb:.2f}", f"vram_total_gb={total_gb:.2f}"],
            )
        return HealthCheckResult("gpu", HealthStatus.HEALTHY, ["CUDA not available (CPU mode)"])
    except Exception as exc:
        return HealthCheckResult("gpu", HealthStatus.UNKNOWN, [str(exc)])


def _check_configuration() -> HealthCheckResult:
    try:
        cfg = get_config()
        return HealthCheckResult(
            "configuration",
            HealthStatus.HEALTHY,
            [f"profile={cfg.profile.value}", f"mode={cfg.mode.value}"],
        )
    except Exception as exc:
        return HealthCheckResult("configuration", HealthStatus.DEGRADED, [str(exc)])


def _check_folders() -> HealthCheckResult:
    missing = []
    for rel in ("data", "config", "storage"):
        if not (ROOT / rel).exists():
            missing.append(rel)
    if missing:
        return HealthCheckResult("folders", HealthStatus.DEGRADED, [f"missing={missing}"])
    return HealthCheckResult("folders", HealthStatus.HEALTHY, ["core folders present"])


HEALTH_CHECKS: tuple[tuple[str, Callable[[], HealthCheckResult]], ...] = (
    ("configuration", _check_configuration),
    ("folders", _check_folders),
    ("memory", _check_memory_db),
    ("vector_db", _check_vector_db),
    ("models", _check_models),
    ("plugins", _check_plugins),
    ("voice", _check_voice),
    ("desktop", _check_desktop),
    ("task_engine", _check_task_engine),
    ("supervisor", _check_supervisor),
    ("memory_intelligence", _check_memory_intelligence),
    ("gpu", _check_gpu),
    ("resources", _check_cpu_ram_disk),
)


def run_health_checks() -> list[HealthCheckResult]:
    results: list[HealthCheckResult] = []
    for _, fn in HEALTH_CHECKS:
        try:
            results.append(fn())
        except Exception as exc:
            results.append(HealthCheckResult(fn.__name__, HealthStatus.UNHEALTHY, [str(exc)]))
    return results


def overall_health(results: list[HealthCheckResult]) -> HealthStatus:
    if any(r.status == HealthStatus.UNHEALTHY for r in results):
        return HealthStatus.UNHEALTHY
    if any(r.status == HealthStatus.DEGRADED for r in results):
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY
