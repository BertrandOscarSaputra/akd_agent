"""Prompt templates for AI issue extraction."""

SYSTEM_PROMPT = """Extract issues from DPR RI Executive Summary text.

RULES:
1. Extract EVERY distinct issue.
2. Keep original wording. Do NOT summarize.
3. Keep dates exactly as written, or null if missing.
4. Return ONLY valid JSON array. No markdown, no explanation.
5. Keep descriptions SHORT (max 2 sentences).

FORMAT: JSON array of objects with keys: title, description, date, confidence
"""

def build_user_prompt(section_name: str, section_content: str) -> str:
    """Build the user prompt for a specific section.
    
    Args:
        section_name: The name of the section.
        section_content: The text content of the section.
        
    Returns:
        The formatted user prompt.
    """
    return f"""Section: "{section_name}"

TEXT:
{section_content}

Return ONLY a JSON array."""
