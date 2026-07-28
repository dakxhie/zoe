"""Collection names and index status helpers for Zoe AI."""

from __future__ import annotations

COLLECTION_MEMORY = "zoe_memory"
COLLECTION_NOTES = "zoe_notes"
COLLECTION_PDF = "zoe_documents"
COLLECTION_CODE = "zoe_code"

EMPTY_INDEX_MESSAGES: dict[str, str] = {
    "notes": "Your notes haven't been indexed yet. Run: python cli/main.py ingest",
    "pdf": "No PDFs have been indexed yet. Add PDFs and run: python cli/main.py ingest",
    "code": "No project has been indexed yet. Run: python cli/main.py code <path>",
}

TOOL_COLLECTIONS: dict[str, str] = {
    "notes": COLLECTION_NOTES,
    "pdf": COLLECTION_PDF,
    "code": COLLECTION_CODE,
}
