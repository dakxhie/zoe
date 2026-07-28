"""CLI command discovery for Zoe AI."""

from __future__ import annotations

import re
from pathlib import Path

from core.config import ROOT

CLI_MAIN = ROOT / "cli" / "main.py"

EXPECTED_COMMANDS: frozenset[str] = frozenset(
    {"chat", "doctor", "image", "train", "code", "ingest"}
)


def discover_cli_commands() -> list[str]:
    """Discover registered CLI commands from cli/main.py without importing it."""
    if not CLI_MAIN.exists():
        return []

    source = CLI_MAIN.read_text(encoding="utf-8")
    commands: list[str] = []

    pattern = re.compile(
        r'@app\.command(?:\("([^"]+)"\))?\s*\ndef\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        re.MULTILINE,
    )

    for explicit_name, function_name in pattern.findall(source):
        if explicit_name:
            commands.append(explicit_name)
            continue

        if function_name.endswith("_cmd"):
            commands.append(function_name[:-4])
        else:
            commands.append(function_name)

    return sorted(set(commands))
