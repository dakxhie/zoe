"""Shared helpers for Zoe regression tests."""

from __future__ import annotations

import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator

ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "tests" / "reports"
REGRESSION_TAG = "REGTEST_ZOE15"


def ensure_project_root() -> Path:
    """Insert the repository root on sys.path and return it."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return ROOT


def regression_marker() -> str:
    """Return a unique marker string for temporary regression data."""
    return f"{REGRESSION_TAG}_{uuid.uuid4().hex[:12]}"


def tagged_memory_text(marker: str, statement: str) -> str:
    """Prefix a memory statement with a regression marker (embedded, low salience)."""
    return f"{marker} {statement}"


@contextmanager
def measure_seconds() -> Generator[list[float], None, None]:
    """Context manager that stores elapsed seconds in a one-element list."""
    bucket: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield bucket
    finally:
        bucket[0] = time.perf_counter() - start


class TerminalColors:
    """ANSI colors with automatic disable when output is not a TTY."""

    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"

    def __init__(self) -> None:
        self.enabled = self._should_colorize()

    @staticmethod
    def _should_colorize() -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        try:
            return sys.stdout.isatty()
        except Exception:
            return False

    def wrap(self, text: str, color: str) -> str:
        if not self.enabled:
            return text
        return f"{color}{text}{self.RESET}"

    def pass_label(self, text: str = "PASS") -> str:
        return self.wrap(text, self.GREEN)

    def warn_label(self, text: str = "WARN") -> str:
        return self.wrap(text, self.YELLOW)

    def fail_label(self, text: str = "FAIL") -> str:
        return self.wrap(text, self.RED)

    def info_label(self, text: str) -> str:
        return self.wrap(text, self.BLUE)


def delete_regression_memories() -> int:
    """Remove Chroma memories created by regression runs. Returns delete count."""
    try:
        from core.chroma import get_collection

        collection = get_collection("zoe_memory")
        if collection.count() == 0:
            return 0
        results = collection.get(include=["documents"])
        ids = results.get("ids") or []
        documents = results.get("documents") or []
        to_delete = [
            memory_id
            for memory_id, document in zip(ids, documents)
            if REGRESSION_TAG in (document or "")
        ]
        if to_delete:
            collection.delete(ids=to_delete)
        return len(to_delete)
    except Exception:
        return 0


@contextmanager
def regression_memory_cleanup() -> Iterator[None]:
    """Ensure regression-tagged memories are removed after a test block."""
    try:
        yield
    finally:
        delete_regression_memories()
