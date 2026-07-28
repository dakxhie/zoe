"""Pytest coverage for conversational memory inference."""

from __future__ import annotations

import pytest

from memory.detector import should_remember
from memory.history import add_message, clear_history
from memory.inference import infer_memory, is_personal_info_question, parse_personal_question
from memory.store import save_memory

INFERENCE_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "What is your favorite programming language?",
        "python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite programming language?",
        "it's python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite programming language?",
        "definitely python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite programming language?",
        "mine is python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite programming language?",
        "I prefer python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite programming language?",
        "I use python",
        "My favorite programming language is python.",
    ),
    (
        "What is your favorite animal?",
        "wolf",
        "My favorite animal is wolf.",
    ),
    (
        "What is your favorite color?",
        "black",
        "My favorite color is black.",
    ),
    (
        "Is Python your favorite programming language?",
        "yes",
        "My favorite programming language is Python.",
    ),
    (
        "What is your name?",
        "Dakshitha",
        "My name is Dakshitha.",
    ),
    (
        "Where do you live?",
        "India",
        "I live in India.",
    ),
)

NO_INFERENCE_CASES: tuple[tuple[str, str], ...] = (
    ("What is Python?", "python"),
    ("Can you write a Python function to sort a list?", "python"),
    ("What is 2 + 2?", "4"),
    ("How do I fix this bug?", "restart the server"),
    ("What is your favorite programming language?", "What is Java?"),
    ("What is your favorite programming language?", "Can you explain recursion?"),
    ("What is your favorite programming language?", ""),
    ("What is your favorite programming language?", "Hello"),
    ("Tell me about your day.", "python"),
)


@pytest.mark.parametrize(
    ("assistant_message", "user_reply", "expected_memory"),
    INFERENCE_CASES,
)
def test_infer_memory_from_conversational_replies(
    assistant_message: str,
    user_reply: str,
    expected_memory: str,
) -> None:
    """Infer memories from short replies to personal assistant questions."""
    assert infer_memory(user_reply, assistant_message) == expected_memory


@pytest.mark.parametrize(("assistant_message", "user_reply"), NO_INFERENCE_CASES)
def test_infer_memory_skips_non_personal_context(
    assistant_message: str,
    user_reply: str,
) -> None:
    """Do not infer memories for math, code, or unrelated replies."""
    assert infer_memory(user_reply, assistant_message) is None


def test_is_personal_info_question_detects_assistant_prompts() -> None:
    """Detect personal-info questions from the assistant."""
    assert is_personal_info_question("What is your favorite programming language?")
    assert is_personal_info_question("Where do you live?")
    assert not is_personal_info_question("What is Python?")
    assert not is_personal_info_question("Can you write a Python function?")


def test_parse_personal_question_returns_template() -> None:
    """Parse a personal question into a memory template."""
    parsed = parse_personal_question("What is your favorite animal?")

    assert parsed is not None
    assert parsed.template == "My favorite {topic} is {value}."
    assert parsed.topic == "animal"


def test_should_remember_behavior_is_unchanged() -> None:
    """Keep explicit detector behavior unchanged."""
    assert should_remember("My favorite programming language is Python.")
    assert not should_remember("python")
    assert not should_remember("What is my favorite programming language?")


def test_save_memory_uses_previous_assistant_context(monkeypatch) -> None:
    """Save inferred memories using the previous assistant message in history."""
    clear_history()
    add_message("assistant", "What is your favorite programming language?")

    saved_texts: list[str] = []

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 0.0]]

    class _FakeCollection:
        def count(self) -> int:
            return 0

        def add(self, **kwargs) -> None:
            saved_texts.extend(kwargs["documents"])

    monkeypatch.setattr("memory.store.get_collection", lambda: _FakeCollection())
    monkeypatch.setattr("memory.store.existing_document_texts", lambda _collection: set())
    monkeypatch.setattr("memory.store.embed_texts", _fake_embed)

    saved = save_memory("python")

    assert saved is True
    assert saved_texts == ["My favorite programming language is python."]
