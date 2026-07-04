"""Issue extraction service using Ollama."""

import json
import logging
import time

from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt
from app.schemas.document import Section
from app.schemas.issue import Issue
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

# Maximum characters to send per LLM call. Sections larger than this
# are split, and smaller consecutive sections are batched together.
_MAX_CHARS_PER_CALL = 4000


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

        Batches small sections into a single LLM call to reduce total
        round-trips and speed up processing.

        Args:
            sections: List of document sections.
            model: Optional model name to override the default.

        Returns:
            Tuple of (list of extracted issues, total duration in ms).
        """
        all_issues: list[Issue] = []
        total_duration_ms = 0

        # Filter out empty sections
        valid_sections = [
            s for s in sections
            if s.content and len(s.content.strip()) >= 10
        ]

        if not valid_sections:
            logger.info("No valid sections to extract from")
            return [], 0

        # Batch small sections together to reduce LLM calls
        batches = self._create_batches(valid_sections)
        logger.info(
            "Batched %d sections into %d LLM calls",
            len(valid_sections), len(batches),
        )

        for batch in batches:
            # Combine section names and contents for the prompt
            combined_name = " + ".join(s.name for s in batch)
            combined_content = "\n\n---\n\n".join(
                f"[Section: {s.name}]\n{s.content}" for s in batch
            )

            user_prompt = build_user_prompt(combined_name, combined_content)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            issues, duration_ms = await self._extract_with_retry(
                messages, batch, model
            )
            all_issues.extend(issues)
            total_duration_ms += duration_ms

        logger.info(
            "Extraction complete: %d total issues from %d sections in %d ms",
            len(all_issues),
            len(valid_sections),
            total_duration_ms,
        )
        return all_issues, total_duration_ms

    def _create_batches(self, sections: list[Section]) -> list[list[Section]]:
        """Group sections into batches that fit within the character limit.

        Args:
            sections: List of valid sections.

        Returns:
            List of section batches, each fitting within _MAX_CHARS_PER_CALL.
        """
        batches: list[list[Section]] = []
        current_batch: list[Section] = []
        current_chars = 0

        for section in sections:
            section_chars = len(section.content)

            # If a single section exceeds the limit, it gets its own batch
            if section_chars > _MAX_CHARS_PER_CALL:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_chars = 0
                batches.append([section])
                continue

            # Check if adding this section would exceed the limit
            if current_chars + section_chars > _MAX_CHARS_PER_CALL:
                batches.append(current_batch)
                current_batch = [section]
                current_chars = section_chars
            else:
                current_batch.append(section)
                current_chars += section_chars

        if current_batch:
            batches.append(current_batch)

        return batches

    async def _extract_with_retry(
        self, messages: list[dict], sections: list[Section], model: str | None
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
                # Collect all pages across all sections in this batch
                all_pages = set()
                all_section_names = []
                for section in sections:
                    pages = list(range(section.page_start, section.page_end + 1))
                    all_pages.update(pages)
                    all_section_names.append(section.name)

                for item in parsed_data:
                    # Try to match the issue to a specific section from the batch
                    issue_section = item.get("section")
                    matched_sections = [issue_section] if issue_section in all_section_names else all_section_names
                    
                    issues.append(Issue(
                        title=item.get("title", "Untitled Issue"),
                        description=item.get("description", ""),
                        date=item.get("date"),
                        confidence=item.get("confidence", 1.0),
                        sections=matched_sections,
                        source_pages=sorted(list(all_pages)),
                    ))
                
                batch_names = ", ".join(s.name for s in sections)
                logger.info("Extracted %d issues from batch: [%s]", len(issues), batch_names)
                return issues, total_duration_ms

            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "JSON parsing failed on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                if attempt == self._max_retries:
                    logger.error("Max retries reached. Skipping batch.")
                    return [], total_duration_ms
                
                # Append the error as a user message to prompt correction
                messages.append({"role": "assistant", "content": response.get("message", {}).get("content", "")})
                messages.append({
                    "role": "user", 
                    "content": f"The response was not valid JSON. Please fix the formatting error: {str(exc)}. Return ONLY a JSON array."
                })
            except Exception as exc:
                logger.error("Ollama extraction failed: %s", exc)
                if attempt == self._max_retries:
                    return [], total_duration_ms

        return [], total_duration_ms
