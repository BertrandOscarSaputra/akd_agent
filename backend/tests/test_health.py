"""Tests for health, models, and chat endpoints.

Uses httpx AsyncClient with mocked OllamaService to test
endpoints without requiring a running Ollama instance.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_ok_when_ollama_connected(client: AsyncClient):
    """GET /health should return 200 with status ok when Ollama is reachable."""
    with patch(
        "app.routers.health._ollama.health_check",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ollama_status"] == "connected"
    assert "version" in data


@pytest.mark.anyio
async def test_health_returns_disconnected_when_ollama_down(client: AsyncClient):
    """GET /health should report disconnected when Ollama is unreachable."""
    with patch(
        "app.routers.health._ollama.health_check",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["ollama_status"] == "disconnected"


@pytest.mark.anyio
async def test_models_returns_model_list(client: AsyncClient):
    """GET /models should return a list of models from Ollama."""
    mock_models = [
        {"name": "qwen2.5:3b", "size": 1_900_000_000, "parameter_size": "3B"},
    ]
    with patch(
        "app.routers.health._ollama.list_models",
        new_callable=AsyncMock,
        return_value=mock_models,
    ):
        response = await client.get("/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "qwen2.5:3b"


@pytest.mark.anyio
async def test_models_returns_502_on_ollama_error(client: AsyncClient):
    """GET /models should return 502 when Ollama is unreachable."""
    with patch(
        "app.routers.health._ollama.list_models",
        new_callable=AsyncMock,
        side_effect=ConnectionError("Connection refused"),
    ):
        response = await client.get("/models")

    assert response.status_code == 502


@pytest.mark.anyio
async def test_chat_returns_response(client: AsyncClient):
    """POST /chat should forward messages to Ollama and return the reply."""
    mock_result = {
        "model": "qwen2.5:3b",
        "message": {"role": "assistant", "content": "Hello!"},
        "total_duration": 500_000_000,
    }
    with patch(
        "app.routers.health._ollama.chat",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        response = await client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "qwen2.5:3b"
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "Hello!"


@pytest.mark.anyio
async def test_chat_returns_502_on_ollama_error(client: AsyncClient):
    """POST /chat should return 502 when Ollama fails."""
    with patch(
        "app.routers.health._ollama.chat",
        new_callable=AsyncMock,
        side_effect=ConnectionError("Connection refused"),
    ):
        response = await client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )

    assert response.status_code == 502


@pytest.mark.anyio
async def test_chat_validates_empty_messages(client: AsyncClient):
    """POST /chat should reject an empty messages array."""
    response = await client.post("/chat", json={"messages": []})
    assert response.status_code == 422
