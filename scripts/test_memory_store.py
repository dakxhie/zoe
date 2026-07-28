"""Smoke test for persistent Zoe memory storage.

Usage: python scripts/test_memory_store.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.store import MemoryStoreError, list_memories, save_memory

SAMPLE_MEMORIES: tuple[str, ...] = (
    "My favorite color is black.",
    "My favorite food is pizza.",
    "I am building Zoe AI.",
)


def _save_samples() -> None:
    """Save example memories that should pass the detector."""
    for text in SAMPLE_MEMORIES:
        saved = save_memory(text)
        print(f'Save "{text}" -> {saved}')


def _print_memories() -> None:
    """Print all stored conversation memories."""
    print("\nStored memories:")
    memories = list_memories()

    if not memories:
        print("(none)")
        return

    for memory in memories:
        print(f"- [{memory['created_at']}] {memory['text']}")


def main() -> None:
    """Save sample memories and list everything stored in ChromaDB."""
    try:
        _save_samples()
        _print_memories()
    except MemoryStoreError as exc:
        print(f"Memory store test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
