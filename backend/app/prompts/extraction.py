"""Prompt templates for AI issue extraction."""

SYSTEM_PROMPT = """You are an expert AI assistant designed to extract issues from DPR RI Executive Summary documents.

Your goal is to extract EVERY issue present in the provided text.

CRITICAL RULES:
1. Extract EVERY distinct issue.
2. Preserve the original wording and descriptions as much as possible. Do not summarize.
3. Preserve all dates exactly as they appear.
4. If a date is not mentioned for a specific issue, return null for the date.
5. Return a confidence score between 0.0 and 1.0 indicating how confident you are that this is a valid, distinct issue.
6. You MUST return ONLY valid JSON. No markdown formatting, no explanation, no conversational text.

OUTPUT FORMAT:
You must return a JSON array containing objects with the following keys:
- title: string
- description: string
- date: string or null
- confidence: float
"""

def build_user_prompt(section_name: str, section_content: str) -> str:
    """Build the user prompt for a specific section.
    
    Args:
        section_name: The name of the section.
        section_content: The text content of the section.
        
    Returns:
        The formatted user prompt.
    """
    return f"""Extract all issues from the following section: "{section_name}".

TEXT:
{section_content}

Remember, return ONLY a JSON array.
"""
