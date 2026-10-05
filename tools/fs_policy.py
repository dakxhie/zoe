"""Filesystem trust boundary for Zoe tools (Phase B1, ZOE_PHASE_A1_DESIGN.md §4-§5).

Responsibilities:

- ``get_workspace_root()``: one explicit, canonical WORKSPACE_ROOT.
- ``resolve_in_workspace()``: canonical, component-based containment with
  symlink-escape detection and sensitive / internal-state denial.
- ``walk_workspace()``: recursive walk that never follows symlinked
  directories, skips hidden, sensitive and internal-state entries, and skips
  links whose target escapes the workspace.
- ``read_bytes_no_follow()``: bounded read of an already-validated file with
  no-follow semantics on the final component where the OS supports it.

WORKSPACE_ROOT configuration (first match wins):

1. environment variable ``ZOE_WORKSPACE_ROOT``
2. ``WORKSPACE_ROOT=`` in ``config/settings.txt`` (via ``core.config.load_settings``)
3. compatibility fallback: the Zoe install root (``core.config.ROOT``).

The fallback keeps existing behaviour (project analysis and the system check
read Zoe's own README and source through these tools). Security implication:
with the fallback, the boundary is the Zoe installation, so Zoe internal state
(history, Chroma memory, telemetry, held-out evaluation data, model and adapter
weights) is explicitly denied below. Configure a dedicated workspace directory
to remove the overlap entirely.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Iterator

from core.config import ROOT

logger = logging.getLogger(__name__)

WORKSPACE_ROOT_ENV = "ZOE_WORKSPACE_ROOT"
WORKSPACE_ROOT_SETTING = "WORKSPACE_ROOT"

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
MAX_WALK_FILES = 20_000
MAX_SEARCH_TOTAL_BYTES = 20 * 1024 * 1024

# Directories skipped by walks and denied for direct access (pre-existing list).
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {".git", "node_modules", "venv", "__pycache__", "storage"}
)

# --- Sensitive path policy (design §5.1, default deny) -----------------------

_SENSITIVE_DIR_NAMES: frozenset[str] = frozenset(
    {".ssh", ".aws", ".azure", ".gcloud", ".kube", ".gnupg", ".password-store"}
)
_SENSITIVE_PATH_SUFFIXES: tuple[tuple[str, ...], ...] = (
    (".docker", "config.json"),
    (".config", "gcloud"),
)
_SENSITIVE_NAME_GLOBS: tuple[str, ...] = (
    # environment files
    ".env", ".env.*", "*.env", ".envrc",
    # private keys / certificates / keyrings
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore", "*.ppk",
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*", "*.gpg", "*.asc", "secring.*",
    # authentication / configuration
    ".netrc", "_netrc", ".npmrc", ".pypirc", ".git-credentials", ".gitconfig",
    "credentials", "credentials.json", "credentials.*", "service-account*.json",
    "*-sa.json", "client_secret*.json", "token.json", "*.token", "*token*.txt",
    "secrets.*", "secret.*", "*.secret", ".htpasswd", "auth.json", "keychain*", "*.kdbx",
    # Android / app signing
    "keystore.properties", "signing.properties", "google-services.json",
    "googleservice-info.plist",
)
# Placeholder-only templates may be read explicitly (content is checked by the caller).
_ENV_TEMPLATE_NAMES: frozenset[str] = frozenset(
    {".env.example", ".env.sample", ".env.template", ".env.dist"}
)

# --- Zoe internal state (applies when the workspace overlaps the install) -----

_INTERNAL_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("data", "history"),
    ("data", "telemetry"),
    ("storage",),
    ("training", "data", "held_out_eval"),
    ("training", "adapters"),
    ("models",),
)
_INTERNAL_DIR_NAMES: frozenset[str] = frozenset({"chroma", "chroma_db", "vector_db", "faiss"})
_WEIGHT_GLOBS: tuple[str, ...] = (
    "*.safetensors", "*.gguf", "*.bin", "*.pt", "*.pth", "*.ckpt", "*.onnx",
    "adapter_model*", "adapter_config.json",
)

_ENV_VAR_IN_PATH = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class AccessMode(str, Enum):
    """What the caller intends to do with a resolved path (no write mode in B1)."""

    READ = "read"  # open an existing regular file
    LIST = "list"  # enumerate an existing directory


class FilesystemError(RuntimeError):
    """Raised when a filesystem operation is not allowed or fails.

    ``error_type`` is a stable machine-readable category; messages never
    contain file contents or secret values.
    """

    def __init__(self, message: str, error_type: str = "filesystem_error") -> None:
        super().__init__(message)
        self.error_type = error_type


@dataclass(frozen=True)
class Workspace:
    """Canonical workspace boundary."""

    root: Path
    source: str  # "env", "settings" or "install_root_fallback"
    install_root: Path
    overlaps_install: bool
    internal_extra: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class ResolvedPath:
    """A path validated against the workspace boundary."""

    canonical: Path
    relative: PurePosixPath


@dataclass
class WalkStats:
    """Counts of entries a walk skipped (names are never reported)."""

    skipped_sensitive: int = 0
    skipped_symlink: int = 0
    skipped_hidden: int = 0
    visited: int = 0
    truncated: bool = False

    def footer(self) -> str:
        parts: list[str] = []
        if self.skipped_sensitive:
            parts.append(f"{self.skipped_sensitive} protected")
        if self.skipped_symlink:
            parts.append(f"{self.skipped_symlink} unsafe symlink")
        if self.truncated:
            parts.append("walk limit reached")
        if not parts:
            return ""
        return f"[skipped: {', '.join(parts)}]"


# --- Workspace root ----------------------------------------------------------

_warned_fallback = False
_root_cache: dict[str, Workspace] = {}


def _within(path: Path, root: Path) -> bool:
    """Component-based containment (never string-prefix)."""
    return path == root or root in path.parents


def _configured_value() -> tuple[str | None, str]:
    env_value = os.environ.get(WORKSPACE_ROOT_ENV, "").strip()
    if env_value:
        return env_value, "env"
    try:
        from core.config import load_settings

        value = (load_settings().get(WORKSPACE_ROOT_SETTING) or "").strip()
    except Exception:  # settings unreadable: fall through to compatibility root
        value = ""
    if value:
        return value, "settings"
    return None, "install_root_fallback"


def _memory_db_prefix() -> tuple[str, ...]:
    try:
        from core.config import load_settings

        raw = (load_settings().get("MEMORY_DB") or "").strip()
    except Exception:
        raw = ""
    if not raw or Path(raw).is_absolute():
        return ()
    parts = tuple(p for p in PurePosixPath(raw.replace("\\", "/")).parts if p not in ("", "."))
    return parts if parts and ".." not in parts else ()


def _validate_root(raw: str) -> Path:
    if _CONTROL_CHARS.search(raw):
        raise FilesystemError("WORKSPACE_ROOT contains invalid characters", "workspace_misconfigured")
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise FilesystemError("WORKSPACE_ROOT must be an absolute path", "workspace_misconfigured")
    canonical = Path(os.path.realpath(candidate))
    if not canonical.exists():
        raise FilesystemError("WORKSPACE_ROOT does not exist", "workspace_misconfigured")
    if not canonical.is_dir():
        raise FilesystemError("WORKSPACE_ROOT is not a directory", "workspace_misconfigured")
    if canonical == Path(canonical.anchor):
        raise FilesystemError("WORKSPACE_ROOT cannot be the filesystem root", "workspace_misconfigured")
    home = Path(os.path.realpath(Path.home()))
    if canonical == home or canonical in home.parents:
        raise FilesystemError(
            "WORKSPACE_ROOT cannot be the home directory or one of its parents",
            "workspace_misconfigured",
        )
    return canonical


def get_workspace_root() -> Workspace:
    """Return the canonical workspace (canonicalized once per configured value)."""
    global _warned_fallback
    raw, source = _configured_value()
    install_root = Path(os.path.realpath(ROOT))
    key = f"{source}:{raw or install_root}"
    cached = _root_cache.get(key)
    if cached is not None:
        return cached

    if raw is None:
        root = _validate_root(str(install_root))
        if not _warned_fallback:
            logger.warning(
                "WORKSPACE_ROOT not configured; filesystem tools use the Zoe install root "
                "with internal state denied. Set %s or WORKSPACE_ROOT to a dedicated workspace.",
                WORKSPACE_ROOT_ENV,
            )
            _warned_fallback = True
    else:
        root = _validate_root(raw)

    overlaps = _within(root, install_root) or _within(install_root, root)
    memory_prefix = _memory_db_prefix()
    workspace = Workspace(
        root=root,
        source=source,
        install_root=install_root,
        overlaps_install=overlaps,
        internal_extra=(memory_prefix,) if memory_prefix else (),
    )
    _root_cache[key] = workspace
    return workspace


def clear_workspace_cache() -> None:
    """Forget cached workspace roots (tests and config reloads)."""
    _root_cache.clear()


# --- Classification ----------------------------------------------------------


def _name_matches(name: str, globs: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatchcase(lowered, pattern) for pattern in globs)


def is_env_template(name: str) -> bool:
    """Return True for placeholder env templates such as ``.env.example``."""
    return name.lower() in _ENV_TEMPLATE_NAMES


def is_sensitive_path(parts: tuple[str, ...]) -> bool:
    """Return True when a relative path matches the sensitive-file policy."""
    if not parts:
        return False
    lowered = tuple(p.lower() for p in parts)
    if any(p in _SENSITIVE_DIR_NAMES for p in lowered):
        return True
    for suffix in _SENSITIVE_PATH_SUFFIXES:
        n = len(suffix)
        for i in range(len(lowered) - n + 1):
            if lowered[i : i + n] == suffix:
                return True
    name = parts[-1]
    if is_env_template(name):
        return False
    return _name_matches(name, _SENSITIVE_NAME_GLOBS)


def _install_relative(path: Path, ws: Workspace) -> tuple[str, ...] | None:
    if not ws.overlaps_install or not _within(path, ws.install_root):
        return None
    return path.relative_to(ws.install_root).parts


def is_internal_state(path: Path, ws: Workspace) -> bool:
    """Return True for Zoe internal state when the workspace overlaps the install."""
    parts = _install_relative(path, ws)
    if parts is None:
        return False
    lowered = tuple(p.lower() for p in parts)
    for prefix in _INTERNAL_PREFIXES + ws.internal_extra:
        prefix_l = tuple(p.lower() for p in prefix)
        if lowered[: len(prefix_l)] == prefix_l:
            return True
    if any(p in _INTERNAL_DIR_NAMES for p in lowered):
        return True
    return bool(parts) and _name_matches(parts[-1], _WEIGHT_GLOBS)


def _is_skipped_dir_path(parts: tuple[str, ...]) -> bool:
    return any(part in SKIP_DIR_NAMES for part in parts)


def deny_reason(path: Path, ws: Workspace) -> str | None:
    """Return a denial category for an absolute in-workspace path, else None."""
    rel_parts = path.relative_to(ws.root).parts if _within(path, ws.root) else path.parts
    if is_internal_state(path, ws):
        return "internal_state"
    if is_sensitive_path(rel_parts):
        return "sensitive_path"
    if _is_skipped_dir_path(rel_parts):
        return "skipped_path"
    return None


# --- Resolution --------------------------------------------------------------


def _check_syntax(user_path: str) -> str:
    if not isinstance(user_path, str):
        raise FilesystemError("Path must be text", "invalid_path")
    if not user_path.strip():
        raise FilesystemError("A path is required", "invalid_path")
    if _CONTROL_CHARS.search(user_path):
        raise FilesystemError("Path contains invalid characters", "invalid_path")
    if user_path.startswith("~"):
        raise FilesystemError("Home-directory shortcuts (~) are not allowed in paths", "invalid_path")
    if _ENV_VAR_IN_PATH.search(user_path):
        raise FilesystemError("Environment variables are not expanded in paths", "invalid_path")
    return user_path.replace("\\", "/")


def resolve_in_workspace(
    user_path: str, mode: AccessMode = AccessMode.READ, ws: Workspace | None = None
) -> ResolvedPath:
    """Resolve a user path inside the workspace or raise ``FilesystemError``.

    Relative paths are relative to WORKSPACE_ROOT (never the process CWD).
    Symlinks are resolved; a canonical target outside the root is rejected.
    Sensitive and internal-state paths are denied before any existence check
    so a denial does not reveal whether the file exists. ``mode`` then checks
    existence and object type (READ needs a file, LIST needs a directory).
    """
    ws = ws or get_workspace_root()
    text = _check_syntax(user_path)
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = ws.root / candidate
    lexical = Path(os.path.normpath(candidate))
    canonical = Path(os.path.realpath(candidate))

    if not _within(canonical, ws.root):
        if _within(lexical, ws.root):
            raise FilesystemError(
                f"Path resolves outside the workspace through a symlink: {user_path}",
                "symlink_escape",
            )
        raise FilesystemError(
            f"Path outside workspace is not allowed: {user_path}", "path_outside_workspace"
        )

    for checked in {lexical, canonical}:
        if not _within(checked, ws.root):
            continue
        reason = deny_reason(checked, ws)
        if reason == "skipped_path":
            raise FilesystemError(f"Access to skipped path is not allowed: {user_path}", reason)
        if reason:
            raise FilesystemError(
                f"Access denied: '{user_path}' is a protected file or directory", reason
            )

    if not canonical.exists():
        label = "File" if mode is AccessMode.READ else "Path"
        raise FilesystemError(f"{label} does not exist: {user_path}", "not_found")
    if mode is AccessMode.READ and not canonical.is_file():
        raise FilesystemError(f"Path is not a file: {user_path}", "not_a_file")
    if mode is AccessMode.LIST and not canonical.is_dir():
        raise FilesystemError(f"Path is not a directory: {user_path}", "not_a_directory")

    return ResolvedPath(
        canonical=canonical,
        relative=PurePosixPath(canonical.relative_to(ws.root).as_posix()),
    )


# --- Safe walking ------------------------------------------------------------


def walk_workspace(start: Path, ws: Workspace, stats: WalkStats) -> Iterator[Path]:
    """Yield in-workspace file paths under ``start`` without following symlinked dirs.

    Every yielded path must still be revalidated with ``resolve_in_workspace``
    immediately before it is opened.
    """
    for dirpath, dirnames, filenames in os.walk(start, topdown=True, followlinks=False):
        current = Path(dirpath)
        kept: list[str] = []
        for name in sorted(dirnames):
            child = current / name
            if os.path.islink(child):
                stats.skipped_symlink += 1
                continue
            if name.startswith("."):
                if is_sensitive_path((name,)):
                    stats.skipped_sensitive += 1
                else:
                    stats.skipped_hidden += 1
                continue
            if name in SKIP_DIR_NAMES:
                continue
            if deny_reason(child, ws):
                stats.skipped_sensitive += 1
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in sorted(filenames):
            if stats.visited >= MAX_WALK_FILES:
                stats.truncated = True
                return
            child = current / name
            if name.startswith(".") and not is_sensitive_path((name,)):
                stats.skipped_hidden += 1
                continue
            if os.path.islink(child):
                target = Path(os.path.realpath(child))
                if not _within(target, ws.root) or not target.is_file():
                    stats.skipped_symlink += 1
                    continue
                if deny_reason(target, ws):
                    stats.skipped_sensitive += 1
                    continue
            if deny_reason(child, ws) or name.startswith("."):
                stats.skipped_sensitive += 1
                continue
            stats.visited += 1
            yield child


# --- Bounded, no-follow reads --------------------------------------------------


def read_bytes_no_follow(canonical: Path, display: str, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """Read a validated regular file, refusing a symlink on the final component."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(canonical, flags)
    except OSError as exc:
        raise FilesystemError(f"Could not open file: {display}", "read_failed") from exc
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise FilesystemError(f"Path is not a regular file: {display}", "not_a_file")
        if info.st_size > max_bytes:
            raise FilesystemError(f"File exceeds 2 MB limit: {display}", "file_too_large")
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FilesystemError(f"File exceeds 2 MB limit: {display}", "file_too_large")
    return data
