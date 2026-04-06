"""Observer/Reflector Pattern — Continuous background memory processing.

Based on Mastra Observational Memory (94.87% LongMemEval — highest ever recorded).

Pattern: Two background agents watch conversations and maintain a dense
observation log. Raw messages are converted into observations and then
dropped — the context window stays stable.

Key innovations:
1. No per-turn dynamic retrieval — context is predictable and cacheable
2. Continuous subconscious processing — memories are updated in background
3. Observation → Reflection → Integration pipeline
4. Stable context windows with prompt-cacheable observations

Architecture:
- Observer: Watches conversations, extracts dense observations
- Reflector: Reviews observations, extracts patterns, updates knowledge
- Integration: Merges reflections into long-term memory
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    """A dense observation extracted from conversation."""

    id: str
    session_id: str
    content: str
    observation_type: str  # fact, decision, correction, preference, error, pattern
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 0.5
    source_messages: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Reflection:
    """A reflection derived from multiple observations."""

    id: str
    content: str
    reflection_type: str  # pattern, insight, principle, contradiction
    source_observations: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Observer:
    """Watches conversations and extracts dense observations.

    Pattern: Converts raw messages into observations, then drops raw messages.
    This keeps the context window stable and predictable.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize observer.

        Args:
            storage_path: Path to store observations.
        """
        self.storage_path = storage_path or Path(".sisyphus/observations")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.observations: list[Observation] = []
        self._load_observations()

    def observe_message(
        self,
        session_id: str,
        role: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> list[Observation]:
        """Observe a single message and extract observations.

        In production, this would use an LLM to extract dense observations.
        For now, uses pattern matching to identify key information.

        Args:
            session_id: Session identifier.
            role: Message role (user, assistant, system, tool).
            content: Message content.
            context: Additional context.

        Returns:
            List of extracted observations.
        """
        observations = []

        # Pattern 1: User corrections
        if role == "user" and any(
            phrase in content.lower()
            for phrase in ["don't", "stop", "no", "not that", "wrong", "incorrect"]
        ):
            observations.append(
                Observation(
                    id=f"obs_{int(time.time() * 1000)}_corr",
                    session_id=session_id,
                    content=f"User correction: {content[:200]}",
                    observation_type="correction",
                    confidence=0.9,
                    source_messages=[content],
                    tags=["correction", "feedback"],
                )
            )

        # Pattern 2: User preferences
        elif role == "user" and any(
            phrase in content.lower()
            for phrase in ["i prefer", "i like", "i want", "i need"]
        ):
            observations.append(
                Observation(
                    id=f"obs_{int(time.time() * 1000)}_pref",
                    session_id=session_id,
                    content=f"User preference: {content[:200]}",
                    observation_type="preference",
                    confidence=0.8,
                    source_messages=[content],
                    tags=["preference", "user"],
                )
            )

        # Pattern 3: Decisions
        elif any(
            phrase in content.lower()
            for phrase in [
                "we decided",
                "we'll use",
                "let's go with",
                "the approach is",
            ]
        ):
            observations.append(
                Observation(
                    id=f"obs_{int(time.time() * 1000)}_dec",
                    session_id=session_id,
                    content=f"Decision: {content[:200]}",
                    observation_type="decision",
                    confidence=0.85,
                    source_messages=[content],
                    tags=["decision"],
                )
            )

        # Pattern 4: Errors and fixes
        elif role == "assistant" and any(
            phrase in content.lower()
            for phrase in ["error:", "fixed", "resolved", "the issue was"]
        ):
            observations.append(
                Observation(
                    id=f"obs_{int(time.time() * 1000)}_err",
                    session_id=session_id,
                    content=f"Error/Fix: {content[:200]}",
                    observation_type="error",
                    confidence=0.7,
                    source_messages=[content],
                    tags=["error", "fix"],
                )
            )

        # Pattern 5: Facts and knowledge
        elif role == "assistant" and len(content) > 100:
            # Extract key facts from longer responses
            sentences = content.split(". ")
            if len(sentences) > 2:
                observations.append(
                    Observation(
                        id=f"obs_{int(time.time() * 1000)}_fact",
                        session_id=session_id,
                        content=f"Fact: {sentences[0]}",
                        observation_type="fact",
                        confidence=0.6,
                        source_messages=[content],
                        tags=["fact", "knowledge"],
                    )
                )

        # Store observations
        for obs in observations:
            self.observations.append(obs)
            self._save_observation(obs)

        return observations

    def get_observations(
        self,
        session_id: str | None = None,
        observation_type: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[Observation]:
        """Get observations with optional filters."""
        results = self.observations

        if session_id:
            results = [o for o in results if o.session_id == session_id]
        if observation_type:
            results = [o for o in results if o.observation_type == observation_type]
        if tag:
            results = [o for o in results if tag in o.tags]

        # Sort by timestamp (newest first)
        results.sort(key=lambda o: o.timestamp, reverse=True)
        return results[:limit]

    def get_recent_observations(
        self, hours: int = 24, limit: int = 20
    ) -> list[Observation]:
        """Get observations from the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = []

        for obs in self.observations:
            obs_time = datetime.fromisoformat(obs.timestamp)
            if obs_time >= cutoff:
                results.append(obs)

        results.sort(key=lambda o: o.timestamp, reverse=True)
        return results[:limit]

    def _save_observation(self, observation: Observation) -> None:
        """Save observation to storage."""
        obs_file = self.storage_path / f"{observation.id}.json"
        obs_file.write_text(
            json.dumps(
                {
                    "id": observation.id,
                    "session_id": observation.session_id,
                    "content": observation.content,
                    "observation_type": observation.observation_type,
                    "timestamp": observation.timestamp,
                    "confidence": observation.confidence,
                    "source_messages": observation.source_messages,
                    "tags": observation.tags,
                    "metadata": observation.metadata,
                },
                indent=2,
            )
        )

    def _load_observations(self) -> None:
        """Load observations from storage."""
        for obs_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(obs_file.read_text())
                obs = Observation(
                    id=data["id"],
                    session_id=data["session_id"],
                    content=data["content"],
                    observation_type=data["observation_type"],
                    timestamp=data.get("timestamp", ""),
                    confidence=data.get("confidence", 0.5),
                    source_messages=data.get("source_messages", []),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                )
                self.observations.append(obs)
            except Exception as e:
                logger.warning(f"Failed to load observation {obs_file}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get observation statistics."""
        by_type: dict[str, int] = {}
        for obs in self.observations:
            by_type[obs.observation_type] = by_type.get(obs.observation_type, 0) + 1

        return {
            "total_observations": len(self.observations),
            "by_type": by_type,
        }


class Reflector:
    """Reviews observations and extracts patterns/insights.

    Pattern: Periodically reviews the observation log, identifies patterns,
    contradictions, and insights, then updates the knowledge graph.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize reflector.

        Args:
            storage_path: Path to store reflections.
        """
        self.storage_path = storage_path or Path(".sisyphus/reflections")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reflections: list[Reflection] = []
        self._load_reflections()

    def reflect(
        self,
        observations: list[Observation],
        min_confidence: float = 0.6,
    ) -> list[Reflection]:
        """Reflect on a set of observations and extract insights.

        In production, this would use an LLM to analyze observations.
        For now, uses pattern matching to identify relationships.

        Args:
            observations: List of observations to reflect on.
            min_confidence: Minimum confidence for reflections.

        Returns:
            List of generated reflections.
        """
        reflections = []

        # Group observations by type
        by_type: dict[str, list[Observation]] = {}
        for obs in observations:
            if obs.observation_type not in by_type:
                by_type[obs.observation_type] = []
            by_type[obs.observation_type].append(obs)

        # Pattern 1: Multiple corrections on same topic → pattern
        if "correction" in by_type and len(by_type["correction"]) >= 2:
            corrections = by_type["correction"]
            reflections.append(
                Reflection(
                    id=f"ref_{int(time.time() * 1000)}_pattern",
                    content=f"Pattern: {len(corrections)} corrections observed. "
                    f"Topics: {', '.join(c.content[:50] for c in corrections[:3])}",
                    reflection_type="pattern",
                    source_observations=[c.id for c in corrections],
                    confidence=min(0.9, 0.5 + len(corrections) * 0.1),
                    tags=["pattern", "correction"],
                )
            )

        # Pattern 2: Contradictions between observations
        if len(observations) >= 3:
            # Simple contradiction detection: similar content with different types
            for i, obs1 in enumerate(observations):
                for obs2 in observations[i + 1 :]:
                    if obs1.observation_type != obs2.observation_type:
                        # Check for semantic similarity (simple keyword overlap)
                        words1 = set(obs1.content.lower().split())
                        words2 = set(obs2.content.lower().split())
                        overlap = len(words1 & words2) / max(len(words1), len(words2))

                        if overlap > 0.3:
                            reflections.append(
                                Reflection(
                                    id=f"ref_{int(time.time() * 1000)}_contradict",
                                    content=f"Potential contradiction between:\n"
                                    f"1. {obs1.content[:100]}\n"
                                    f"2. {obs2.content[:100]}",
                                    reflection_type="contradiction",
                                    source_observations=[obs1.id, obs2.id],
                                    confidence=overlap,
                                    tags=["contradiction", "review"],
                                )
                            )

        # Pattern 3: Recurring facts → principle
        if "fact" in by_type and len(by_type["fact"]) >= 3:
            facts = by_type["fact"]
            reflections.append(
                Reflection(
                    id=f"ref_{int(time.time() * 1000)}_principle",
                    content=f"Principle derived from {len(facts)} observations: "
                    f"{' '.join(f.content[:30] for f in facts[:3])}",
                    reflection_type="principle",
                    source_observations=[f.id for f in facts],
                    confidence=0.7,
                    tags=["principle", "knowledge"],
                )
            )

        # Store reflections
        for ref in reflections:
            if ref.confidence >= min_confidence:
                self.reflections.append(ref)
                self._save_reflection(ref)

        return reflections

    def get_reflections(
        self,
        reflection_type: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[Reflection]:
        """Get reflections with optional filters."""
        results = self.reflections

        if reflection_type:
            results = [r for r in results if r.reflection_type == reflection_type]
        if tag:
            results = [r for r in results if tag in r.tags]

        # Sort by confidence (highest first)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]

    def _save_reflection(self, reflection: Reflection) -> None:
        """Save reflection to storage."""
        ref_file = self.storage_path / f"{reflection.id}.json"
        ref_file.write_text(
            json.dumps(
                {
                    "id": reflection.id,
                    "content": reflection.content,
                    "reflection_type": reflection.reflection_type,
                    "source_observations": reflection.source_observations,
                    "timestamp": reflection.timestamp,
                    "confidence": reflection.confidence,
                    "tags": reflection.tags,
                    "metadata": reflection.metadata,
                },
                indent=2,
            )
        )

    def _load_reflections(self) -> None:
        """Load reflections from storage."""
        for ref_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(ref_file.read_text())
                ref = Reflection(
                    id=data["id"],
                    content=data["content"],
                    reflection_type=data["reflection_type"],
                    source_observations=data.get("source_observations", []),
                    timestamp=data.get("timestamp", ""),
                    confidence=data.get("confidence", 0.5),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                )
                self.reflections.append(ref)
            except Exception as e:
                logger.warning(f"Failed to load reflection {ref_file}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get reflection statistics."""
        by_type: dict[str, int] = {}
        for ref in self.reflections:
            by_type[ref.reflection_type] = by_type.get(ref.reflection_type, 0) + 1

        return {
            "total_reflections": len(self.reflections),
            "by_type": by_type,
        }


class ObservationalMemory:
    """Complete observational memory system (Observer + Reflector).

    This is the main interface for the Mastra OM pattern.
    """

    def __init__(
        self,
        observer_path: Path | None = None,
        reflector_path: Path | None = None,
    ):
        """Initialize observational memory.

        Args:
            observer_path: Path for observer storage.
            reflector_path: Path for reflector storage.
        """
        self.observer = Observer(observer_path)
        self.reflector = Reflector(reflector_path)

    def process_message(
        self,
        session_id: str,
        role: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a message through the observation pipeline.

        Args:
            session_id: Session identifier.
            role: Message role.
            content: Message content.
            context: Additional context.

        Returns:
            Dict with observations and any reflections generated.
        """
        # Step 1: Observer extracts observations
        observations = self.observer.observe_message(session_id, role, content, context)

        # Step 2: If we have enough observations, trigger reflection
        reflections = []
        recent = self.observer.get_recent_observations(hours=1, limit=20)
        if len(recent) >= 3:
            reflections = self.reflector.reflect(recent)

        return {
            "observations": [o.id for o in observations],
            "reflections": [r.id for r in reflections],
            "context_stable": True,  # Context window is stable
        }

    def get_context_for_prompt(
        self,
        session_id: str,
        max_observations: int = 10,
        max_reflections: int = 5,
    ) -> str:
        """Get stable context for prompt injection.

        This replaces per-turn dynamic retrieval with a predictable,
        cacheable context window.

        Args:
            session_id: Session identifier.
            max_observations: Maximum observations to include.
            max_reflections: Maximum reflections to include.

        Returns:
            Formatted context string for prompt injection.
        """
        observations = self.observer.get_observations(
            session_id=session_id,
            limit=max_observations,
        )
        reflections = self.reflector.get_reflections(
            limit=max_reflections,
        )

        context_parts = ["# Observational Memory Context", ""]

        if observations:
            context_parts.append("## Recent Observations")
            for obs in observations:
                context_parts.append(f"- [{obs.observation_type}] {obs.content}")

        if reflections:
            context_parts.append("\n## Reflections")
            for ref in reflections:
                context_parts.append(f"- [{ref.reflection_type}] {ref.content}")

        return "\n".join(context_parts)

    def get_stats(self) -> dict[str, Any]:
        """Get complete system statistics."""
        return {
            "observer": self.observer.get_stats(),
            "reflector": self.reflector.get_stats(),
        }


# Global singleton
_observational_memory = ObservationalMemory()


def process_message(
    session_id: str,
    role: str,
    content: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to process a message."""
    return _observational_memory.process_message(session_id, role, content, context)


def get_context_for_prompt(
    session_id: str,
    max_observations: int = 10,
    max_reflections: int = 5,
) -> str:
    """Convenience function to get context for prompt."""
    return _observational_memory.get_context_for_prompt(
        session_id,
        max_observations,
        max_reflections,
    )
