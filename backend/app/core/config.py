"""Application settings via Pydantic BaseSettings.

Reads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the DPR Monitoring Agent."""

    app_name: str = "DPR Monitoring Agent"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_embedding_model: str = "nomic-embed-text"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
