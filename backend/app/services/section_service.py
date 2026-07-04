"""Executive Summary section detection service.

Detects known section headings in extracted PDF text and splits
the content into structured sections with page ranges.
"""

import logging
import re

from app.schemas.document import PageContent, Section


logger = logging.getLogger(__name__)

# Known Executive Summary section patterns (case-insensitive).
# Order matters — matched top to bottom against each line.
_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Top Issue", re.compile(r"^\s*(?:top\s+iss?ue?|top\s+isu)\s*$", re.IGNORECASE)),
    ("Alert Issue", re.compile(r"^\s*(?:alert\s+iss?ue?|alert\s+isu)\s*$", re.IGNORECASE)),
    ("Isu Harian", re.compile(r"^\s*isu\s+harian\s*$", re.IGNORECASE)),
    ("Media Online", re.compile(r"^\s*media\s+online\s*$", re.IGNORECASE)),
    ("Media Sosial", re.compile(r"^\s*media\s+sosial\s*$", re.IGNORECASE)),
]


class SectionService:
    """Detects and splits Executive Summary sections from extracted text."""

    def detect(self, pages: list[PageContent]) -> list[Section]:
        """Detect sections across all pages.

        Scans each page line-by-line for known section headings.
        Text between headings is grouped into sections.

        Args:
            pages: List of extracted page content (1-indexed page numbers).

        Returns:
            List of detected sections with content and page ranges.
            If no sections are detected, returns a single "Unknown" section
            containing all text.
        """
        # Build a flat list of (line, page_number) tuples
        line_entries: list[tuple[str, int]] = []
        for page in pages:
            for line in page.text.splitlines():
                line_entries.append((line, page.page_number))

        # Find section boundaries
        boundaries: list[tuple[str, int]] = []  # (section_name, line_index)
        for idx, (line, _page_num) in enumerate(line_entries):
            matched_name = self._match_heading(line)
            if matched_name is not None:
                boundaries.append((matched_name, idx))

        if not boundaries:
            logger.info("No sections detected, returning full text as Unknown")
            full_text = "\n".join(line for line, _ in line_entries)
            page_numbers = [p.page_number for p in pages]
            return [Section(
                name="Unknown",
                content=full_text.strip(),
                page_start=min(page_numbers) if page_numbers else 1,
                page_end=max(page_numbers) if page_numbers else 1,
            )]

        sections: list[Section] = []
        for i, (name, start_idx) in enumerate(boundaries):
            # Content runs from the line after the heading to the next heading
            content_start = start_idx + 1
            content_end = (
                boundaries[i + 1][1] if i + 1 < len(boundaries) else len(line_entries)
            )

            content_lines = [
                line for line, _ in line_entries[content_start:content_end]
            ]
            page_nums = [
                page_num for _, page_num in line_entries[content_start:content_end]
            ]

            # Fall back to the heading's page if section is empty
            if not page_nums:
                _, heading_page = line_entries[start_idx]
                page_nums = [heading_page]

            sections.append(Section(
                name=name,
                content="\n".join(content_lines).strip(),
                page_start=min(page_nums),
                page_end=max(page_nums),
            ))

        # Merge sections with the same name to avoid redundant LLM calls.
        # E.g. three consecutive "Alert Issue" headings become one section.
        sections = self._merge_same_name_sections(sections)

        logger.info(
            "Sections detected: %s",
            [s.name for s in sections],
        )
        return sections

    def _merge_same_name_sections(self, sections: list[Section]) -> list[Section]:
        """Merge sections that share the same name into a single section.

        Combines their content and expands the page range.
        """
        if not sections:
            return sections

        merged: list[Section] = []
        groups: dict[str, list[Section]] = {}
        # Preserve order by tracking first occurrence
        order: list[str] = []

        for section in sections:
            if section.name not in groups:
                groups[section.name] = []
                order.append(section.name)
            groups[section.name].append(section)

        for name in order:
            group = groups[name]
            if len(group) == 1:
                merged.append(group[0])
            else:
                combined_content = "\n\n".join(s.content for s in group if s.content)
                page_start = min(s.page_start for s in group)
                page_end = max(s.page_end for s in group)
                merged.append(Section(
                    name=name,
                    content=combined_content,
                    page_start=page_start,
                    page_end=page_end,
                ))
                logger.info(
                    "Merged %d '%s' sections into one (pages %d-%d)",
                    len(group), name, page_start, page_end,
                )

        return merged

    def _match_heading(self, line: str) -> str | None:
        """Check if a line matches a known section heading.

        Args:
            line: A single line of text.

        Returns:
            The canonical section name if matched, None otherwise.
        """
        stripped = line.strip()
        if not stripped:
            return None

        for name, pattern in _SECTION_PATTERNS:
            if pattern.match(stripped):
                return name

        return None
