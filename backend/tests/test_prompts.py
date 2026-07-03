"""Unit tests for extraction prompts."""

from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_rules():
    """System prompt should contain the key rules."""
    assert "Extract EVERY distinct issue" in SYSTEM_PROMPT
    assert "Preserve the original wording" in SYSTEM_PROMPT
    assert "Preserve all dates exactly" in SYSTEM_PROMPT
    assert "ONLY valid JSON" in SYSTEM_PROMPT
    
    assert "title:" in SYSTEM_PROMPT
    assert "description:" in SYSTEM_PROMPT
    assert "date:" in SYSTEM_PROMPT
    assert "confidence:" in SYSTEM_PROMPT


def test_user_prompt_includes_section_content():
    """User prompt should include the provided section name and content."""
    prompt = build_user_prompt("Top Issue", "This is the content.")
    
    assert "Top Issue" in prompt
    assert "This is the content." in prompt
    assert "ONLY a JSON array" in prompt
