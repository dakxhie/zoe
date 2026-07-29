"""Pytest coverage for Chroma collection listing compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from core.chroma import ChromaError, list_collection_names
from core.doctor import check_chroma


@dataclass
class _FakeCollection:
    name: str


def test_list_collection_names_accepts_string_entries() -> None:
    """ChromaDB 0.6+ returns collection names as strings."""
    client = MagicMock()
    client.list_collections.return_value = [
        "zoe_memory",
        "zoe_notes",
        "zoe_documents",
        "zoe_code",
        "zoe_history",
    ]

    with patch("core.chroma.get_chroma_client", return_value=client):
        names = list_collection_names()

    assert names == [
        "zoe_code",
        "zoe_documents",
        "zoe_history",
        "zoe_memory",
        "zoe_notes",
    ]


def test_list_collection_names_accepts_collection_objects() -> None:
    """ChromaDB 0.5 and earlier return Collection objects with a name attribute."""
    client = MagicMock()
    client.list_collections.return_value = [
        _FakeCollection("zoe_memory"),
        _FakeCollection("zoe_notes"),
    ]

    with patch("core.chroma.get_chroma_client", return_value=client):
        names = list_collection_names()

    assert names == ["zoe_memory", "zoe_notes"]


def test_list_collection_names_raises_on_unexpected_entry() -> None:
    """Reject unknown list_collections() entry shapes."""
    client = MagicMock()
    client.list_collections.return_value = [123]

    with patch("core.chroma.get_chroma_client", return_value=client):
        with pytest.raises(ChromaError, match="Unexpected collection entry"):
            list_collection_names()


def test_check_chroma_reports_collections_with_string_names() -> None:
    """Doctor should enumerate collections when Chroma returns name strings."""
    fake_collection = MagicMock()
    fake_collection.count.return_value = 7

    with patch("core.doctor.get_chroma_path", return_value=MagicMock(exists=lambda: True)), patch(
        "core.doctor.list_collection_names",
        return_value=["zoe_memory", "zoe_notes"],
    ), patch(
        "core.doctor.get_collection",
        return_value=fake_collection,
    ):
        result, collections = check_chroma()

    assert result.status.value == "PASS"
    assert any(info.name == "zoe_memory" and info.count == 7 for info in collections)
    assert any(info.name == "zoe_notes" and info.count == 7 for info in collections)
