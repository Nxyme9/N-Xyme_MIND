"""Agent Pre-Warmer - Phase 4.5: Pre-warm likely agents before submission.

This module pre-warms the session pool with agents likely to be needed
based on predictive routing from intent vectors.

Usage:
    warmer = AgentPreWarmer()
    result = warmer.pre_warm("add JWT auth", top_k=3)
    # Returns: {"warmed_agents": ["hephaestus", "explore"], "predictions": [...], "confidence": 0.85}
"""

from __future__ import annotations

__version__ = "4.5.0"

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Valid agent names for the orchestration system
VALID_AGENTS = frozenset(
    [
        "hephaestus",  # Implementation agent
        "explore",  # Codebase exploration
        "librarian",  # External research
        "oracle",  # Architecture review
        "metis",  # Pre-planning
        "momus",  # Adversarial review
        "prometheus",  # Plan building
        "atlas",  # Plan execution
        "sisyphus-junior",  # Trivial fixes
        "multimodal-looker",  # Visual content
    ]
)


@dataclass
class Prediction:
    """Single agent prediction with confidence."""

    agent: str
    score: float
    reason: str


@dataclass
class PreWarmResult:
    """Structured result from pre-warming."""

    status: str
    warmed_agents: list[str] = field(default_factory=list)
    predictions: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    query: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "warmed_agents": self.warmed_agents,
            "predictions": self.predictions,
            "confidence": self.confidence,
            "query": self.query,
            "error": self.error,
        }


class AgentPreWarmer:
    """Pre-warm agent sessions based on predicted needs.

    This class integrates with IntentPredictor to predict which agents
    will be needed based on the user's partial input, then pre-warms
    those agent sessions before the user submits their request.
    """

    def __init__(self, min_score: float = 0.2):
        """Initialize pre-warmer.

        Args:
            min_score: Minimum prediction score to consider (0-1)
        """
        self._predictor = None
        self._session_warm_pool = None
        self.min_score = min_score

    @property
    def predictor(self):
        """Lazy load intent predictor from packages.intelligence.intent_predictor."""
        if self._predictor is None:
            try:
                from packages.intelligence.intent_predictor import get_intent_predictor

                self._predictor = get_intent_predictor()
                logger.debug("Loaded intent predictor")
            except ImportError as e:
                logger.warning(f"Could not load intent predictor: {e}")
        return self._predictor

    @property
    def session_warm_pool(self):
        """Lazy load session warm pool function."""
        if self._session_warm_pool is None:
            try:
                from packages.brain_mcp.namespaces.session import session_warm_pool

                self._session_warm_pool = session_warm_pool
                logger.debug("Loaded session_warm_pool")
            except ImportError as e:
                logger.warning(f"Could not load session_warm_pool: {e}")
        return self._session_warm_pool

    def pre_warm(
        self,
        partial_input: str,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """Pre-warm likely agents before user submits.

        Args:
            partial_input: User's partial query or task description
            top_k: Number of top agents to warm (default 3)

        Returns:
            Dict with warmed_agents, predictions, confidence
        """
        return self._pre_warm_impl(partial_input, top_k).to_dict()

    def _pre_warm_impl(
        self,
        partial_input: str,
        top_k: int = 3,
    ) -> PreWarmResult:
        """Internal implementation returning structured result."""
        # Input validation
        if not partial_input or len(partial_input.strip()) < 2:
            return PreWarmResult(
                status="skipped",
                query=partial_input,
                error="Input too short",
            )

        # Step 1: Get predictions from IntentPredictor
        predictions = self._get_predictions(partial_input)

        if not predictions:
            return PreWarmResult(
                status="skipped",
                query=partial_input,
                error="No predictions",
            )

        # Step 2: Filter to top_k valid agents
        top_agents = self._filter_top_agents(predictions, top_k)

        if not top_agents:
            return PreWarmResult(
                status="skipped",
                query=partial_input,
                error="No valid agents predicted",
            )

        # Step 3: Warm the sessions
        self._warm_sessions(top_agents)

        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(predictions[:top_k])

        return PreWarmResult(
            status="success",
            query=partial_input,
            warmed_agents=top_agents,
            predictions=predictions[:top_k],
            confidence=confidence,
        )

    def _get_predictions(
        self,
        partial_input: str,
    ) -> list[dict[str, Any]]:
        """Get agent predictions from IntentPredictor."""
        if not self.predictor:
            logger.debug("No predictor available, using fallback")
            return self._fallback_predict(partial_input)

        try:
            # Use IntentPredictor's predict_from_partial method
            results = self.predictor.predict_from_partial(
                partial_input,
                min_score=self.min_score,
            )
            logger.debug(f"Got {len(results)} predictions for: {partial_input[:30]}")
            return results
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return self._fallback_predict(partial_input)

    def _fallback_predict(self, partial_input: str) -> list[dict[str, Any]]:
        """Fallback keyword-based prediction when IntentPredictor unavailable."""
        partial_lower = partial_input.lower().strip()
        results = []

        # Simple keyword matching as fallback
        keywords_map = {
            "hephaestus": ["add", "implement", "create", "fix", "bug", "write", "code"],
            "explore": ["find", "search", "where", "grep", "glob", "look"],
            "oracle": ["review", "design", "architecture", "advice", "analyze"],
            "librarian": ["docs", "library", "api", "example", "reference"],
            "metis": ["plan", "design", "scope", "ambiguous"],
            "momus": ["test", "vulnerability", "security", "risk"],
        }

        for agent, keywords in keywords_map.items():
            matches = sum(1 for kw in keywords if kw in partial_lower)
            if matches > 0:
                score = min(matches / 2.0, 1.0)
                results.append(
                    {
                        "agent": agent,
                        "score": score,
                        "reason": "keyword_fallback",
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]

    def _filter_top_agents(
        self,
        predictions: list[dict[str, Any]],
        top_k: int,
    ) -> list[str]:
        """Filter predictions to valid agent names."""
        agents = []
        for pred in predictions:
            agent = pred.get("agent", "")
            if agent in VALID_AGENTS and agent not in agents:
                agents.append(agent)
                if len(agents) >= top_k:
                    break
        return agents

    def _warm_sessions(self, agents: list[str]) -> None:
        """Warm session pool for given agents."""
        if not self.session_warm_pool:
            logger.warning("session_warm_pool not available")
            return

        if not agents:
            return

        try:
            result = self.session_warm_pool(agents=agents[:3])
            if result.get("error"):
                logger.warning(f"Session warm error: {result.get('error')}")
            else:
                logger.info(f"Warmed agents: {agents[:3]}")
        except Exception as e:
            logger.warning(f"Session warm failed: {e}")

    def _calculate_confidence(
        self,
        predictions: list[dict[str, Any]],
    ) -> float:
        """Calculate overall confidence score."""
        if not predictions:
            return 0.0

        # Average of top-3 scores
        scores = [p.get("score", 0.0) for p in predictions[:3]]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return round(avg_score, 2)

    def pre_warm_auto(self) -> dict[str, Any]:
        """Auto pre-warm based on common agents.

        Returns:
            Dict with status and warmed agents
        """
        common_agents = ["hephaestus", "explore", "oracle"]
        self._warm_sessions(common_agents)

        return {
            "status": "success",
            "warmed_agents": common_agents,
        }


# Singleton pattern
_pre_warmer: Optional[AgentPreWarmer] = None


def get_pre_warmer() -> AgentPreWarmer:
    """Get singleton pre-warmer instance."""
    global _pre_warmer
    if _pre_warmer is None:
        _pre_warmer = AgentPreWarmer()
    return _pre_warmer


def pre_warm_time_based() -> dict[str, Any]:
    """Pre-warm agents based on time-of-day patterns.

    Reads peak hours from style_learner and warms appropriate agents.

    Returns:
        Dict with status and warmed agents
    """
    import datetime
    from packages.context_store import get_style_context

    current_hour = datetime.datetime.now().hour

    try:
        style = get_style_context()
        peak_hours = style.get("style_profile", {}).get("peak_hours", [])

        if peak_hours and current_hour in peak_hours:
            warmer = get_pre_warmer()
            result = warmer.pre_warm_auto()
            result["time_based"] = True
            result["current_hour"] = current_hour
            result["peak_hours"] = peak_hours
            return result
    except Exception as e:
        logger.warning(f"Time-based pre-warm failed: {e}")

    return {
        "status": "skipped",
        "time_based": False,
        "current_hour": current_hour,
        "reason": "No peak hours match" if current_hour else "No style data",
    }


_pre_warm_accuracy_db: Optional[Any] = None


def _get_accuracy_db():
    """Get or create SQLite DB for pre-warm accuracy tracking."""
    global _pre_warm_accuracy_db
    if _pre_warm_accuracy_db is None:
        import sqlite3
        from pathlib import Path

        db_path = Path(".sisyphus/pre_warm_accuracy.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _pre_warm_accuracy_db = sqlite3.connect(str(db_path), check_same_thread=False)
        _pre_warm_accuracy_db.execute("""
            CREATE TABLE IF NOT EXISTS pre_warm_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predicted_agents TEXT,
                actual_agent TEXT,
                query TEXT,
                confidence REAL,
                correct INTEGER,
                timestamp INTEGER
            )
        """)
        _pre_warm_accuracy_db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON pre_warm_predictions(timestamp)
        """)
    return _pre_warm_accuracy_db


def record_pre_warm_accuracy(
    predicted_agents: list[str],
    actual_agent: str,
    query: str,
    confidence: float,
) -> dict[str, Any]:
    """Record pre-warm prediction vs actual agent for accuracy tracking.

    Args:
        predicted_agents: List of agents predicted by pre_warm
        actual_agent: The agent that was actually used
        query: The user query
        confidence: Prediction confidence score

    Returns:
        Dict with recording status and correctness
    """
    import time

    correct = 1 if actual_agent in predicted_agents else 0

    try:
        db = _get_accuracy_db()
        db.execute(
            """INSERT INTO pre_warm_predictions 
               (predicted_agents, actual_agent, query, confidence, correct, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                ",".join(predicted_agents),
                actual_agent,
                query,
                confidence,
                correct,
                int(time.time()),
            ),
        )
        db.commit()

        return {
            "status": "recorded",
            "correct": correct,
            "predicted": predicted_agents,
            "actual": actual_agent,
        }
    except Exception as e:
        logger.warning(f"Failed to record pre-warm accuracy: {e}")
        return {"status": "error", "error": str(e)}


def get_pre_warm_accuracy(days: int = 7) -> dict[str, Any]:
    """Get pre-warm accuracy statistics.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with accuracy metrics
    """
    import time

    cutoff = int(time.time()) - days * 24 * 60 * 60

    try:
        db = _get_accuracy_db()

        overall = db.execute(
            """SELECT 
                   COUNT(*) as total,
                   SUM(correct) as correct,
                   AVG(confidence) as avg_confidence
               FROM pre_warm_predictions 
               WHERE timestamp > ?""",
            (cutoff,),
        ).fetchone()

        by_agent = db.execute(
            """SELECT 
                   actual_agent,
                   COUNT(*) as total,
                   SUM(correct) as correct,
                   AVG(confidence) as avg_confidence
               FROM pre_warm_predictions 
               WHERE timestamp > ?
               GROUP BY actual_agent""",
            (cutoff,),
        ).fetchall()

        daily = db.execute(
            """SELECT 
                   strftime('%Y-%m-%d', timestamp, 'unixepoch') as date,
                   COUNT(*) as predictions,
                   SUM(correct) as correct,
                   AVG(confidence) as avg_confidence
               FROM pre_warm_predictions 
               WHERE timestamp > ?
               GROUP BY date
               ORDER BY date ASC""",
            (cutoff,),
        ).fetchall()

        total = overall[0] or 0
        correct_count = overall[1] or 0

        return {
            "accuracy": round(correct_count / total, 3) if total > 0 else 0.0,
            "total_predictions": total,
            "correct_predictions": correct_count,
            "avg_confidence": round(overall[2] or 0, 2),
            "by_actual_agent": [
                {
                    "agent": row[0],
                    "total": row[1],
                    "correct": row[2],
                    "accuracy": round(row[2] / row[1], 3) if row[1] > 0 else 0,
                    "avg_confidence": round(row[3] or 0, 2),
                }
                for row in by_agent
            ],
            "daily_trend": [
                {
                    "date": row[0],
                    "predictions": row[1],
                    "correct": row[2],
                    "accuracy": round(row[2] / row[1], 3) if row[1] > 0 else 0,
                }
                for row in daily
            ],
            "period_days": days,
        }
    except Exception as e:
        logger.warning(f"Failed to get pre-warm accuracy: {e}")
        return {"accuracy": 0, "total_predictions": 0, "error": str(e)}
