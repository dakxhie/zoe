"""Load and extract text from PDF documents."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from core.config import ROOT, load_settings

PDF_SUFFIX = ".pdf"


class PDFDocument(TypedDict):
    """A PDF document with extracted text."""

    id: str
    filename: str
    text: str


class PDFLoaderError(RuntimeError):
    """Raised when PDF loading cannot proceed due to an unrecoverable error."""


def get_pdfs_dir() -> Path:
    """Return the absolute path to the PDF directory."""
    settings = load_settings()
    pdf_folder = settings.get("PDF_FOLDER", "data/pdfs")
    pdf_path = Path(pdf_folder)

    if not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path

    return pdf_path


def _is_pdf_file(path: Path) -> bool:
    """Return True for PDF files."""
    return path.is_file() and path.suffix.lower() == PDF_SUFFIX


def _extract_text(pdf_path: Path) -> str | None:
    """Extract text from one PDF, or return None when it should be skipped."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PDFLoaderError(
            "pypdf is not installed. Run: pip install pypdf"
        ) from exc

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return None

    if reader.is_encrypted:
        return None

    page_texts: list[str] = []

    for page in reader.pages:
        try:
            page_text = page.extract_text()
        except Exception:
            continue

        if page_text:
            page_texts.append(page_text)

    extracted_text = "\n".join(page_texts).strip()
    if not extracted_text:
        return None

    return extracted_text


def _load_single_pdf(pdf_path: Path) -> PDFDocument | None:
    """Load one PDF into a document dictionary, or skip it when unusable."""
    extracted_text = _extract_text(pdf_path)

    if extracted_text is None:
        return None

    return {
        "id": pdf_path.stem,
        "filename": pdf_path.name,
        "text": extracted_text,
    }


def load_pdfs() -> list[PDFDocument]:
    """Load every PDF recursively from data/pdfs/."""
    pdfs_dir = get_pdfs_dir()

    if not pdfs_dir.exists():
        raise PDFLoaderError(f"PDF directory does not exist: {pdfs_dir}")

    documents: list[PDFDocument] = []

    for pdf_path in sorted(pdfs_dir.rglob("*")):
        if not _is_pdf_file(pdf_path):
            continue

        document = _load_single_pdf(pdf_path)
        if document is not None:
            documents.append(document)

    return documents
