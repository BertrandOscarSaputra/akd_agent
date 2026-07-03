"""Quality review service for detecting problems in extracted issues."""

import logging
from collections import Counter

from app.schemas.issue import Issue

logger = logging.getLogger(__name__)


class ReviewService:
    """Scans issues and attaches warning flags for potential problems."""

    def review_issues(self, issues: list[Issue]) -> None:
        """Analyze a list of issues and populate their review_flags.

        Args:
            issues: List of extracted issues to review.
        """
        if not issues:
            return

        logger.info("Running quality review on %d issues", len(issues))

        # Check for duplicate titles across the entire document
        title_counts = Counter(issue.title.lower().strip() for issue in issues)

        for issue in issues:
            flags = []

            if not issue.date:
                flags.append("Missing date")
            
            if not issue.akd:
                flags.append("Missing AKD")

            if issue.confidence < 0.8:
                flags.append("Low extraction confidence")
                
            if issue.akd_confidence > 0 and issue.akd_confidence < 0.8:
                flags.append("Low AKD classification confidence")
                
            if "Unknown" in issue.sections:
                flags.append("Unknown section source")

            title_normalized = issue.title.lower().strip()
            if title_counts[title_normalized] > 1:
                flags.append("Duplicate title found in document")

            issue.review_flags = flags

        flagged_count = sum(1 for i in issues if i.review_flags)
        logger.info(
            "Quality review complete. %d/%d issues flagged with warnings.",
            flagged_count, len(issues)
        )
