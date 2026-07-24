"""Zoe AI command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.model import ModelLoadError, generate_response

app = typer.Typer()

_EXIT_COMMANDS = frozenset({"exit", "quit"})


def _print_welcome() -> None:
    """Show the chat session header."""
    print("🤖 Zoe v1")
    print('Type "exit" to quit.\n')


def _read_user_input() -> str | None:
    """Read one line of user input; return None when the session should end."""
    try:
        return input("You: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _should_exit(user_input: str) -> bool:
    """Return True when the user wants to leave the chat loop."""
    return user_input.strip().lower() in _EXIT_COMMANDS


def _run_chat_loop() -> None:
    """Run the interactive chat session until the user exits."""
    _print_welcome()

    while True:
        user_input = _read_user_input()

        if user_input is None:
            break

        if _should_exit(user_input):
            break

        if not user_input.strip():
            continue

        try:
            reply = generate_response(user_input)
        except ModelLoadError as exc:
            print(f"Zoe: Sorry, I could not load the model. {exc}")
            break

        print(f"Zoe: {reply}")


@app.command()
def chat() -> None:
    """Start an interactive chat session with Zoe."""
    _run_chat_loop()


@app.command()
def train() -> None:
    """Placeholder for future fine-tuning support."""
    print("Training will be added later.")


@app.command()
def ingest() -> None:
    """Placeholder for future PDF ingestion support."""
    print("PDF ingestion coming soon.")


if __name__ == "__main__":
    app()
