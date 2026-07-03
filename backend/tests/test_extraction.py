"""Tests for the extraction service and endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.document import Section
from app.services.extraction_service import ExtractionService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_sections():
    return [
        Section(
            name="Top Issue",
            content="Isu pertama. Terjadi korupsi.",
            page_start=1,
            page_end=1,
        )
    ]


@pytest.mark.anyio
async def test_extract_issues_from_document(client: AsyncClient, mock_sections: list[Section]):
    """POST /extract should process document sections and return issues."""
    
    # Need to create a document first to extract from
    from app.routers.documents import _document_store
    doc = _document_store.save("test.pdf", [], mock_sections)
    
    mock_ollama_response = {
        "model": "qwen2.5:3b",
        "message": {
            "role": "assistant",
            "content": '[{"title": "Korupsi", "description": "Terjadi korupsi.", "date": null, "confidence": 0.9}]'
        },
        "total_duration": 1000,
    }
    
    with patch(
        "app.services.extraction_service.OllamaService.chat",
        new_callable=AsyncMock,
        return_value=mock_ollama_response,
    ), patch(
        "app.services.duplicate_service.OllamaService.generate_embeddings",
        new_callable=AsyncMock,
        return_value=[0.1, 0.2, 0.3],
    ):
        response = await client.post(
            f"/extract/{doc.id}",
            json={"model": "qwen2.5:3b"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc.id
    assert data["total_issues"] == 1
    assert data["sections_processed"] == 1
    
    issue = data["issues"][0]
    assert issue["title"] == "Korupsi"
    assert "Top Issue" in issue["sections"]
    assert issue["confidence"] == 0.9
    assert 1 in issue["source_pages"]


@pytest.mark.anyio
async def test_extract_nonexistent_document(client: AsyncClient):
    """POST /extract should return 404 for unknown IDs."""
    response = await client.post("/extract/nonexistent123", json={})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_extract_handles_malformed_json(mock_sections: list[Section]):
    """ExtractionService should retry when JSON is malformed."""
    
    # First call returns bad JSON, second call returns good JSON
    mock_responses = [
        {
            "model": "qwen2.5:3b",
            "message": {"role": "assistant", "content": "I found some issues: [{bad json"},
        },
        {
            "model": "qwen2.5:3b",
            "message": {
                "role": "assistant", 
                "content": '[{"title": "Fixed", "description": "Desc", "date": null, "confidence": 1.0}]'
            },
        },
    ]
    
    mock_chat = AsyncMock(side_effect=mock_responses)
    
    from app.services.ollama_service import OllamaService
    from app.core.config import get_settings
    
    service = ExtractionService(OllamaService(get_settings()))
    
    with patch.object(service._ollama, "chat", mock_chat):
        issues, _ = await service.extract_from_sections(mock_sections)
        
    assert len(issues) == 1
    assert issues[0].title == "Fixed"
    assert mock_chat.call_count == 2


@pytest.mark.anyio
async def test_extract_skips_empty_sections():
    """ExtractionService should skip empty sections."""
    sections = [
        Section(
            name="Empty Issue",
            content="   \n  ", # Too short/empty
            page_start=1,
            page_end=1,
        )
    ]
    
    mock_chat = AsyncMock()
    
    from app.services.ollama_service import OllamaService
    from app.core.config import get_settings
    
    service = ExtractionService(OllamaService(get_settings()))
    
    with patch.object(service._ollama, "chat", mock_chat):
        issues, _ = await service.extract_from_sections(sections)
        
    assert len(issues) == 0
    assert mock_chat.call_count == 0
