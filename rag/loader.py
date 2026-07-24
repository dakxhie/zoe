"""Load note documents from the configured notes directory."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from core.config import ROOT, load_settings

SUPPORTED_SUFFIXES = {".md", ".txt"}


class Document(TypedDict):
    """A note document loaded from disk."""

    id: str
    filename: str
    content: str


class DocumentLoadError(RuntimeError):
    """Raised when note documents cannot be loaded."""


def get_notes_dir() -> Path:
    """Return the absolute path to the notes directory."""
    settings = load_settings()
    notes_folder = settings.get("NOTES_FOLDER", "data/notes")
    notes_path = Path(notes_folder)

    if not notes_path.is_absolute():
        notes_path = ROOT / notes_path

    return notes_path


def _is_supported_file(path: Path) -> bool:
    """Return True for supported note file types."""
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES


def _make_document_id(notes_dir: Path, file_path: Path) -> str:
    """Build a stable document id from the file path relative to notes_dir."""
    relative_path = file_path.relative_to(notes_dir)
    return relative_path.as_posix()


def _read_document(notes_dir: Path, file_path: Path) -> Document:
    """Read one note file into a document dictionary."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentLoadError(
            f"Could not read note file '{file_path}': {exc}"
        ) from exc

    return {
        "id": _make_document_id(notes_dir, file_path),
        "filename": file_path.name,
        "content": content,
    }


def load_documents() -> list[Document]:
    """Load every .md and .txt file recursively from data/notes/."""
    notes_dir = get_notes_dir()

    if not notes_dir.exists():
        raise DocumentLoadError(f"Notes directory does not exist: {notes_dir}")

    documents: list[Document] = []

    for file_path in sorted(notes_dir.rglob("*")):
        if not _is_supported_file(file_path):
            continue
        documents.append(_read_document(notes_dir, file_path))

    return documents
