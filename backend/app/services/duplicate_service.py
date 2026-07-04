"""Duplicate detection and merging service.

Uses semantic embeddings to find and merge identical or similar issues
that were extracted from different sections.
"""

import logging
import math

from app.schemas.issue import Issue
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


class DuplicateService:
    """Detects and merges duplicate issues."""

    def __init__(
        self,
        ollama_service: OllamaService,
        similarity_threshold: float = 0.85,
    ) -> None:
        """Initialize the duplicate service.

        Args:
            ollama_service: Configured Ollama API client wrapper.
            similarity_threshold: Cosine similarity threshold to consider issues as duplicates.
        """
        self._ollama = ollama_service
        self._threshold = similarity_threshold

    async def detect_and_merge(self, issues: list[Issue]) -> list[Issue]:
        """Detect and merge duplicate issues.

        Args:
            issues: List of raw extracted issues.

        Returns:
            List of merged, unique issues.
        """
        if len(issues) <= 1:
            return issues

        logger.info("Starting duplicate detection for %d issues", len(issues))

        # 1. Generate embeddings for all issues
        embeddings = []
        for issue in issues:
            text_to_embed = f"{issue.title}\n{issue.description}"
            try:
                emb = await self._ollama.generate_embeddings(text_to_embed)
                embeddings.append(emb)
            except Exception as exc:
                logger.warning(
                    "Failed to generate embedding for issue '%s', treating as unique: %s",
                    issue.title,
                    exc,
                )
                embeddings.append([]) # Empty embedding will have 0 similarity

        # 2. Find connected components (groups of duplicates)
        # Using a simple disjoint-set / union-find approach or just adjacency
        n = len(issues)
        parent = list(range(n))

        def find(i: int) -> int:
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i: int, j: int) -> None:
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        for i in range(n):
            for j in range(i + 1, n):
                if not embeddings[i] or not embeddings[j]:
                    continue
                
                sim = _cosine_similarity(embeddings[i], embeddings[j])
                if sim >= self._threshold:
                    logger.info(
                        "Found duplicate (sim=%.2f): '%s' and '%s'",
                        sim,
                        issues[i].title,
                        issues[j].title,
                    )
                    union(i, j)

        # 3. Group issues by their root parent
        groups: dict[int, list[Issue]] = {}
        for i in range(n):
            root = find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(issues[i])

        # 4. Merge each group
        merged_issues = []
        for group in groups.values():
            if len(group) == 1:
                merged_issues.append(group[0])
            else:
                merged_issues.append(self._merge_issues(group))

        logger.info(
            "Duplicate detection complete. Reduced %d issues to %d",
            len(issues),
            len(merged_issues),
        )
        return merged_issues

    def _merge_issues(self, duplicates: list[Issue]) -> Issue:
        """Merge a group of duplicate issues into a single issue.

        Rules:
        - Keep longest description.
        - Keep title of the issue with the longest description.
        - Keep earliest date.
        - Combine sections and pages (unique).
        - Keep max confidence.
        """
        # Find the issue with the longest description
        primary_issue = max(duplicates, key=lambda i: len(i.description))

        # Find earliest date (simple string comparison works for YYYY-MM-DD, 
        # but we also need to handle None)
        dates = [i.date for i in duplicates if i.date]
        earliest_date = min(dates) if dates else None

        # Combine unique sections
        sections_set = set()
        for i in duplicates:
            sections_set.update(i.sections)
        
        # Combine unique pages
        pages_set = set()
        for i in duplicates:
            pages_set.update(i.source_pages)

        # Max confidence
        max_confidence = max(i.confidence for i in duplicates)

        return Issue(
            title=primary_issue.title,
            description=primary_issue.description,
            date=earliest_date,
            sections=sorted(list(sections_set)),
            confidence=max_confidence,
            source_pages=sorted(list(pages_set)),
        )

    def _fast_title_dedup(self, issues: list[Issue]) -> list[Issue]:
        """Quick dedup for small lists using normalized title comparison.

        Avoids the cost of embedding generation when there are only a few
        issues.
        """
        groups: dict[str, list[Issue]] = {}
        for issue in issues:
            key = issue.title.lower().strip()
            if key not in groups:
                groups[key] = []
            groups[key].append(issue)

        merged = []
        for group in groups.values():
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged.append(self._merge_issues(group))

        if len(merged) < len(issues):
            logger.info(
                "Fast title dedup reduced %d issues to %d",
                len(issues), len(merged),
            )
        return merged
