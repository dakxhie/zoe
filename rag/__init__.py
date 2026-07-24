"""Retrieval-Augmented Generation pipeline for Zoe AI notes."""

from rag.embedder import embed_texts, load_embedder
from rag.loader import load_documents
from rag.retriever import build_index, search

__all__ = [
    "build_index",
    "embed_texts",
    "load_documents",
    "load_embedder",
    "search",
]
