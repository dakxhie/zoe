"""PDF loading, chunking, indexing, and retrieval for Zoe AI."""

from pdf.chunker import TextChunk, chunk_text
from pdf.indexer import PDFIndexerError, build_pdf_index
from pdf.loader import PDFDocument, PDFLoaderError, load_pdfs
from pdf.retriever import PDFRetrieverError, PDFSearchResult, search_documents

__all__ = [
    "PDFDocument",
    "PDFIndexerError",
    "PDFLoaderError",
    "PDFRetrieverError",
    "PDFSearchResult",
    "TextChunk",
    "build_pdf_index",
    "chunk_text",
    "load_pdfs",
    "search_documents",
]
