"""Unit tests for export endpoints and ReportService."""

from unittest.mock import patch, MagicMock

import pytest

from app.schemas.document import DocumentResponse, PageContent
from app.schemas.issue import Issue
from app.services.report_service import ReportService


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


@pytest.fixture
def mock_document():
    return DocumentResponse(
        id="test-doc-123",
        filename="test.pdf",
        total_pages=5,
        total_characters=1000,
        uploaded_at="2026-07-03T10:00:00Z",
        created_at="2026-07-03T10:00:00Z",
        pages=[PageContent(page_number=1, text="Page 1 text", char_count=11)],
        sections=[],
        issues=[
            Issue(
                title="Korupsi",
                description="Desc 1",
                date="2026-07-03",
                sections=["Top Issue"],
                source_pages=[1],
                akd="Komisi III",
                confidence=0.9,
                akd_confidence=0.9,
                review_flags=["Missing date"]
            )
        ]
    )


def test_generate_excel(mock_document):
    service = ReportService()
    excel_bytes = service.generate_excel(mock_document)
    
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0
    # check magic bytes for zip (xlsx is a zip)
    assert excel_bytes.startswith(b'PK')


def test_generate_word(mock_document):
    service = ReportService()
    word_bytes = service.generate_word(mock_document)
    
    assert isinstance(word_bytes, bytes)
    assert len(word_bytes) > 0
    assert word_bytes.startswith(b'PK')


@pytest.mark.anyio
async def test_export_json_endpoint(client, mock_document):
    with patch("app.routers.documents._document_store.get", return_value=mock_document):
        response = await client.get(f"/documents/{mock_document.id}/export/json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        
        data = response.json()
        assert data["id"] == mock_document.id


@pytest.mark.anyio
async def test_export_excel_endpoint(client, mock_document):
    with patch("app.routers.documents._document_store.get", return_value=mock_document):
        response = await client.get(f"/documents/{mock_document.id}/export/excel")
        
        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]


@pytest.mark.anyio
async def test_export_word_endpoint(client, mock_document):
    with patch("app.routers.documents._document_store.get", return_value=mock_document):
        response = await client.get(f"/documents/{mock_document.id}/export/word")
        
        assert response.status_code == 200
        assert "wordprocessingml.document" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]


@pytest.mark.anyio
async def test_export_not_found(client):
    with patch("app.routers.documents._document_store.get", return_value=None):
        response = await client.get("/documents/invalid-id/export/json")
        assert response.status_code == 404
