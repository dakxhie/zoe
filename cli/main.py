"""Zoe AI command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import typer

from core.logging_config import configure_logging

configure_logging()

from brain.model import ModelLoadError, generate_image_response, generate_response
from codebase.indexer import build_code_index
from core.diagnostics import print_startup_diagnostics
from core.doctor import print_doctor_report, run_doctor
from pdf.indexer import build_pdf_index
from rag.retriever import build_index
from vision.pipeline import analyze_image

_CLI_EPILOG = """
Examples:
  python cli/main.py chat
  python cli/main.py ingest
  python cli/main.py code .
  python cli/main.py image photo.jpg
  python cli/main.py image screenshot.png --prompt "Explain the error."
"""

app = typer.Typer(
    name="zoe",
    help="Zoe AI — local-first personal assistant with notes, memory, PDF, code, web, and vision.",
    epilog=_CLI_EPILOG,
    no_args_is_help=True,
)

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
    print_startup_diagnostics()
    print()

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


@app.command("image")
def image_cmd(
    image_path: str = typer.Argument(..., help="Path to the image file."),
    prompt: str = typer.Option("", "--prompt", help="Optional question about the image."),
) -> None:
    """Analyze an image directly or answer a question about it."""
    result = analyze_image(image_path, prompt=prompt)
    metadata = result.get("metadata", {})

    if not isinstance(metadata, dict) or metadata.get("width", 0) == 0:
        print(f"Sorry, I could not load the image: {image_path}")
        raise typer.Exit(code=1)

    if not prompt.strip():
        print("Caption")
        print(result.get("caption") or "(empty)")
        print()
        print("OCR")
        print(result.get("ocr") or "(empty)")
        print()
        print("Metadata")
        for key, value in metadata.items():
            print(f"{key}: {value}")
        return

    try:
        reply = generate_image_response(image_path, prompt)
    except ModelLoadError as exc:
        print(f"Zoe: Sorry, I could not load the model. {exc}")
        raise typer.Exit(code=1) from exc

    print(f"Zoe: {reply}")


@app.command()
def doctor() -> None:
    """Run a full system health check and print a diagnostic report."""
    print_doctor_report(run_doctor())


@app.command()
def train() -> None:
    """Placeholder for future fine-tuning support."""
    print("Training will be added later.")


@app.command()
def code(
    project_path: str = typer.Argument(..., help="Root directory of the project to index."),
) -> None:
    """Index a project's source code for semantic search."""
    print("Scanning project...")
    indexed_files, indexed_chunks = build_code_index(project_path)
    print(f"Indexed {indexed_files} files")
    print(f"Indexed {indexed_chunks} chunks")
    print("Done.")


@app.command()
def ingest() -> None:
    """Build the notes and PDF indexes from data/notes/ and data/pdfs/."""
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
