"""Safe read-only filesystem tools for Zoe AI.

Phase B1 trust boundary: every path is resolved by ``tools.fs_policy`` against
one canonical WORKSPACE_ROOT (component-based containment, symlink-escape
protection, hidden / sensitive / internal-state denial), recursive walks never
follow symlinked directories, and file content passes ``tools.secret_scan``
before it leaves these functions.
"""

from __future__ import annotations

from pathlib import Path

from tools.fs_policy import (
    MAX_FILE_SIZE_BYTES,
    MAX_SEARCH_TOTAL_BYTES,
    SKIP_DIR_NAMES,
    AccessMode,
    FilesystemError,
    WalkStats,
    Workspace,
    get_workspace_root,
    is_env_template,
    read_bytes_no_follow,
    resolve_in_workspace,
    walk_workspace,
)
from tools.secret_scan import REDACTED_LINE, contains_private_key, line_has_secret, scan_and_redact

__all__ = [
    "FilesystemError",
    "MAX_FILE_SIZE_BYTES",
    "SKIP_DIR_NAMES",
    "find_file",
    "list_files",
    "read_file",
    "search_text",
]

MAX_LIST_ENTRIES = 200
MAX_SEARCH_MATCHES = 50
MAX_MATCH_LINE_CHARS = 300
MAX_READ_LINES = 400
MAX_LINE_CHARS = 2000


def _relative(path: Path, ws: Workspace) -> str:
    return path.relative_to(ws.root).as_posix()


def _resolve_directory(path: str, ws: Workspace) -> Path:
    """Resolve an existing directory inside the workspace (LIST mode)."""
    return resolve_in_workspace(path, AccessMode.LIST, ws).canonical


def _resolve_file(path: str, ws: Workspace) -> Path:
    """Resolve an existing regular file inside the workspace (READ mode)."""
    return resolve_in_workspace(path, AccessMode.READ, ws).canonical


def _decode_text(data: bytes, display: str) -> str:
    if b"\x00" in data[:1024]:
        raise FilesystemError(f"Binary files cannot be read: {display}", "binary_file")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FilesystemError(f"File is not valid UTF-8 text: {display}", "not_utf8") from exc


def _with_footer(lines: list[str], stats: WalkStats, truncated_at: int | None) -> str:
    out = list(lines)
    if truncated_at is not None:
        out.append(f"... truncated to first {truncated_at} entries ...")
    footer = stats.footer()
    if footer:
        out.append(footer)
    return "\n".join(out)


def list_files(path: str = ".") -> str:
    """List relative file paths under a directory inside the workspace."""
    ws = get_workspace_root()
    directory = _resolve_directory(path, ws)
    stats = WalkStats()
    file_paths: list[str] = []
    truncated_at: int | None = None

    for file_path in walk_workspace(directory, ws, stats):
        if len(file_paths) >= MAX_LIST_ENTRIES:
            truncated_at = MAX_LIST_ENTRIES
            break
        file_paths.append(_relative(file_path, ws))

    if not file_paths:
        footer = stats.footer()
        return "(no files found)" + (f"\n{footer}" if footer else "")

    return _with_footer(file_paths, stats, truncated_at)


def read_file(path: str, max_lines: int = 200) -> str:
    """Read the first lines of a UTF-8 text file up to 2 MB, with secrets redacted."""
    ws = get_workspace_root()
    file_path = _resolve_file(path, ws)
    data = read_bytes_no_follow(file_path, path, MAX_FILE_SIZE_BYTES)
    text = _decode_text(data, path)

    if is_env_template(file_path.name) and any(line_has_secret(l) for l in text.splitlines()):
        raise FilesystemError(
            f"Access denied: '{path}' contains values that look like real secrets",
            "sensitive_content",
        )

    scan = scan_and_redact(text)
    if scan.blocked:
        raise FilesystemError(
            f"Access denied: '{path}' contains a private key", "sensitive_content"
        )

    limit = max(1, min(int(max_lines), MAX_READ_LINES))
    lines = scan.text.splitlines()
    selected = [
        line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + " ... [line truncated]"
        for line in lines[:limit]
    ]
    content = "\n".join(selected)

    if len(lines) > limit:
        content += f"\n\n... truncated to first {limit} lines ..."
    if scan.redacted_lines:
        # Phase B2 (A.1 §6.4): keyed fingerprints only; the values are not kept.
        from tools.session_markers import record_redacted_lines

        record_redacted_lines([line for line in text.splitlines() if line_has_secret(line)])
        content += (
            f"\n\n[redacted {scan.redacted_lines} line(s) containing possible secrets]"
        )

    return content


def find_file(filename: str, root: str = ".") -> str:
    """Recursively find files by name using case-insensitive matching."""
    if not filename.strip():
        raise FilesystemError("Filename is required", "invalid_argument")

    ws = get_workspace_root()
    directory = _resolve_directory(root, ws)
    target = filename.strip().lower()
    stats = WalkStats()
    matches: list[str] = []
    truncated_at: int | None = None

    for file_path in walk_workspace(directory, ws, stats):
        if target not in file_path.name.lower():
            continue
        if len(matches) >= MAX_LIST_ENTRIES:
            truncated_at = MAX_LIST_ENTRIES
            break
        matches.append(_relative(file_path, ws))

    if not matches:
        return f"(no files found matching '{filename}')"

    return _with_footer(matches, stats, truncated_at)


def search_text(text: str, root: str = ".") -> str:
    """Recursively search UTF-8 text files for a matching string (secrets redacted)."""
    if not text.strip():
        raise FilesystemError("Search text is required", "invalid_argument")

    ws = get_workspace_root()
    directory = _resolve_directory(root, ws)
    needle = text.strip()
    stats = WalkStats()
    results: list[str] = []
    redacted = 0
    blocked_files = 0
    bytes_read = 0
    truncated_at: int | None = None

    for file_path in walk_workspace(directory, ws, stats):
        relative_path = _relative(file_path, ws)
        try:
            # Revalidate immediately before opening (TOCTOU / swapped symlinks).
            checked = resolve_in_workspace(relative_path, AccessMode.READ, ws).canonical
            if checked.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            data = read_bytes_no_follow(checked, relative_path, MAX_FILE_SIZE_BYTES)
            content = _decode_text(data, relative_path)
        except (FilesystemError, OSError):
            continue

        bytes_read += len(data)
        if needle not in content:
            if bytes_read >= MAX_SEARCH_TOTAL_BYTES:
                stats.truncated = True
                break
            continue
        if contains_private_key(content):
            blocked_files += 1
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if needle not in line:
                continue
            if len(results) >= MAX_SEARCH_MATCHES:
                truncated_at = MAX_SEARCH_MATCHES
                break
            if line_has_secret(line):
                redacted += 1
                shown = REDACTED_LINE
                # Phase B2 (A.1 §6.4): keyed fingerprints only; the value is not kept.
                from tools.session_markers import record_redacted_lines

                record_redacted_lines([line])
            else:
                shown = line.strip()
                if len(shown) > MAX_MATCH_LINE_CHARS:
                    shown = shown[:MAX_MATCH_LINE_CHARS] + " ... [line truncated]"
            results.append(f"{relative_path}:{line_number}: {shown}")
        if truncated_at is not None or bytes_read >= MAX_SEARCH_TOTAL_BYTES:
            stats.truncated = stats.truncated or truncated_at is None
            break

    notes: list[str] = []
    if redacted:
        notes.append(f"[redacted {redacted} matching line(s) containing possible secrets]")
    if blocked_files:
        notes.append(f"[skipped {blocked_files} file(s) containing private keys]")

    if not results:
        base = f"(no matches found for '{needle}')"
        extra = [n for n in notes + [stats.footer()] if n]
        return "\n".join([base, *extra])

    body = _with_footer(results, stats, truncated_at)
    return "\n".join([body, *notes]) if notes else body
