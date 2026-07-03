"""AKD Classification service.

Uses a hybrid approach to classify issues into EXACTLY ONE AKD:
1. Rule Engine: Fast keyword matching based on akd_rules.json.
2. AI Fallback: Uses Ollama if the rule engine is ambiguous or finds no matches.
"""

import json
import logging
import os
import time

from app.core.config import get_settings
from app.prompts.classification import CLASSIFICATION_SYSTEM_PROMPT, build_classification_user_prompt
from app.schemas.issue import Issue
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class AKDService:
    """Classifies issues into AKDs."""

    def __init__(self, ollama_service: OllamaService) -> None:
        """Initialize the AKD service and load rules."""
        self._ollama = ollama_service
        self._settings = get_settings()
        
        # Load AKD rules
        rules_path = os.path.join(self._settings.knowledge_dir, "akd_rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                self._rules_data = json.load(f)
            self._akd_list = self._rules_data.get("classification_rules", {}).get("priority_order", [])
            self._akd_definitions = self._rules_data.get("akd", {})
            logger.info("Loaded %d AKD rules from %s", len(self._akd_definitions), rules_path)
        except Exception as exc:
            logger.error("Failed to load AKD rules from %s: %s", rules_path, exc)
            self._akd_list = []
            self._akd_definitions = {}

    async def classify_issues(self, issues: list[Issue], model: str | None = None) -> None:
        """Classify a list of issues in place.

        Args:
            issues: List of issues to classify.
            model: Optional Ollama model override for the AI fallback.
        """
        if not self._akd_list:
            logger.warning("No AKD rules loaded. Skipping classification.")
            return

        for issue in issues:
            # 1. Try Rule Engine
            akd, confidence = self._rule_engine_classify(issue)
            
            if akd:
                logger.info(
                    "Rule Engine classified issue '%s' as %s (confidence: %.2f)",
                    issue.title, akd, confidence
                )
                issue.akd = akd
                issue.akd_confidence = confidence
                continue

            # 2. AI Fallback
            logger.info("Rule Engine ambiguous for issue '%s', using AI fallback", issue.title)
            akd, confidence = await self._ai_classify(issue, model)
            
            if akd:
                logger.info(
                    "AI classified issue '%s' as %s (confidence: %.2f)",
                    issue.title, akd, confidence
                )
                issue.akd = akd
                issue.akd_confidence = confidence
            else:
                logger.warning("Failed to classify issue '%s'", issue.title)

    def _rule_engine_classify(self, issue: Issue) -> tuple[str | None, float]:
        """Classify an issue using keyword matching.

        Returns:
            Tuple of (AKD name, confidence) if a clear match is found,
            else (None, 0.0).
        """
        text = f"{issue.title} {issue.description}".lower()
        
        scores: dict[str, int] = {}
        
        for akd_name, definition in self._akd_definitions.items():
            keywords = definition.get("keywords", [])
            score = 0
            for kw in keywords:
                # Count occurrences of the keyword in the text
                score += text.count(kw.lower())
            
            if score > 0:
                scores[akd_name] = score

        if not scores:
            return None, 0.0

        # Sort AKDs by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        top_akd, top_score = sorted_scores[0]
        
        # If there's only one match, return it
        if len(sorted_scores) == 1:
            return top_akd, 0.8  # 0.8 confidence for a single keyword match
            
        runner_up_akd, runner_up_score = sorted_scores[1]
        
        # We need a clear winner (e.g. score must be strictly greater)
        if top_score > runner_up_score:
            # Calculate a confidence score based on the margin
            total_hits = sum(scores.values())
            confidence = min(0.95, (top_score / total_hits) + 0.1)
            return top_akd, confidence
            
        # Ambiguous (tie)
        return None, 0.0

    async def _ai_classify(self, issue: Issue, model: str | None) -> tuple[str | None, float]:
        """Classify an issue using Ollama.

        Returns:
            Tuple of (AKD name, confidence).
        """
        user_prompt = build_classification_user_prompt(
            issue_title=issue.title,
            issue_description=issue.description,
            akd_list=self._akd_list,
        )
        
        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                response = await self._ollama.chat(messages=messages, model=model)
                content = response["message"]["content"]
                
                # Try to clean up markdown block if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                
                content = content.strip()
                
                parsed_data = json.loads(content)
                if not isinstance(parsed_data, dict):
                    raise ValueError("Expected a JSON object")
                
                akd = parsed_data.get("akd")
                confidence = float(parsed_data.get("confidence", 0.0))
                
                if akd not in self._akd_list:
                    raise ValueError(f"Returned AKD '{akd}' is not in the valid list")
                    
                return akd, confidence

            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "AI Classification parsing failed on attempt %d for issue '%s': %s",
                    attempt + 1, issue.title, exc
                )
                if attempt == max_retries:
                    return None, 0.0
                
                messages.append({"role": "assistant", "content": response.get("message", {}).get("content", "")})
                messages.append({
                    "role": "user", 
                    "content": f"The response was invalid: {str(exc)}. Please return ONLY a valid JSON object with 'akd' (from the list) and 'confidence'."
                })
            except Exception as exc:
                logger.error("Ollama classification failed for issue '%s': %s", issue.title, exc)
                return None, 0.0
                
        return None, 0.0
