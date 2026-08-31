"""Text extraction for PDF documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf_text(file_path: str) -> dict[str, Any]:
    """Extract text from every page in a local PDF.

    The combined ``text`` field separates pages with a form-feed character.
    Individual page text is also returned so callers can retain page numbers.
    Image-only PDFs require OCR and therefore return empty text for those pages.
    """
    path = _validate_pdf_path(file_path)

    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception as error:
                raise ValueError("PDF is encrypted and cannot be read") from error
            if not unlocked:
                raise ValueError("PDF is encrypted and requires a password")

        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append(
                {
                    "page_number": page_number,
                    "text": page.extract_text() or "",
                }
            )
    except (PdfReadError, OSError) as error:
        raise ValueError(f"Could not read PDF: {path}") from error

    return {
        "file_path": str(path),
        "file_name": path.name,
        "page_count": len(pages),
        "text": "\n\f\n".join(page["text"] for page in pages),
        "pages": pages,
    }


def _validate_pdf_path(file_path: str) -> Path:
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("file_path must be a non-empty string")

    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {path}")
    with path.open("rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise ValueError(f"File does not have a valid PDF header: {path}")
    return path
