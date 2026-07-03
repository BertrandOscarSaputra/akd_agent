"""Issue extraction service using Ollama."""

import json
import logging
import time

from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt
from app.schemas.document import Section
from app.schemas.issue import Issue
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Orchestrates AI-based issue extraction from document sections."""

    def __init__(self, ollama_service: OllamaService) -> None:
        """Initialize the extraction service.
        
        Args:
            ollama_service: Configured Ollama API client wrapper.
        """
        self._ollama = ollama_service
        self._max_retries = 2

    async def extract_from_sections(
        self, sections: list[Section], model: str | None = None
    ) -> tuple[list[Issue], int]:
        """Extract issues from a list of sections.

        Args:
            sections: List of document sections.
            model: Optional model name to override the default.

        Returns:
            Tuple of (list of extracted issues, total duration in ms).
        """
        all_issues: list[Issue] = []
        total_duration_ms = 0

        for section in sections:
            # Skip sections with no meaningful content
            if not section.content or len(section.content.strip()) < 10:
                logger.info("Skipping empty section: %s", section.name)
                continue

            user_prompt = build_user_prompt(section.name, section.content)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            issues, duration_ms = await self._extract_with_retry(
                messages, section, model
            )
            all_issues.extend(issues)
            total_duration_ms += duration_ms

        logger.info(
            "Extraction complete: %d total issues from %d sections in %d ms",
            len(all_issues),
            len(sections),
            total_duration_ms,
        )
        return all_issues, total_duration_ms

    async def _extract_with_retry(
        self, messages: list[dict], section: Section, model: str | None
    ) -> tuple[list[Issue], int]:
        """Call Ollama and parse JSON, with retries on failure.
        
        Returns:
            Tuple of (list of issues, duration in ms).
        """
        total_duration_ms = 0

        for attempt in range(self._max_retries + 1):
            try:
                start_time = time.monotonic()
                response = await self._ollama.chat(messages=messages, model=model)
                end_time = time.monotonic()
                
                duration_ms = int((end_time - start_time) * 1000)
                total_duration_ms += duration_ms
                
                content = response["message"]["content"]
                
                # Try to clean up markdown block if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                
                content = content.strip()
                
                parsed_data = json.loads(content)
                if not isinstance(parsed_data, list):
                    raise ValueError("Expected a JSON array")
                
                issues = []
                for item in parsed_data:
                    # Collect all pages this section spans
                    pages = list(range(section.page_start, section.page_end + 1))
                    
                    issues.append(Issue(
                        title=item.get("title", "Untitled Issue"),
                        description=item.get("description", ""),
                        date=item.get("date"),
                        confidence=item.get("confidence", 1.0),
                        sections=[section.name],
                        source_pages=pages,
                    ))
                
                logger.info("Extracted %d issues from section: %s", len(issues), section.name)
                return issues, total_duration_ms

            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "JSON parsing failed on attempt %d for section %s: %s",
                    attempt + 1,
                    section.name,
                    exc,
                )
                if attempt == self._max_retries:
                    logger.error("Max retries reached for section %s. Skipping.", section.name)
                    return [], total_duration_ms
                
                # Append the error as a user message to prompt correction
                messages.append({"role": "assistant", "content": response.get("message", {}).get("content", "")})
                messages.append({
                    "role": "user", 
                    "content": f"The response was not valid JSON. Please fix the formatting error: {str(exc)}. Return ONLY a JSON array."
                })
            except Exception as exc:
                logger.error("Ollama extraction failed for section %s: %s", section.name, exc)
                if attempt == self._max_retries:
                    return [], total_duration_ms

        return [], total_duration_ms
