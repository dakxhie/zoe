#!/usr/bin/env python3
"""Import settings bundle produced by export_settings.py."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Import Zoe settings bundle")
    parser.add_argument("source", help="Export directory")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        print("Source directory not found")
        return 1

    manifest_path = src / "manifest.json"
    if manifest_path.is_file():
        print(json.loads(manifest_path.read_text(encoding="utf-8")))

    settings = src / "settings.txt"
    if settings.is_file():
        shutil.copy2(settings, ROOT / "config" / "settings.txt")

    for name in ("default.yaml", "development.yaml", "production.yaml"):
        file = src / name
        if file.is_file():
            shutil.copy2(file, ROOT / "config" / name)

    enabled = src / "enabled.json"
    if enabled.is_file():
        dest = ROOT / "data" / "plugins" / "enabled.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(enabled, dest)

    prefs = src / "desktop_preferences.json"
    if prefs.is_file():
        dest = ROOT / "data" / "desktop_preferences.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prefs, dest)

    from deployment.config import reset_config_for_tests, invalidate_settings_cache

    reset_config_for_tests()
    invalidate_settings_cache()
    print("Import complete. Restart Zoe to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
