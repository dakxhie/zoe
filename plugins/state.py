"""Extension plugin state persistence."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from plugins.plugin_api import PLUGIN_DATA_ROOT

logger = logging.getLogger(__name__)

STATE_FILENAME = "enabled.json"


def _state_path() -> Path:
    PLUGIN_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    return PLUGIN_DATA_ROOT / STATE_FILENAME


def load_enabled_extension_ids() -> set[str]:
    path = _state_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("enabled"), list):
            return {str(item) for item in data["enabled"]}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read plugin state: %s", exc)
    return set()


def save_enabled_extension_ids(enabled: set[str]) -> None:
    path = _state_path()
    path.write_text(
        json.dumps({"enabled": sorted(enabled)}, indent=2),
        encoding="utf-8",
    )


def is_extension_enabled(qualified_id: str) -> bool:
    return qualified_id in load_enabled_extension_ids()


def set_extension_enabled(qualified_id: str, enabled: bool) -> None:
    current = load_enabled_extension_ids()
    if enabled:
        current.add(qualified_id)
    else:
        current.discard(qualified_id)
    save_enabled_extension_ids(current)
