"""In-memory document store.

Simple dict-based storage for processed documents.
Adequate for Sprint 2 — will be replaced by a real DB in later milestones.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.schemas.document import (
    DocumentResponse,
    DocumentSummary,
    PageContent,
    Section,
)


logger = logging.getLogger(__name__)


class DocumentStore:
    """Stores processed documents in memory."""

    def __init__(self) -> None:
        self._documents: dict[str, DocumentResponse] = {}

    def save(
        self,
        filename: str,
        pages: list[PageContent],
        sections: list[Section],
    ) -> DocumentResponse:
        """Save a processed document.

        Args:
            filename: Original PDF filename.
            pages: Extracted page contents.
            sections: Detected sections.

        Returns:
            The stored DocumentResponse with generated ID.
        """
        doc_id = uuid.uuid4().hex[:12]
        total_chars = sum(p.char_count for p in pages)

        doc = DocumentResponse(
            id=doc_id,
            filename=filename,
            total_pages=len(pages),
            total_characters=total_chars,
            pages=pages,
            sections=sections,
            created_at=datetime.now(timezone.utc),
        )

        self._documents[doc_id] = doc
        logger.info("Document saved: id=%s, filename=%s", doc_id, filename)
        return doc

    def get(self, document_id: str) -> DocumentResponse | None:
        """Retrieve a document by ID.

        Args:
            document_id: The document's unique identifier.

        Returns:
            The document if found, None otherwise.
        """
        return self._documents.get(document_id)

    def list_all(self) -> list[DocumentSummary]:
        """Return summaries of all stored documents.

        Returns:
            List of document summaries, newest first.
        """
        summaries = [
            DocumentSummary(
                id=doc.id,
                filename=doc.filename,
                total_pages=doc.total_pages,
                sections_found=len(doc.sections),
                created_at=doc.created_at,
            )
            for doc in self._documents.values()
        ]
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries
