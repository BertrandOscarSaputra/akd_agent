"""API router for health, models, and chat endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
)
from app.services.ollama_service import OllamaService


logger = logging.getLogger(__name__)
router = APIRouter()

_settings = get_settings()
_ollama = OllamaService(_settings)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return application and Ollama connection status."""
    ollama_ok = await _ollama.health_check()
    return HealthResponse(
        status="ok",
        ollama_status="connected" if ollama_ok else "disconnected",
        version=_settings.app_version,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """Return available Ollama models."""
    try:
        raw_models = await _ollama.list_models()
        models = [ModelInfo(**m) for m in raw_models]
        return ModelsResponse(models=models)
    except Exception as exc:
        logger.error("Failed to fetch models: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve models from Ollama",
        ) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Forward a chat request to Ollama and return the response."""
    messages = [msg.model_dump() for msg in request.messages]
    try:
        result = await _ollama.chat(messages=messages, model=request.model)
        return ChatResponse(**result)
    except Exception as exc:
        logger.error("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Ollama chat request failed",
        ) from exc
