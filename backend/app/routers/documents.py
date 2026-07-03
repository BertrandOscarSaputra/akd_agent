"""API router for PDF upload and document retrieval."""

import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    UploadResponse,
)
from app.services.document_store import DocumentStore
from app.services.pdf_service import PDFService
from app.services.section_service import SectionService


logger = logging.getLogger(__name__)
router = APIRouter()

_pdf_service = PDFService()
_section_service = SectionService()
_document_store = DocumentStore()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile) -> UploadResponse:
    """Upload an Executive Summary PDF for processing.

    Extracts text page-by-page and detects known sections.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        pages = _pdf_service.extract_text(file_bytes, file.filename)
    except ValueError as exc:
        logger.error("PDF validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sections = _section_service.detect(pages)
    doc = _document_store.save(file.filename, pages, sections)

    return UploadResponse(
        id=doc.id,
        filename=doc.filename,
        total_pages=doc.total_pages,
        total_characters=doc.total_characters,
        sections_found=len(sections),
        section_names=[s.name for s in sections],
        message="PDF processed successfully",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List all processed documents."""
    return DocumentListResponse(documents=_document_store.list_all())


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    """Retrieve a processed document by ID."""
    doc = _document_store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
