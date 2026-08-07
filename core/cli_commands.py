"""CLI command discovery for Zoe AI."""

from __future__ import annotations

from pathlib import Path

from core.config import ROOT

CLI_MAIN = ROOT / "cli" / "main.py"

EXPECTED_COMMANDS: frozenset[str] = frozenset(
    {"chat", "doctor", "history", "image", "train", "code", "ingest"}
)


def command_names_from_typer_app(typer_app: object) -> list[str]:
    """Return sorted top-level command names registered on a Typer application."""
    import typer.main as typer_main

    group = typer_main.get_group(typer_app)
    # Typer may expose function names with hyphens; export Python-style identifiers.
    return sorted(name.replace("-", "_") for name in group.commands.keys())


def nested_command_names(typer_app: object, group_name: str) -> list[str]:
    """Return sorted subcommand names for a named Typer group on the application."""
    import typer.main as typer_main

    group = typer_main.get_group(typer_app)
    sub_group = group.commands.get(group_name)
    if sub_group is None or not hasattr(sub_group, "commands"):
        return []

    return sorted(sub_group.commands.keys())


def discover_cli_commands() -> list[str]:
    """Discover registered top-level CLI commands from the Typer application."""
    if not CLI_MAIN.exists():
        return []

    try:
        from cli.main import app
    except Exception:
        return []

    try:
        return command_names_from_typer_app(app)
    except Exception:
        return []
