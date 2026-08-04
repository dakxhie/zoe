"""Local-only telemetry (never uploaded)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import ROOT
from deployment.config import get_config

logger = logging.getLogger(__name__)


def _telemetry_dir() -> Path:
    try:
        cfg = get_config()
        rel = cfg.raw.get("telemetry", {}).get("path", "data/telemetry")
        path = ROOT / str(rel)
    except Exception:
        path = ROOT / "data" / "telemetry"
    path.mkdir(parents=True, exist_ok=True)
    return path


def telemetry_enabled() -> bool:
    try:
        return get_config().telemetry_enabled()
    except Exception:
        return True


def record_telemetry(event: str, payload: dict[str, Any] | None = None) -> None:
    """Append one anonymous local stats record."""
    if not telemetry_enabled():
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload or {},
    }
    path = _telemetry_dir() / "runtime.jsonl"
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Telemetry recorded: %s", event)
    except OSError as exc:
        logger.debug("Telemetry write skipped: %s", exc)


def summarize_telemetry(limit: int = 500) -> dict[str, Any]:
    path = _telemetry_dir() / "runtime.jsonl"
    if not path.is_file():
        return {"events": 0, "by_type": {}}
    counts: dict[str, int] = {}
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    for line in lines:
        try:
            data = json.loads(line)
            key = str(data.get("event", "unknown"))
            counts[key] = counts.get(key, 0) + 1
        except json.JSONDecodeError:
            continue
    return {"events": len(lines), "by_type": counts}
