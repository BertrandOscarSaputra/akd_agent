"""Pydantic schemas for extracted issues."""

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """An issue extracted from a document section."""

    title: str = Field(..., description="A short, concise title for the issue")
    description: str = Field(..., description="Detailed description, preserving original wording")
    date: str | None = Field(default=None, description="Date mentioned in the issue, if any")
    sections: list[str] = Field(..., description="The sections this issue was extracted from")
    confidence: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the extraction (0.0 to 1.0)"
    )
    source_pages: list[int] = Field(..., description="List of page numbers where this issue was found")


class ExtractionRequest(BaseModel):
    """Request body for POST /extract/{document_id}."""

    model: str | None = Field(
        default=None,
        description="Ollama model name to use for extraction. Uses server default if omitted.",
    )
    deduplicate: bool = Field(
        default=True,
        description="Whether to detect and merge duplicate issues.",
    )


class ExtractionResponse(BaseModel):
    """Response body for POST /extract/{document_id}."""

    document_id: str
    total_issues: int
    issues: list[Issue]
    sections_processed: int
    extraction_duration_ms: int
