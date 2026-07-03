"""FastAPI application entry point.

Creates the app, registers routers, and configures startup logging.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.routers import documents, health


settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler — runs on startup and shutdown."""
    logger.info(
        "Application started: %s v%s",
        settings.app_name,
        settings.app_version,
    )
    logger.info("Ollama URL: %s", settings.ollama_url)
    logger.info("Default model: %s", settings.ollama_model)
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-assisted monitoring platform for DPR RI Executive Summary documents.",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["System"])
app.include_router(documents.router, tags=["Documents"])
