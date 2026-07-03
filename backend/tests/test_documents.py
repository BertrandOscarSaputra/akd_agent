"""Tests for PDF upload and document retrieval endpoints.

Generates synthetic test PDFs using PyMuPDF to avoid needing
external test fixtures.
"""

import io

import fitz
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_test_pdf(pages_text: list[str]) -> bytes:
    """Generate a minimal PDF with the given page texts.

    Args:
        pages_text: List of strings, one per page.

    Returns:
        PDF file content as bytes.
    """
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((72, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_sectioned_pdf() -> bytes:
    """Generate a test PDF with known Executive Summary sections."""
    content = [
        "Executive Summary\nDate: 2026-07-03\n\nTop Issue\nIsu korupsi di Kementerian X\nDetail tentang kasus.",
        "Alert Issue\nKeamanan perbatasan meningkat\nDetail tentang perbatasan.\n\nIsu Harian\nHarga beras naik 10%",
        "Media Online\nViralnya berita tentang DPR\nDetail berita.\n\nMedia Sosial\nTrending topic: #ReformasiDPR",
    ]
    return _make_test_pdf(content)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_upload_valid_pdf(client: AsyncClient):
    """POST /upload with a valid PDF should return 200 with document info."""
    pdf_bytes = _make_test_pdf(["Hello World\nPage 1 content"])
    response = await client.post(
        "/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["total_pages"] == 1
    assert data["id"]
    assert data["message"] == "PDF processed successfully"


@pytest.mark.anyio
async def test_upload_multi_page_pdf(client: AsyncClient):
    """POST /upload with a multi-page PDF should report correct page count."""
    pdf_bytes = _make_test_pdf(["Page 1", "Page 2", "Page 3"])
    response = await client.post(
        "/upload",
        files={"file": ("multi.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_pages"] == 3


@pytest.mark.anyio
async def test_upload_rejects_non_pdf(client: AsyncClient):
    """POST /upload should reject non-PDF files with 400."""
    response = await client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_rejects_empty_file(client: AsyncClient):
    """POST /upload should reject empty files with 400."""
    response = await client.post(
        "/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_rejects_fake_pdf_extension(client: AsyncClient):
    """POST /upload should reject files with .pdf extension but invalid content."""
    response = await client.post(
        "/upload",
        files={"file": ("fake.pdf", io.BytesIO(b"not really a pdf"), "application/pdf")},
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_get_document_after_upload(client: AsyncClient):
    """GET /documents/{id} should return the full document after upload."""
    pdf_bytes = _make_test_pdf(["Hello World"])
    upload_resp = await client.post(
        "/upload",
        files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    response = await client.get(f"/documents/{doc_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["filename"] == "doc.pdf"
    assert len(data["pages"]) == 1
    assert data["pages"][0]["page_number"] == 1
    assert "Hello World" in data["pages"][0]["text"]


@pytest.mark.anyio
async def test_get_nonexistent_document(client: AsyncClient):
    """GET /documents/{id} should return 404 for unknown IDs."""
    response = await client.get("/documents/nonexistent123")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_documents(client: AsyncClient):
    """GET /documents should return a list of uploaded documents."""
    pdf_bytes = _make_test_pdf(["Test"])
    await client.post(
        "/upload",
        files={"file": ("list_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    response = await client.get("/documents")

    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) >= 1


@pytest.mark.anyio
async def test_upload_with_sections(client: AsyncClient):
    """POST /upload with sectioned content should detect sections."""
    pdf_bytes = _make_sectioned_pdf()
    response = await client.post(
        "/upload",
        files={"file": ("summary.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sections_found"] >= 3
    section_names = data["section_names"]
    assert "Top Issue" in section_names
