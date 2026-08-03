"""Regression tests for Typer-based CLI command discovery."""

from __future__ import annotations

import typer

from core.cli_commands import (
    EXPECTED_COMMANDS,
    command_names_from_typer_app,
    discover_cli_commands,
    nested_command_names,
)
from core.doctor import CheckStatus, check_cli


def test_discover_cli_commands_includes_every_public_command() -> None:
    """Every expected public command is registered on the root Typer app."""
    commands = discover_cli_commands()

    assert commands
    assert EXPECTED_COMMANDS.issubset(set(commands))


def test_check_cli_passes_when_all_commands_exist() -> None:
    """Doctor reports PASS when the Typer app exposes all expected commands."""
    result = check_cli()

    assert result.status == CheckStatus.PASS
    assert result.name == "CLI"


def test_new_command_is_automatically_detected_without_hardcoding() -> None:
    """New commands are found via Typer registration, not source-code patterns."""
    app = typer.Typer()

    @app.command()
    def freshly_added_command() -> None:
        """Temporary command for discovery regression coverage."""

    names = command_names_from_typer_app(app)

    assert "freshly_added_command" in names


def test_nested_typer_group_exposes_subcommands() -> None:
    """Named Typer groups remain discoverable with nested subcommands."""
    from cli.main import app

    root_commands = discover_cli_commands()
    assert "history" in root_commands

    history_subcommands = nested_command_names(app, "history")
    assert "sessions" in history_subcommands
    assert "summary" in history_subcommands
    assert "clear" in history_subcommands
    assert "stats" in history_subcommands


def test_nested_typer_fixture_still_works() -> None:
    """Synthetic nested Typer apps enumerate group and subcommand names."""
    root = typer.Typer()
    child = typer.Typer()

    @child.command("list-items")
    def list_items() -> None:
        """List items."""

    root.add_typer(child, name="items")

    assert "items" in command_names_from_typer_app(root)
    assert "list-items" in nested_command_names(root, "items")
