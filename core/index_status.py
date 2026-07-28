"""Collection names and index status helpers for Zoe AI."""

from __future__ import annotations

COLLECTION_MEMORY = "zoe_memory"
COLLECTION_NOTES = "zoe_notes"
COLLECTION_PDF = "zoe_documents"
COLLECTION_CODE = "zoe_code"

EMPTY_INDEX_MESSAGES: dict[str, str] = {
    "notes": "Your notes haven't been indexed yet. Run: zoe ingest",
    "pdf": "No PDFs have been indexed yet. Add PDFs and run: zoe ingest",
    "code": "No project has been indexed yet. Run: zoe code <path>",
}

TOOL_COLLECTIONS: dict[str, str] = {
    "notes": COLLECTION_NOTES,
    "pdf": COLLECTION_PDF,
    "code": COLLECTION_CODE,
}
