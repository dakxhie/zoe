from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SETTINGS_FILE = ROOT / "config" / "settings.txt"

def load_settings():
    settings = {}

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()

    return settings
