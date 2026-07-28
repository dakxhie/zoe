"""Load source code files from a project directory."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".json",
        ".md",
        ".yaml",
        ".yml",
    }
)
SPECIAL_FILENAMES: frozenset[str] = frozenset({".env.example"})
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        "venv",
        "build",
        "dist",
        "storage",
        "__pycache__",
    }
)

LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".example": "env",
}


class CodeFile(TypedDict):
    """A supported source file loaded from disk."""

    id: str
    filename: str
    path: str
    language: str
    content: str


class CodeLoaderError(RuntimeError):
    """Raised when code loading cannot proceed due to an unrecoverable error."""


def _resolve_project_path(project_path: str | Path) -> Path:
    """Return an absolute project path."""
    path = Path(project_path).expanduser().resolve()
    if not path.exists():
        raise CodeLoaderError(f"Project path does not exist: {path}")
    if not path.is_dir():
        raise CodeLoaderError(f"Project path is not a directory: {path}")
    return path


def _should_skip_path(path: Path) -> bool:
    """Return True when a path is inside a skipped directory."""
    return any(part in SKIP_DIRS for part in path.parts)


def _is_supported_file(path: Path) -> bool:
    """Return True for supported code files."""
    if not path.is_file():
        return False
    if path.name in SPECIAL_FILENAMES:
        return True
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _detect_language(path: Path) -> str:
    """Detect a language label from the file path."""
    if path.name in SPECIAL_FILENAMES:
        return "env"
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "text")


def _is_binary_file(path: Path) -> bool:
    """Return True when a file appears to be binary."""
    try:
        sample = path.read_bytes()[:1024]
    except OSError:
        return True

    return b"\x00" in sample


def _make_file_id(project_root: Path, file_path: Path) -> str:
    """Build a stable file id from the project-relative path."""
    return file_path.relative_to(project_root).as_posix()


def _read_code_file(project_root: Path, file_path: Path) -> CodeFile | None:
    """Read one code file into a document dictionary."""
    if _is_binary_file(file_path):
        return None

    try:
        content = file_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None

    if not content:
        return None

    relative_path = file_path.relative_to(project_root).as_posix()

    return {
        "id": _make_file_id(project_root, file_path),
        "filename": file_path.name,
        "path": relative_path,
        "language": _detect_language(file_path),
        "content": content,
    }


def load_code(project_path: str | Path) -> list[CodeFile]:
    """Recursively load supported code files from a project directory."""
    project_root = _resolve_project_path(project_path)
    documents: list[CodeFile] = []

    for file_path in sorted(project_root.rglob("*")):
        if _should_skip_path(file_path.relative_to(project_root)):
            continue
        if not _is_supported_file(file_path):
            continue

        try:
            document = _read_code_file(project_root, file_path)
        except Exception:
            continue

        if document is not None:
            documents.append(document)

    return documents
