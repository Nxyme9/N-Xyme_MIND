#!/usr/bin/env python3
"""Intent Predictor - Phase 4.6: Predict agent from partial user input.

This module provides intent prediction from partial/fuzzy input for
pre-emptive agent pre-warming before user finishes typing.

Usage:
    predictor = IntentPredictor()
    agents = predictor.predict_from_partial("add JWT")
    # Returns: ["hephaestus", "explore"]
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IntentPredictor:
    """Predict likely agents from partial input."""

    def __init__(self):
        """Initialize predictor with intent vectors."""
        self._builder = None
        self._keywords = self._load_keywords()

    @property
    def builder(self):
        """Lazy load intent builder."""
        if self._builder is None:
            try:
                from packages.learning_engine.intent_vectors import get_intent_builder

                self._builder = get_intent_builder()
            except Exception as e:
                logger.debug(f"Could not load intent builder: {e}")
        return self._builder

    def _load_keywords(self) -> dict[str, list[str]]:
        """Load keyword to agent mappings."""
        return {
            "hephaestus": [
                "add",
                "implement",
                "create",
                "fix",
                "bug",
                "error",
                "refactor",
                "write",
                "edit",
                "modify",
                "change",
                "build",
                "feature",
                "new",
                "code",
            ],
            "explore": [
                "search",
                "find",
                "where",
                "locate",
                "look",
                "show",
                "list",
                "check",
                "trace",
                "grep",
                "glob",
                "what",
                "how does",
                "explain",
            ],
            "oracle": [
                "review",
                "design",
                "architecture",
                "compare",
                "better",
                "optimal",
                "recommend",
                "advice",
                "evaluate",
                "assess",
                "analyze",
            ],
            "librarian": [
                "docs",
                "documentation",
                "example",
                "library",
                "api",
                "reference",
                "tutorial",
                "guide",
                "how to use",
                "best practice",
            ],
            "multimodal-looker": [
                "image",
                "picture",
                "screenshot",
                "visual",
                "diagram",
                "chart",
                "graph",
                "photo",
            ],
            "momus": [
                "critique",
                "red-team",
                "test",
                "vulnerability",
                "security",
                "risk",
                "attack",
                "exploit",
            ],
            "metis": [
                "plan",
                "design",
                "scope",
                "requirements",
                "ambiguous",
                "unclear",
                "define",
            ],
            "atlas": [
                "run",
                "execute",
                "test",
                "benchmark",
                "verify",
                "validate",
                "check",
            ],
        }

    def predict_from_partial(
        self,
        partial_input: str,
        min_score: float = 0.2,
    ) -> list[dict[str, Any]]:
        """Predict agents from partial input.

        Args:
            partial_input: User's partial query
            min_score: Minimum match score (0-1)

        Returns:
            List of {agent, score, reason} sorted by score
        """
        if not partial_input or len(partial_input.strip()) < 2:
            return []

        partial_lower = partial_input.lower().strip()
        results = []

        # Method 1: Keyword matching
        keyword_scores = self._keyword_match(partial_lower)
        for agent, score in keyword_scores.items():
            if score >= min_score:
                results.append(
                    {
                        "agent": agent,
                        "score": score,
                        "reason": "keyword_match",
                    }
                )

        # Method 2: Fuzzy matching to known queries
        if self.builder:
            try:
                vector_results = self.builder.find_similar(
                    partial_input,
                    top_k=3,
                    min_score=0.1,
                )
                for r in vector_results:
                    # Boost score slightly for vector match
                    results.append(
                        {
                            "agent": r["agent"],
                            "score": r["score"] * 0.9,  # Slightly lower than keyword
                            "reason": "intent_vector",
                        }
                    )
            except Exception as e:
                logger.debug(f"Vector match failed: {e}")

        # Method 3: Prefix matching
        prefix_results = self._prefix_match(partial_lower)
        for agent, score in prefix_results.items():
            if score >= min_score:
                results.append(
                    {
                        "agent": agent,
                        "score": score * 0.8,  # Lower than keyword
                        "reason": "prefix_match",
                    }
                )

        # Deduplicate and combine scores
        combined = self._combine_results(results)

        # Sort by score and return
        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:5]

    def _keyword_match(self, query: str) -> dict[str, float]:
        """Match keywords in query."""
        scores = {}

        for agent, keywords in self._keywords.items():
            matches = sum(1 for kw in keywords if kw in query)
            if matches > 0:
                scores[agent] = min(matches / 2, 1.0)  # Cap at 1.0

        return scores

    def _prefix_match(self, query: str) -> dict[str, float]:
        """Match prefixes of keywords."""
        scores = {}

        for agent, keywords in self._keywords.items():
            for kw in keywords:
                if query.startswith(kw[:3]) or kw.startswith(query[:3]):
                    scores[agent] = scores.get(agent, 0) + 0.3

        # Normalize
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _combine_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Combine duplicate agents, keeping highest score."""
        combined = {}

        for r in results:
            agent = r["agent"]
            if agent not in combined or r["score"] > combined[agent]["score"]:
                combined[agent] = r

        return list(combined.values())

    def predict_agents(self, partial_input: str) -> list[str]:
        """Simple agent name list prediction.

        Args:
            partial_input: User's partial query

        Returns:
            List of agent names sorted by likelihood
        """
        predictions = self.predict_from_partial(partial_input)
        return [p["agent"] for p in predictions]

    def get_suggestions(self, partial_input: str) -> list[str]:
        """Get autocomplete suggestions based on partial input.

        Args:
            partial_input: Current input

        Returns:
            List of possible completions
        """
        suggestions = []
        partial_lower = partial_input.lower().strip()

        # Match against known keywords
        for keywords in self._keywords.values():
            for kw in keywords:
                if kw.startswith(partial_lower) and len(kw) > len(partial_input):
                    suggestions.append(kw)
                elif partial_lower in kw and len(kw) > len(partial_input) + 2:
                    suggestions.append(kw)

        # Deduplicate and limit
        suggestions = list(set(suggestions))[:5]
        return sorted(suggestions)


# Singleton
_predictor: Optional[IntentPredictor] = None


def get_intent_predictor() -> IntentPredictor:
    """Get or create singleton intent predictor."""
    global _predictor
    if _predictor is None:
        _predictor = IntentPredictor()
    return _predictor
