"""Ollama client service.

Thin wrapper around the ollama Python library. Keeps all Ollama
interaction in one place so the rest of the app stays decoupled.
"""

import logging

from ollama import Client, ResponseError

from app.core.config import Settings


logger = logging.getLogger(__name__)


class OllamaService:
    """Handles communication with the Ollama API."""

    def __init__(self, settings: Settings) -> None:
        self._client = Client(host=settings.ollama_url)
        self._default_model = settings.ollama_model

    async def health_check(self) -> bool:
        """Check if Ollama is reachable.

        Returns:
            True if Ollama responds, False otherwise.
        """
        try:
            self._client.list()
            return True
        except Exception:
            logger.error("Ollama health check failed")
            return False

    async def list_models(self) -> list[dict]:
        """Return available models from Ollama.

        Returns:
            List of model info dicts with name, size, parameter_size.
        """
        try:
            response = self._client.list()
            models = []
            for model in response.models:
                models.append({
                    "name": model.model,
                    "size": getattr(model, "size", None),
                    "parameter_size": getattr(
                        getattr(model, "details", None),
                        "parameter_size",
                        None,
                    ),
                })
            return models
        except ResponseError as exc:
            logger.error("Failed to list models: %s", exc)
            raise
        except Exception as exc:
            logger.error("Ollama connection error: %s", exc)
            raise

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> dict:
        """Send a chat request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name override. Uses default if None.

        Returns:
            Dict with model, message, and total_duration.
        """
        target_model = model or self._default_model
        try:
            response = self._client.chat(
                model=target_model,
                messages=messages,
            )
            return {
                "model": response.model,
                "message": {
                    "role": response.message.role,
                    "content": response.message.content,
                },
                "total_duration": getattr(response, "total_duration", None),
            }
        except ResponseError as exc:
            logger.error("Ollama chat failed for model %s: %s", target_model, exc)
            raise
        except Exception as exc:
            logger.error("Ollama connection error during chat: %s", exc)
            raise

    async def generate_embeddings(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """Generate embeddings for a piece of text.

        Args:
            text: The text to embed.
            model: Model name override. Uses default embedding model if None.

        Returns:
            List of floats representing the embedding vector.
        """
        from app.core.config import get_settings
        # Get settings here to avoid circular import if config needs something
        target_model = model or get_settings().ollama_embedding_model
        
        try:
            response = self._client.embeddings(
                model=target_model,
                prompt=text,
            )
            return response.embedding
        except ResponseError as exc:
            logger.error("Ollama embeddings failed for model %s: %s", target_model, exc)
            raise
        except Exception as exc:
            logger.error("Ollama connection error during embeddings: %s", exc)
            raise
