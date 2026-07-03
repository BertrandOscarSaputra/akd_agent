"""Pydantic schemas for PDF document processing."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.issue import Issue


class PageContent(BaseModel):
    """Extracted text from a single PDF page."""

    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted text content")
    char_count: int = Field(..., description="Number of characters on this page")


class Section(BaseModel):
    """A detected section within the Executive Summary."""

    name: str = Field(..., description="Section heading name")
    content: str = Field(..., description="Full text content of the section")
    page_start: int = Field(..., description="Starting page number (1-indexed)")
    page_end: int = Field(..., description="Ending page number (1-indexed)")


class UploadResponse(BaseModel):
    """Response body for POST /upload."""

    id: str = Field(..., description="Unique document identifier")
    filename: str
    total_pages: int
    total_characters: int
    sections_found: int
    section_names: list[str]
    message: str


class DocumentSummary(BaseModel):
    """Brief summary of a stored document."""

    id: str
    filename: str
    total_pages: int
    sections_found: int
    created_at: datetime


class DocumentResponse(BaseModel):
    """Full response for GET /documents/{id}."""

    id: str
    filename: str
    total_pages: int
    total_characters: int
    pages: list[PageContent]
    sections: list[Section]
    issues: list['Issue'] = Field(default_factory=list)
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Response body for GET /documents."""

    documents: list[DocumentSummary]
