"""PDF text extraction service.

Uses PyMuPDF (fitz) to extract text from PDF files page by page.
Handles both text-based and OCR-ready PDFs.
"""

import logging

import fitz

from app.schemas.document import PageContent


logger = logging.getLogger(__name__)

# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"


class PDFService:
    """Extracts text content from PDF files."""

    def validate_pdf(self, file_bytes: bytes) -> None:
        """Validate that the file is a real PDF.

        Args:
            file_bytes: Raw file content.

        Raises:
            ValueError: If the file is not a valid PDF.
        """
        if not file_bytes.startswith(_PDF_MAGIC):
            raise ValueError("File is not a valid PDF")

    def extract_text(self, file_bytes: bytes, filename: str) -> list[PageContent]:
        """Extract text from a PDF file, page by page.

        Args:
            file_bytes: Raw PDF file content.
            filename: Original filename (for logging).

        Returns:
            List of PageContent with 1-indexed page numbers.

        Raises:
            ValueError: If the file is not a valid PDF or has no pages.
        """
        self.validate_pdf(file_bytes)

        pages: list[PageContent] = []
        total_chars = 0

        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            for page in doc:
                text = page.get_text(sort=True)
                char_count = len(text)
                total_chars += char_count

                pages.append(PageContent(
                    page_number=page.number + 1,
                    text=text,
                    char_count=char_count,
                ))

        logger.info(
            "PDF extracted: %s, pages=%d, chars=%d",
            filename,
            len(pages),
            total_chars,
        )

        return pages
