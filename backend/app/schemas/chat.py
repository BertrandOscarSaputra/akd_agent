"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field


# --- Chat ---

class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    model: str | None = Field(
        default=None,
        description="Ollama model name. Uses server default if omitted.",
    )
    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="Conversation messages"
    )


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    model: str
    message: ChatMessage
    total_duration: int | None = Field(
        default=None, description="Total inference duration in nanoseconds"
    )


# --- Health ---

class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = Field(..., description="Application status")
    ollama_status: str = Field(..., description="Ollama connection status")
    version: str = Field(..., description="Application version")


# --- Models ---

class ModelInfo(BaseModel):
    """Summary of a single Ollama model."""

    name: str
    size: int | None = None
    parameter_size: str | None = None


class ModelsResponse(BaseModel):
    """Response body for GET /models."""

    models: list[ModelInfo]
