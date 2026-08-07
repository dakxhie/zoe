"""Configuration loader for Zoe AI.

Keeps a mtime-aware cache of config/settings.txt so hot paths (routing,
doctor, retrieval) do not re-parse the file on every call. Deployment
overlays are applied when available; failures fall back to legacy settings
so local/Colab runs stay usable without deployment.yaml.
"""

from __future__ import annotations

import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "config" / "settings.txt"

logger = logging.getLogger(__name__)

_settings_cache: dict[str, str] | None = None
_settings_mtime: float | None = None


def _load_settings_txt() -> dict[str, str]:
    """Load key=value settings from config/settings.txt."""
    global _settings_cache, _settings_mtime

    try:
        current_mtime = SETTINGS_FILE.stat().st_mtime
    except OSError:
        return {}

    if _settings_cache is not None and _settings_mtime == current_mtime:
        return dict(_settings_cache)

    settings: dict[str, str] = {}

    with SETTINGS_FILE.open(encoding="utf-8") as settings_file:
        for line in settings_file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()

    _settings_cache = dict(settings)
    _settings_mtime = current_mtime
    return dict(settings)


def load_settings() -> dict[str, str]:
    """Load settings with deployment overlay (legacy settings.txt remains supported)."""
    legacy = _load_settings_txt()
    try:
        from deployment.config import get_effective_settings

        return get_effective_settings(legacy)
    except Exception as exc:
        # Overlay is optional; keep legacy settings so core chat still boots.
        logger.debug("Deployment settings overlay unavailable: %s", exc)
        return legacy
