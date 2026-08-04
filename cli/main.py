"""Zoe AI command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atexit
import typer

from core.diagnostics import print_startup_diagnostics
from core.doctor import print_doctor_report, run_doctor
from core.logging_config import configure_logging

from deployment.config import load_config
from deployment.shutdown import run_shutdown_sequence

load_config()
configure_logging()

atexit.register(run_shutdown_sequence)

_CLI_EPILOG = """
Examples:
  python cli/main.py chat
  python cli/main.py ingest
  python cli/main.py code .
  python cli/main.py doctor
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
    print("🤖 Zoe v2")
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
    from brain.model import ModelLoadError, generate_response
    from brain.pipeline import _prepare_chat_session
    from deployment.startup import run_startup_sequence

    _print_welcome()
    _prepare_chat_session()
    report = run_startup_sequence()
    for line in report.diagnostic_lines:
        print(line)
    if not report.diagnostic_lines:
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
    from brain.model import ModelLoadError, generate_image_response
    from vision.pipeline import analyze_image

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
    from codebase.indexer import build_code_index

    print("Scanning project...")
    indexed_files, indexed_chunks = build_code_index(project_path)
    print(f"Indexed {indexed_files} files")
    print(f"Indexed {indexed_chunks} chunks")
    print("Done.")


@app.command()
def ingest() -> None:
    """Build the notes and PDF indexes from data/notes/ and data/pdfs/."""
    from pdf.indexer import build_pdf_index
    from rag.retriever import build_index

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


plugins_app = typer.Typer(help="Manage Zoe extension plugins.")
app.add_typer(plugins_app, name="plugins")


@plugins_app.callback(invoke_without_command=True)
def plugins_default(ctx: typer.Context) -> None:
    """List installed plugins (same as plugins list)."""
    if ctx.invoked_subcommand is not None:
        return
    _plugins_list()


def _plugins_list() -> None:
    from plugins.manager import get_plugin_manager

    rows = get_plugin_manager().list_installed()
    if not rows:
        print("No plugins installed.")
        return
    for row in rows:
        status = "enabled" if row.enabled else "disabled"
        loaded = "loaded" if row.loaded else "not loaded"
        print(f"{row.plugin_id}  {row.name} v{row.version}  [{row.kind}] {status}, {loaded}")
        for err in row.errors:
            print(f"  ! {err}")


@plugins_app.command("list")
def plugins_list_cmd() -> None:
    """List installed plugins."""
    _plugins_list()


@plugins_app.command("enable")
def plugins_enable(plugin_id: str = typer.Argument(..., help="Plugin id (e.g. ext.clock or clock)")) -> None:
    from plugins.manager import get_plugin_manager

    if get_plugin_manager().enable(plugin_id):
        print(f"Enabled {plugin_id}")
    else:
        print(f"Could not enable {plugin_id}")
        raise typer.Exit(code=1)


@plugins_app.command("disable")
def plugins_disable(plugin_id: str = typer.Argument(..., help="Plugin id")) -> None:
    from plugins.manager import get_plugin_manager

    if get_plugin_manager().disable(plugin_id):
        print(f"Disabled {plugin_id}")
    else:
        print(f"Could not disable {plugin_id}")
        raise typer.Exit(code=1)


@plugins_app.command("reload")
def plugins_reload(plugin_id: str = typer.Argument(..., help="Plugin id")) -> None:
    from plugins.manager import get_plugin_manager

    if get_plugin_manager().reload(plugin_id):
        print(f"Reloaded {plugin_id}")
    else:
        print(f"Could not reload {plugin_id}")
        raise typer.Exit(code=1)


history_app = typer.Typer(help="Manage persistent conversation history.")
app.add_typer(history_app, name="history")


@history_app.callback(invoke_without_command=True)
def history_default(ctx: typer.Context) -> None:
    """Print the last 20 conversation messages."""
    if ctx.invoked_subcommand is not None:
        return

    from conversation.history import last_messages

    messages = last_messages(20)
    if not messages:
        print("No conversation history found.")
        return

    for message in messages:
        role = message["role"].capitalize()
        print(f"{role}: {message['content']}")


@history_app.command("sessions")
def history_sessions() -> None:
    """List all conversation session ids."""
    from conversation.history import all_sessions

    sessions = all_sessions()
    if not sessions:
        print("No sessions found.")
        return

    for session_id in sessions:
        print(session_id)


@history_app.command("summary")
def history_summary() -> None:
    """Print the persisted conversation summary."""
    from conversation.summarizer import load_summary, summary_as_text

    summary = summary_as_text(load_summary())
    if not summary:
        print("No conversation summary found.")
        return

    print(summary)


@history_app.command("clear")
def history_clear() -> None:
    """Delete persisted conversation history."""
    from conversation.history import clear_history

    clear_history()
    print("Conversation history cleared.")


@history_app.command("stats")
def history_stats() -> None:
    """Print conversation history statistics."""
    from conversation.history import conversation_statistics

    stats = conversation_statistics()
    print(f"Messages: {stats.messages}")
    print(f"Sessions: {stats.sessions}")
    print(f"Token estimate: {stats.token_estimate}")
    print(f"Summary size: {stats.summary_size} chars")
    print(f"Database size: {stats.database_size} bytes")


if __name__ == "__main__":
    app()
