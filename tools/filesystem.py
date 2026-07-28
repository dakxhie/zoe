"""Safe read-only filesystem tools for Zoe AI."""

from __future__ import annotations

from pathlib import Path

from core.config import ROOT

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        "__pycache__",
        "storage",
    }
)


class FilesystemError(RuntimeError):
    """Raised when a filesystem operation is not allowed or fails."""


def _normalize_relative_path(path: Path) -> Path:
    """Return a normalized path relative to the project root when possible."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved


def _should_skip(path: Path) -> bool:
    """Return True when a path is inside a skipped directory."""
    relative = _normalize_relative_path(path)
    return any(part in SKIP_DIR_NAMES for part in relative.parts)


def _resolve_directory(path: str) -> Path:
    """Resolve a directory path safely within or under the project root."""
    target = (ROOT / path).resolve()

    if not str(target).startswith(str(ROOT.resolve())):
        raise FilesystemError("Path outside project root is not allowed")

    if not target.exists():
        raise FilesystemError(f"Path does not exist: {path}")

    if not target.is_dir():
        raise FilesystemError(f"Path is not a directory: {path}")

    return target


def _resolve_file(path: str) -> Path:
    """Resolve a file path safely within or under the project root."""
    target = (ROOT / path).resolve()

    if not str(target).startswith(str(ROOT.resolve())):
        raise FilesystemError("Path outside project root is not allowed")

    if not target.exists():
        raise FilesystemError(f"File does not exist: {path}")

    if not target.is_file():
        raise FilesystemError(f"Path is not a file: {path}")

    if _should_skip(target):
        raise FilesystemError(f"Access to skipped path is not allowed: {path}")

    return target


def _is_binary_file(path: Path) -> bool:
    """Return True when a file appears to be binary."""
    try:
        sample = path.read_bytes()[:1024]
    except OSError as exc:
        raise FilesystemError(f"Could not read file '{path}': {exc}") from exc

    return b"\x00" in sample


def list_files(path: str = ".") -> str:
    """List relative file paths under a directory."""
    directory = _resolve_directory(path)
    file_paths: list[str] = []

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file() or _should_skip(file_path):
            continue
        file_paths.append(_normalize_relative_path(file_path).as_posix())

    if not file_paths:
        return "(no files found)"

    return "\n".join(file_paths)


def read_file(path: str, max_lines: int = 200) -> str:
    """Read the first lines of a UTF-8 text file up to 2 MB."""
    file_path = _resolve_file(path)

    if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise FilesystemError(f"File exceeds 2 MB limit: {path}")

    if _is_binary_file(file_path):
        raise FilesystemError(f"Binary files cannot be read: {path}")

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise FilesystemError(f"File is not valid UTF-8 text: {path}") from exc
    except OSError as exc:
        raise FilesystemError(f"Could not read file '{path}': {exc}") from exc

    selected = lines[:max_lines]
    content = "\n".join(selected)

    if len(lines) > max_lines:
        content += f"\n\n... truncated to first {max_lines} lines ..."

    return content


def find_file(filename: str, root: str = ".") -> str:
    """Recursively find files by name using case-insensitive matching."""
    if not filename.strip():
        raise FilesystemError("Filename is required")

    directory = _resolve_directory(root)
    target = filename.strip().lower()
    matches: list[str] = []

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file() or _should_skip(file_path):
            continue
        if target in file_path.name.lower():
            matches.append(_normalize_relative_path(file_path).as_posix())

    if not matches:
        return f"(no files found matching '{filename}')"

    return "\n".join(matches)


def search_text(text: str, root: str = ".") -> str:
    """Recursively search UTF-8 text files for a matching string."""
    if not text.strip():
        raise FilesystemError("Search text is required")

    directory = _resolve_directory(root)
    needle = text.strip()
    results: list[str] = []

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file() or _should_skip(file_path):
            continue
        if _is_binary_file(file_path):
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        relative_path = _normalize_relative_path(file_path).as_posix()
        for line_number, line in enumerate(lines, start=1):
            if needle in line:
                results.append(f"{relative_path}:{line_number}: {line.strip()}")

    if not results:
        return f"(no matches found for '{needle}')"

    return "\n".join(results)
