"""Unit tests for ReviewService."""

from app.schemas.issue import Issue
from app.services.review_service import ReviewService


def test_review_issues_flags_missing_date():
    service = ReviewService()
    issue = Issue(
        title="Test",
        description="Desc",
        sections=["Top Issue"],
        source_pages=[1],
        akd="Komisi I",
        confidence=0.9,
        akd_confidence=0.9,
        date=None,
    )
    
    service.review_issues([issue])
    
    assert "Missing date" in issue.review_flags


def test_review_issues_flags_missing_akd():
    service = ReviewService()
    issue = Issue(
        title="Test",
        description="Desc",
        sections=["Top Issue"],
        source_pages=[1],
        confidence=0.9,
        date="2026-07-03",
        akd=None,
    )
    
    service.review_issues([issue])
    
    assert "Missing AKD" in issue.review_flags


def test_review_issues_flags_low_confidence():
    service = ReviewService()
    issue = Issue(
        title="Test",
        description="Desc",
        sections=["Top Issue"],
        source_pages=[1],
        date="2026-07-03",
        akd="Komisi I",
        confidence=0.7,
        akd_confidence=0.7,
    )
    
    service.review_issues([issue])
    
    assert "Low extraction confidence" in issue.review_flags
    assert "Low AKD classification confidence" in issue.review_flags


def test_review_issues_flags_unknown_section():
    service = ReviewService()
    issue = Issue(
        title="Test",
        description="Desc",
        sections=["Unknown"],
        source_pages=[1],
        date="2026-07-03",
        akd="Komisi I",
        confidence=0.9,
        akd_confidence=0.9,
    )
    
    service.review_issues([issue])
    
    assert "Unknown section source" in issue.review_flags


def test_review_issues_flags_duplicate_titles():
    service = ReviewService()
    issues = [
        Issue(
            title="Korupsi E-KTP",
            description="Desc 1",
            sections=["Top Issue"],
            source_pages=[1],
            date="2026-07-03",
            akd="Komisi III",
            confidence=0.9,
            akd_confidence=0.9,
        ),
        Issue(
            title="Korupsi E-KTP ",
            description="Desc 2",
            sections=["Isu Harian"],
            source_pages=[2],
            date="2026-07-03",
            akd="Komisi III",
            confidence=0.9,
            akd_confidence=0.9,
        )
    ]
    
    service.review_issues(issues)
    
    assert "Duplicate title found in document" in issues[0].review_flags
    assert "Duplicate title found in document" in issues[1].review_flags


def test_review_issues_clean():
    service = ReviewService()
    issue = Issue(
        title="Valid Issue",
        description="Desc",
        sections=["Top Issue"],
        source_pages=[1],
        date="2026-07-03",
        akd="Komisi I",
        confidence=0.9,
        akd_confidence=0.9,
    )
    
    service.review_issues([issue])
    
    assert len(issue.review_flags) == 0
