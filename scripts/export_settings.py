#!/usr/bin/env python3
"""Export settings, YAML preferences, and plugin state (not memories or conversations)."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Export Zoe portable settings bundle")
    parser.add_argument(
        "destination",
        nargs="?",
        default="data/exports/zoe-export",
        help="Output directory",
    )
    args = parser.parse_args()

    dest = Path(args.destination)
    dest.mkdir(parents=True, exist_ok=True)

    from core.config import SETTINGS_FILE
    from deployment.config import get_config, load_config

    load_config()
    cfg = get_config()

    if SETTINGS_FILE.is_file():
        shutil.copy2(SETTINGS_FILE, dest / "settings.txt")

    for name in ("default.yaml", "development.yaml", "production.yaml"):
        src = ROOT / "config" / name
        if src.is_file():
            shutil.copy2(src, dest / name)

    plugin_state = ROOT / "data" / "plugins" / "enabled.json"
    if plugin_state.is_file():
        shutil.copy2(plugin_state, dest / "enabled.json")

    prefs = ROOT / "data" / "desktop_preferences.json"
    if prefs.is_file():
        shutil.copy2(prefs, dest / "desktop_preferences.json")

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": cfg.profile.value,
        "mode": cfg.mode.value,
        "excludes": ["memories", "conversations"],
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Exported to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
