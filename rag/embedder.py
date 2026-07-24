"""Document embedding utilities using sentence-transformers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

EMBEDDER_MODEL_NAME = "all-MiniLM-L6-v2"

_embedder: SentenceTransformer | None = None


class EmbedderError(RuntimeError):
    """Raised when the embedding model cannot be loaded or used."""


def load_embedder() -> SentenceTransformer:
    """Load the sentence-transformer model once and reuse it."""
    global _embedder

    if _embedder is not None:
        return _embedder

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbedderError(
            "sentence-transformers is not installed. Run: pip install sentence-transformers"
        ) from exc

    try:
        _embedder = SentenceTransformer(EMBEDDER_MODEL_NAME)
    except Exception as exc:
        raise EmbedderError(
            f"Failed to load embedding model '{EMBEDDER_MODEL_NAME}': {exc}"
        ) from exc

    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create embeddings for one or more text documents."""
    if not texts:
        return []

    try:
        model = load_embedder()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    except EmbedderError:
        raise
    except Exception as exc:
        raise EmbedderError(f"Failed to create embeddings: {exc}") from exc
