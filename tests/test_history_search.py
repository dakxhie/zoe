"""Pytest coverage for conversation semantic search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from conversation.history import append_message
from conversation.retriever import retrieve_conversation_context, search_history
from conversation.session import create_session
from conversation.storage import StoredMessage
from tests.conversation_fixtures import isolated_history  # noqa: F401


def test_search_history_returns_ranked_results(isolated_history) -> None:
    """Return semantic search results sorted by relevance."""
    fake_collection = MagicMock()
    fake_collection.count.return_value = 2
    fake_collection.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["user: My dog is Max.", "user: I like coffee."]],
        "metadatas": [[{"session": "s", "role": "user", "timestamp": "t"}] * 2],
        "distances": [[0.1, 0.8]],
    }

    with patch("conversation.retriever._get_collection", return_value=fake_collection), patch(
        "conversation.retriever.embed_texts",
        return_value=[[0.0, 0.1]],
    ):
        results = search_history("What is my dog's name?", top_k=2)

    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert "Max" in results[0]["content"]


def test_retrieve_conversation_context_deduplicates_messages(isolated_history) -> None:
    """Combine summary, search, and recent messages without duplicates."""
    recent = [
        StoredMessage(session="s", timestamp="t", role="user", content="My dog is Max."),
        StoredMessage(session="s", timestamp="t", role="assistant", content="Nice name."),
    ]

    with patch(
        "conversation.retriever.search_history",
        return_value=[
            {
                "id": "1",
                "session": "s",
                "role": "user",
                "content": "user: My dog is Max.",
                "timestamp": "t",
                "score": 0.9,
            }
        ],
    ):
        context = retrieve_conversation_context(
            "What's my dog's name?",
            summary_text="User owns a dog named Max.",
            recent_messages=recent,
        )

    assert "Max" in context
    assert context.lower().count("my dog is max") == 1


def test_append_indexes_messages(isolated_history) -> None:
    """Index messages in Chroma when appending history."""
    create_session()

    with patch("conversation.history.index_message") as index_message:
        append_message("user", "Indexed message")
        index_message.assert_called_once()
