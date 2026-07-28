"""Configuration loader for Zoe AI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "config" / "settings.txt"

_settings_cache: dict[str, str] | None = None
_settings_mtime: float | None = None


def load_settings() -> dict[str, str]:
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
