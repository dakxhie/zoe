"""Smoke test for the Zoe memory detector."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.detector import should_remember

EXAMPLES: tuple[str, ...] = (
    "My favorite programming language is Python.",
    "I like building AI projects in my free time.",
    "My name is Dakshitha.",
    "I am building Zoe AI as my personal assistant.",
    "My goal is to build my own AGI.",
    "What is my favorite programming language?",
    "Can you write a Python function to sort a list?",
    "Hello",
    "Tell me a joke.",
    "Explain how recursion works.",
    "I love working on machine learning projects.",
    "I live in India.",
)


def main() -> None:
    """Print detector decisions for example sentences."""
    for sentence in EXAMPLES:
        decision = "REMEMBER" if should_remember(sentence) else "SKIP"
        print(f"Input: {sentence}")
        print(f"Decision: {decision}\n")


if __name__ == "__main__":
    main()
