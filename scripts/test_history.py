"""Smoke test for in-memory conversation history.

Usage: python scripts/test_history.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.history import add_message, clear_history, get_history


def main() -> None:
    """Verify FIFO conversation history retention."""
    clear_history()

    for index in range(12):
        role = "user" if index % 2 == 0 else "assistant"
        add_message(role, f"message {index}")

    history = get_history(max_messages=10)

    if len(history) != 10:
        raise SystemExit(f"Expected 10 messages, found {len(history)}")

    if history[0]["content"] != "message 2":
        raise SystemExit(f"Unexpected first message: {history[0]['content']}")

    if history[-1]["content"] != "message 11":
        raise SystemExit(f"Unexpected last message: {history[-1]['content']}")

    expected_order = [f"message {index}" for index in range(2, 12)]
    actual_order = [message["content"] for message in history]

    if actual_order != expected_order:
        raise SystemExit("Conversation history order is incorrect")

    print("Conversation history tests passed.")


if __name__ == "__main__":
    main()
