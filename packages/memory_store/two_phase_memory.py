#!/usr/bin/env python3
"""Two-phase memory extraction and update system (Mem0-style)."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryAction(str, Enum):
    """Actions for memory update phase."""

    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NOOP = "NOOP"


@dataclass
class ExtractedMemory:
    """A candidate memory extracted from context."""

    content: str
    priority: float = 1.0
    memory_type: str = "episodic"  # episodic, semantic, sensory


@dataclass
class MemoryUpdate:
    """Result of memory update decision."""

    action: MemoryAction
    target_memory_id: Optional[str] = None
    new_content: Optional[str] = None
    confidence: float = 0.0


class TwoPhaseMemory:
    """Mem0-style two-phase memory processing.

    Phase 1 - Extraction: Extract candidate memories from context using LLM
    Phase 2 - Update: Compare candidates against existing, decide ADD/UPDATE/DELETE/NOOP
    """

    def __init__(self, memory_manager=None):
        """Initialize two-phase memory processor."""
        self.memory_manager = memory_manager
        self._extraction_prompt = self._default_extraction_prompt()

    def _default_extraction_prompt(self) -> str:
        """Default prompt for memory extraction."""
        return """Extract key facts, preferences, and important information from this conversation.
        
Return a JSON list of facts. Each fact should be:
- A single, atomic piece of information
- In the user's own words if possible
- Marked with importance: high/medium/low

Only extract information that would be useful to remember long-term.
Ignore: typos, filler words, redundant information."""

    def extract_memories(
        self, context: str, memory_type: str = "episodic"
    ) -> list[ExtractedMemory]:
        """Phase 1: Extract candidate memories from context.

        This would normally call an LLM. For now, use simple extraction.
        In production, replace with actual LLM call.
        """
        # Simple heuristic extraction (placeholder for LLM)
        memories = []

        # Split by sentences and extract factual statements
        sentences = context.split(".")
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 20 and any(
                keyword in sentence.lower()
                for keyword in [
                    "prefer",
                    "like",
                    "hate",
                    "want",
                    "need",
                    "always",
                    "never",
                    "remember",
                    "forget",
                    "important",
                    "key",
                    "use",
                    "know",
                ]
            ):
                memories.append(
                    ExtractedMemory(
                        content=sentence,
                        priority=1.0
                        if any(
                            k in sentence.lower()
                            for k in ["important", "key", "prefer", "like"]
                        )
                        else 0.5,
                        memory_type=memory_type,
                    )
                )

        logger.info(f"Extracted {len(memories)} candidate memories from context")
        return memories

    def compare_and_update(
        self,
        candidates: list[ExtractedMemory],
        session_id: str = None,
        user_id: str = None,
    ) -> list[MemoryUpdate]:
        """Phase 2: Compare candidates against existing memories and decide actions.

        Returns list of MemoryUpdate decisions.
        """
        updates = []

        if not self.memory_manager:
            # No memory manager - just add everything
            for candidate in candidates:
                updates.append(
                    MemoryUpdate(
                        action=MemoryAction.ADD,
                        new_content=candidate.content,
                        confidence=0.5,
                    )
                )
            return updates

        # Check each candidate against existing memories
        for candidate in candidates:
            # Search for similar existing memories
            existing = self._find_similar(candidate.content, session_id, user_id)

            if not existing:
                # No similar memory - ADD
                updates.append(
                    MemoryUpdate(
                        action=MemoryAction.ADD,
                        new_content=candidate.content,
                        confidence=0.8,
                    )
                )
            else:
                # Check if update needed
                similarity = self._calculate_similarity(
                    candidate.content, existing.get("content", "")
                )

                if similarity > 0.9:
                    # Almost identical - NOOP
                    updates.append(
                        MemoryUpdate(
                            action=MemoryAction.NOOP,
                            target_memory_id=existing.get("id"),
                            confidence=0.95,
                        )
                    )
                elif similarity > 0.6:
                    # Similar but different - UPDATE
                    updates.append(
                        MemoryUpdate(
                            action=MemoryAction.UPDATE,
                            target_memory_id=existing.get("id"),
                            new_content=candidate.content,
                            confidence=0.7,
                        )
                    )
                else:
                    # Different enough - ADD as new
                    updates.append(
                        MemoryUpdate(
                            action=MemoryAction.ADD,
                            new_content=candidate.content,
                            confidence=0.6,
                        )
                    )

        return updates

    def _find_similar(
        self, content: str, session_id: Optional[str], user_id: Optional[str]
    ) -> Optional[dict]:
        """Find similar existing memory."""
        # Placeholder - would search memory store
        return None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple version)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def process_context(
        self,
        context: str,
        session_id: str = None,
        user_id: str = None,
        memory_type: str = "episodic",
    ) -> list[MemoryUpdate]:
        """Full two-phase processing of context."""
        # Phase 1: Extract
        candidates = self.extract_memories(context, memory_type)

        # Phase 2: Update
        updates = self.compare_and_update(candidates, session_id, user_id)

        logger.info(
            f"Two-phase processing: {len(candidates)} candidates -> {len(updates)} decisions"
        )
        return updates
