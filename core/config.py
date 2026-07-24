"""Configuration loader for Zoe AI."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "config" / "settings.txt"


def load_settings() -> dict[str, str]:
    """Load key=value settings from config/settings.txt."""
    settings: dict[str, str] = {}

    with SETTINGS_FILE.open(encoding="utf-8") as settings_file:
        for line in settings_file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()

    return settings
