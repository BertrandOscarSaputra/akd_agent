"""Unit tests for SectionService.

Tests section heading detection and content splitting in isolation.
"""

import pytest

from app.schemas.document import PageContent
from app.services.section_service import SectionService


@pytest.fixture
def service():
    return SectionService()


def _make_pages(texts: list[str]) -> list[PageContent]:
    """Create PageContent list from text strings (one per page)."""
    return [
        PageContent(page_number=i + 1, text=text, char_count=len(text))
        for i, text in enumerate(texts)
    ]


def test_detects_top_issue_heading(service: SectionService):
    """Should detect 'Top Issue' heading."""
    pages = _make_pages(["Top Issue\nKorupsi meningkat di kementerian."])
    sections = service.detect(pages)

    assert len(sections) == 1
    assert sections[0].name == "Top Issue"
    assert "Korupsi" in sections[0].content


def test_detects_top_isu_variant(service: SectionService):
    """Should detect 'Top Isu' as a variant of 'Top Issue'."""
    pages = _make_pages(["Top Isu\nMasalah infrastruktur."])
    sections = service.detect(pages)

    assert len(sections) == 1
    assert sections[0].name == "Top Issue"


def test_detects_multiple_sections(service: SectionService):
    """Should detect multiple sections in sequence."""
    text = "Top Issue\nIsu pertama.\n\nAlert Issue\nIsu kedua.\n\nIsu Harian\nIsu ketiga."
    pages = _make_pages([text])
    sections = service.detect(pages)

    assert len(sections) == 3
    assert sections[0].name == "Top Issue"
    assert sections[1].name == "Alert Issue"
    assert sections[2].name == "Isu Harian"


def test_detects_all_five_sections(service: SectionService):
    """Should detect all 5 known section types."""
    text = (
        "Top Issue\nContent 1\n"
        "Alert Issue\nContent 2\n"
        "Isu Harian\nContent 3\n"
        "Media Online\nContent 4\n"
        "Media Sosial\nContent 5"
    )
    pages = _make_pages([text])
    sections = service.detect(pages)

    names = [s.name for s in sections]
    assert names == ["Top Issue", "Alert Issue", "Isu Harian", "Media Online", "Media Sosial"]


def test_case_insensitive_matching(service: SectionService):
    """Should match headings regardless of case."""
    pages = _make_pages(["TOP ISSUE\nAll caps heading.\n\nmedia online\nLower case heading."])
    sections = service.detect(pages)

    assert len(sections) == 2
    assert sections[0].name == "Top Issue"
    assert sections[1].name == "Media Online"


def test_handles_text_without_sections(service: SectionService):
    """Should return a single 'Unknown' section when no headings found."""
    pages = _make_pages(["This is just plain text without any section headings."])
    sections = service.detect(pages)

    assert len(sections) == 1
    assert sections[0].name == "Unknown"
    assert "plain text" in sections[0].content


def test_preserves_page_ranges_across_pages(service: SectionService):
    """Should track correct page ranges when sections span multiple pages."""
    pages = _make_pages([
        "Top Issue\nContent starts on page 1",
        "More content on page 2\n\nAlert Issue\nNew section on page 2",
        "Alert issue continues on page 3",
    ])
    sections = service.detect(pages)

    assert len(sections) == 2
    assert sections[0].name == "Top Issue"
    assert sections[0].page_start == 1
    assert sections[0].page_end == 2
    assert sections[1].name == "Alert Issue"
    assert sections[1].page_start == 2
    assert sections[1].page_end == 3


def test_handles_empty_pages(service: SectionService):
    """Should handle pages with no text."""
    pages = _make_pages(["", "Top Issue\nSome content", ""])
    sections = service.detect(pages)

    assert len(sections) == 1
    assert sections[0].name == "Top Issue"


def test_section_content_excludes_heading(service: SectionService):
    """Section content should not include the heading line itself."""
    pages = _make_pages(["Top Issue\nActual content here."])
    sections = service.detect(pages)

    assert "Top Issue" not in sections[0].content
    assert "Actual content" in sections[0].content
