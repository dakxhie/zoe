"""Zoe AI command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from core.logging_config import configure_logging

configure_logging()

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.model import ModelLoadError, generate_response
from code.indexer import build_code_index
from pdf.indexer import build_pdf_index
from rag.retriever import build_index

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
def code(project_path: str) -> None:
    """Index a project's source code."""
    print("Scanning project...")
    indexed_files, indexed_chunks = build_code_index(project_path)
    print(f"Indexed {indexed_files} files")
    print(f"Indexed {indexed_chunks} chunks")
    print("Done.")


@app.command()
def ingest() -> None:
    """Build the notes and PDF indexes."""
    print("--------------------------------")
    print()
    print("Building Notes Index...")
    print()
    indexed_notes = build_index()
    print(f"Indexed Notes: {indexed_notes}")
    print()
    print("Building PDF Index...")
    print()
    indexed_pdf_chunks = build_pdf_index()
    print(f"Indexed PDF Chunks: {indexed_pdf_chunks}")
    print()
    print("Done.")
    print()
    print("--------------------------------")


if __name__ == "__main__":
    app()
