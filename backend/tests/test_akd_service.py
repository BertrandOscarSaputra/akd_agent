"""Unit tests for AKDService."""

import json
from unittest.mock import AsyncMock, patch, mock_open

import pytest

from app.schemas.issue import Issue
from app.services.akd_service import AKDService
from app.services.ollama_service import OllamaService
from app.core.config import get_settings


MOCK_AKD_RULES = {
    "classification_rules": {
        "priority_order": ["Komisi I", "Komisi III", "Baleg"]
    },
    "akd": {
        "Komisi I": {
            "keywords": ["pertahanan", "tni", "luar negeri"]
        },
        "Komisi III": {
            "keywords": ["hukum", "polri", "kpk", "korupsi"]
        },
        "Baleg": {
            "keywords": ["undang-undang", "ruu", "legislasi"]
        }
    }
}


@pytest.fixture
def service():
    mock_ollama = AsyncMock()
    
    # We patch open to return our mock rules so it doesn't fail on CI if file is missing
    m = mock_open(read_data=json.dumps(MOCK_AKD_RULES))
    with patch("builtins.open", m):
        return AKDService(mock_ollama)


def test_rule_engine_clear_winner(service: AKDService):
    """Rule engine should assign AKD when there's a clear keyword match."""
    issue = Issue(
        title="RUU Pemberantasan Korupsi",
        description="KPK menangkap tersangka korupsi.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    akd, conf = service._rule_engine_classify(issue)
    
    assert akd == "Komisi III"
    assert conf > 0.0


def test_rule_engine_ambiguous(service: AKDService):
    """Rule engine should return None when there's a tie."""
    issue = Issue(
        title="TNI dan Polri kerjasama",
        description="Pertahanan dan hukum di daerah.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    akd, conf = service._rule_engine_classify(issue)
    
    assert akd is None
    assert conf == 0.0


def test_rule_engine_no_match(service: AKDService):
    """Rule engine should return None when no keywords match."""
    issue = Issue(
        title="Masalah pendidikan",
        description="Sekolah rusak.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    akd, conf = service._rule_engine_classify(issue)
    
    assert akd is None
    assert conf == 0.0


@pytest.mark.anyio
async def test_classify_issues_uses_rule_engine(service: AKDService):
    """classify_issues should use rule engine and skip AI if confident."""
    issue = Issue(
        title="Pembahasan RUU",
        description="Legislasi undang-undang baru.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    await service.classify_issues([issue])
    
    assert issue.akd == "Baleg"
    assert issue.akd_confidence > 0.0
    assert service._ollama.chat.call_count == 0


@pytest.mark.anyio
async def test_classify_issues_uses_ai_fallback(service: AKDService):
    """classify_issues should fallback to AI if rule engine fails."""
    issue = Issue(
        title="Masalah pendidikan",
        description="Sekolah rusak.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    # Mock AI response
    service._ollama.chat.return_value = {
        "message": {
            "content": '{"akd": "Komisi I", "confidence": 0.8}'
        }
    }
    
    await service.classify_issues([issue])
    
    assert issue.akd == "Komisi I"
    assert issue.akd_confidence == 0.8
    assert service._ollama.chat.call_count == 1


@pytest.mark.anyio
async def test_ai_fallback_retries_on_bad_json(service: AKDService):
    """AI fallback should retry if JSON is malformed."""
    issue = Issue(
        title="Unknown issue",
        description="Test.",
        sections=["Top Issue"],
        source_pages=[1]
    )
    
    service._ollama.chat.side_effect = [
        {"message": {"content": "I think it's Komisi I"}}, # Bad JSON
        {"message": {"content": '{"akd": "Komisi I", "confidence": 0.9}'}} # Good JSON
    ]
    
    await service.classify_issues([issue])
    
    assert issue.akd == "Komisi I"
    assert issue.akd_confidence == 0.9
    assert service._ollama.chat.call_count == 2
