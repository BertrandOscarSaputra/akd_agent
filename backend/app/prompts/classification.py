"""Prompt templates for AI AKD classification fallback."""

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert AI assistant for DPR RI (Dewan Perwakilan Rakyat Republik Indonesia).

Your task is to classify a given issue into EXACTLY ONE Alat Kelengkapan Dewan (AKD).
The AKD represents the parliamentary committee or body responsible for handling the issue.

CRITICAL RULES:
1. You MUST assign EXACTLY ONE AKD from the provided list.
2. If the issue is ambiguous, assign the single most relevant AKD.
3. Provide a confidence score between 0.0 and 1.0.
4. You MUST return ONLY valid JSON. No markdown formatting, no explanation, no conversational text.

OUTPUT FORMAT:
You must return a JSON object with the following keys:
- akd: string (Must be exactly one of the provided AKD names)
- confidence: float
"""

def build_classification_user_prompt(issue_title: str, issue_description: str, akd_list: list[str]) -> str:
    """Build the user prompt for classifying an issue.
    
    Args:
        issue_title: The title of the issue.
        issue_description: The description of the issue.
        akd_list: List of valid AKD names to choose from.
        
    Returns:
        The formatted user prompt.
    """
    valid_akds = "\n- ".join(akd_list)
    return f"""Classify the following issue into one of these AKDs:

- {valid_akds}

ISSUE TITLE: {issue_title}
ISSUE DESCRIPTION: {issue_description}

Remember, return ONLY a JSON object containing 'akd' and 'confidence'.
"""
