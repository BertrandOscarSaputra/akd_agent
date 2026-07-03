"""Unit tests for DuplicateService."""

from unittest.mock import AsyncMock

import pytest

from app.schemas.issue import Issue
from app.services.duplicate_service import DuplicateService


@pytest.fixture
def service():
    # We mock OllamaService since we inject it
    mock_ollama = AsyncMock()
    # default threshold is 0.85
    return DuplicateService(mock_ollama)


@pytest.mark.anyio
async def test_detects_and_merges_identical_issues(service: DuplicateService):
    """Should merge issues with high similarity."""
    
    issues = [
        Issue(
            title="Korupsi",
            description="Terjadi korupsi.",
            date="2026-07-03",
            sections=["Top Issue"],
            confidence=0.9,
            source_pages=[1],
        ),
        Issue(
            title="Masalah Korupsi",
            description="Terdapat kasus korupsi yang sedang ditangani.",
            date="2026-07-01",
            sections=["Isu Harian"],
            confidence=0.8,
            source_pages=[2],
        ),
    ]

    # Mock embeddings to be highly similar (e.g., identical vectors)
    service._ollama.generate_embeddings.side_effect = [
        [1.0, 0.0],
        [1.0, 0.0],
    ]

    merged = await service.detect_and_merge(issues)

    assert len(merged) == 1
    
    result = merged[0]
    # Longest description
    assert result.description == "Terdapat kasus korupsi yang sedang ditangani."
    assert result.title == "Masalah Korupsi"
    
    # Earliest date
    assert result.date == "2026-07-01"
    
    # Combined sections
    assert "Top Issue" in result.sections
    assert "Isu Harian" in result.sections
    
    # Combined pages
    assert 1 in result.source_pages
    assert 2 in result.source_pages
    
    # Max confidence
    assert result.confidence == 0.9


@pytest.mark.anyio
async def test_does_not_merge_unrelated_issues(service: DuplicateService):
    """Should not merge issues with similarity below threshold."""
    
    issues = [
        Issue(
            title="Korupsi",
            description="Terjadi korupsi.",
            date="2026-07-03",
            sections=["Top Issue"],
            confidence=0.9,
            source_pages=[1],
        ),
        Issue(
            title="Kecelakaan lalu lintas",
            description="Terjadi kecelakaan.",
            date="2026-07-01",
            sections=["Isu Harian"],
            confidence=0.8,
            source_pages=[2],
        ),
    ]

    # Mock embeddings to be orthogonal (similarity 0)
    service._ollama.generate_embeddings.side_effect = [
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    merged = await service.detect_and_merge(issues)

    assert len(merged) == 2


@pytest.mark.anyio
async def test_merges_multiple_issues_in_cluster(service: DuplicateService):
    """Should merge multiple issues in the same similarity cluster."""
    
    issues = [
        Issue(title="A", description="A", date=None, sections=["A"], confidence=1.0, source_pages=[1]),
        Issue(title="B", description="B", date=None, sections=["B"], confidence=1.0, source_pages=[1]),
        Issue(title="C", description="C", date=None, sections=["C"], confidence=1.0, source_pages=[1]),
    ]

    # A is similar to B, B is similar to C -> all should merge into 1
    service._ollama.generate_embeddings.side_effect = [
        [1.0, 1.0, 0.0], # A
        [1.0, 1.0, 1.0], # B
        [0.0, 1.0, 1.0], # C
    ]
    # Similarity A-B = 2 / (sqrt(2)*sqrt(3)) = 2 / 2.449 = 0.816 (Below threshold 0.85!)
    # Let's make them more similar
    service._ollama.generate_embeddings.side_effect = [
        [1.0, 0.1, 0.1], # A
        [1.0, 0.2, 0.1], # B
        [1.0, 0.1, 0.2], # C
    ]

    merged = await service.detect_and_merge(issues)

    assert len(merged) == 1
    result = merged[0]
    assert "A" in result.sections
    assert "B" in result.sections
    assert "C" in result.sections


@pytest.mark.anyio
async def test_handles_empty_issues_list(service: DuplicateService):
    """Should return empty list when given empty list."""
    merged = await service.detect_and_merge([])
    assert len(merged) == 0


@pytest.mark.anyio
async def test_handles_embedding_generation_failure(service: DuplicateService):
    """Should not crash if embedding generation fails, treats issue as unique."""
    
    issues = [
        Issue(title="A", description="A", date=None, sections=["A"], confidence=1.0, source_pages=[1]),
        Issue(title="B", description="B", date=None, sections=["B"], confidence=1.0, source_pages=[1]),
    ]

    # First succeeds, second fails
    service._ollama.generate_embeddings.side_effect = [
        [1.0, 0.0],
        Exception("Ollama error"),
    ]

    merged = await service.detect_and_merge(issues)
    assert len(merged) == 2
