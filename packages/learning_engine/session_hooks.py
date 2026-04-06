#!/usr/bin/env python3
"""Session hooks for cross-session knowledge transfer."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .cross_session_transfer import CrossSessionTransfer
from .outcome_logger import DelegationOutcome, OutcomeLogger

logger = logging.getLogger(__name__)


class SessionLifecycleHook:
    """Manages knowledge extraction and loading at session boundaries."""

    def __init__(self, knowledge_dir: str = ".sisyphus/cross_session"):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_file = self.knowledge_dir / "knowledge.json"
        self.transfer = CrossSessionTransfer(self.knowledge_dir)
        self.outcome_logger = OutcomeLogger()

    def on_session_start(self) -> dict[str, Any]:
        """Load transferable knowledge at session start."""
        try:
            knowledge = self._load_knowledge()
            return {
                "status": "loaded",
                "knowledge_count": len(knowledge),
                "knowledge": knowledge[:10],  # Top 10 most relevant
            }
        except Exception as e:
            logger.error(f"Error loading session knowledge: {e}")
            return {"status": "error", "error": str(e)}

    def on_session_end(self, session_id: Optional[str] = None) -> dict[str, Any]:
        """Extract and save knowledge at session end."""
        session_id = session_id or str(uuid.uuid4())[:8]
        try:
            # Extract from recent outcomes
            outcomes = self.outcome_logger.get_outcomes(limit=50) or []

            # Convert outcomes to decisions and lessons format
            decisions = self._outcomes_to_decisions(outcomes)
            lessons = self._outcomes_to_lessons(outcomes)

            # Extract decisions and lessons with session_id
            extracted_decisions = self.transfer.extract_decisions(session_id, decisions)
            extracted_lessons = self.transfer.extract_lessons(session_id, lessons)

            return {
                "status": "saved",
                "decisions_extracted": len(extracted_decisions),
                "lessons_extracted": len(extracted_lessons),
                "total_knowledge": len(extracted_decisions) + len(extracted_lessons),
            }
        except Exception as e:
            logger.error(f"Error saving session knowledge: {e}")
            return {"status": "error", "error": str(e)}

    def get_transferable_knowledge(
        self, query: Optional[str] = None, limit: int = 5
    ) -> list[dict]:
        """Get knowledge relevant to current context."""
        try:
            results = self.transfer.get_transferable_knowledge(
                query=str(query or ""), limit=limit
            )
            return [
                {
                    "id": k.id,
                    "source_session": k.source_session,
                    "content": k.content,
                    "knowledge_type": k.knowledge_type,
                    "confidence": k.confidence,
                    "transferability_score": k.transferability_score,
                }
                for k in results
            ]
        except Exception as e:
            logger.error(f"Error getting transferable knowledge: {e}")
            return []

    def _outcomes_to_decisions(
        self, outcomes: list[DelegationOutcome]
    ) -> list[dict[str, Any]]:
        """Convert outcomes to decision format for extraction."""
        decisions = []
        for outcome in outcomes:
            if outcome.success:
                decisions.append(
                    {
                        "content": f"Successfully delegated {outcome.task_type} task to {outcome.agent} (L{outcome.level})",
                        "outcome": "success",
                        "occurrence_count": 1,
                    }
                )
        return decisions

    def _outcomes_to_lessons(
        self, outcomes: list[DelegationOutcome]
    ) -> list[dict[str, Any]]:
        """Convert outcomes to lesson format for extraction."""
        lessons = []
        for outcome in outcomes:
            if not outcome.success:
                lessons.append(
                    {
                        "content": f"Failed delegation: {outcome.task_type} to {outcome.agent} - {outcome.context.get('error', 'unknown error')}",
                        "outcome": "failure",
                        "occurrence_count": 1,
                    }
                )
            elif outcome.quality_score and outcome.quality_score < 0.5:
                lessons.append(
                    {
                        "content": f"Low quality delegation: {outcome.task_type} to {outcome.agent} (score: {outcome.quality_score})",
                        "outcome": "mixed",
                        "occurrence_count": 1,
                    }
                )
        return lessons

    def _load_knowledge(self) -> list[dict]:
        """Load knowledge from file."""
        if not self.knowledge_file.exists():
            return []
        with open(self.knowledge_file, "r") as f:
            data = json.load(f)
        return data.get("knowledge", [])

    def _save_knowledge(self, items: list[dict]):
        """Save knowledge to file."""
        existing = self._load_knowledge()

        # Merge new items, avoiding duplicates
        existing_ids = {item.get("id") for item in existing}
        for item in items:
            if item.get("id") not in existing_ids:
                existing.append(item)

        # Sort by transferability score
        existing.sort(key=lambda x: x.get("transferability_score", 0), reverse=True)

        # Keep top 100
        existing = existing[:100]

        with open(self.knowledge_file, "w") as f:
            json.dump({"knowledge": existing}, f, indent=2)
