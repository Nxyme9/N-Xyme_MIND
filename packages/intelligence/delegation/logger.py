"""Delegation Outcome Logger — Logs outcomes to learning system for continuous improvement."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("outcome-logger")


@dataclass
class OutcomeStats:
    """Statistics for delegation outcomes."""

    total: int = 0
    success: int = 0
    failure: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_tokens: int = 0
    by_level: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class DelegationOutcomeLogger:
    """Logs delegation outcomes to the learning system with JSONL persistence."""

    def __init__(self, learner=None, skill_mgr=None, event_bus=None, persist_path: Optional[str] = None):
        """
        Args:
            learner: SelfLearner instance
            skill_mgr: SkillLifecycleManager instance
            event_bus: LearningEventBus instance
            persist_path: Path to JSONL file for persistence (default: .sisyphus/outcomes.jsonl)
        """
        self._learner = learner
        self._skill_mgr = skill_mgr
        self._event_bus = event_bus
        self._outcomes: List[Dict[str, Any]] = []
        
        # Setup persistence
        if persist_path is None:
            project_root = Path(__file__).parent.parent.parent
            persist_path = str(project_root / ".sisyphus" / "outcomes.jsonl")
        self._persist_path = persist_path
        
        # Load existing outcomes from disk
        self._load_outcomes()

    def _load_outcomes(self) -> None:
        """Load outcomes from JSONL file on startup."""
        try:
            path = Path(self._persist_path)
            if path.exists():
                with open(path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._outcomes.append(json.loads(line))
                logging.getLogger("outcome-logger").info(f"Loaded {len(self._outcomes)} outcomes from {self._persist_path}")
        except Exception as e:
            logging.getLogger("outcome-logger").warning(f"Failed to load outcomes: {e}")

    def _persist_outcome(self, outcome: Dict[str, Any]) -> None:
        """Append a single outcome to the JSONL file."""
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'a') as f:
                f.write(json.dumps(outcome) + '\n')
        except Exception as e:
            logging.getLogger("outcome-logger").warning(f"Failed to persist outcome: {e}")

    async def log_outcome(
        self,
        task_id: str,
        task_description: str,
        level: int,
        agent: str,
        success: bool,
        error: Optional[str] = None,
        latency_ms: float = 0,
        tokens_used: int = 0,
    ) -> bool:
        """Log a delegation outcome to the learning system."""
        try:
            outcome = {
                "task_id": task_id,
                "task_description": task_description,
                "level": level,
                "agent": agent,
                "success": success,
                "error": error,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "timestamp": datetime.now().isoformat(),
            }

            self._outcomes.append(outcome)
            
            # Persist to disk immediately
            self._persist_outcome(outcome)

            if self._learner:
                await self._learner.record_outcome(
                    task_id=task_id,
                    action=f"delegate_{agent}",
                    success=success,
                    reward=1.0 if success else 0.0,
                    latency_ms=latency_ms,
                    cost=float(tokens_used),
                    context={"level": level, "description": task_description},
                )

            if self._skill_mgr:
                try:
                    await self._skill_mgr.record_outcome(
                        skill_name=agent,
                        success=success,
                        latency_ms=latency_ms,
                        cost=float(tokens_used),
                    )
                except Exception as e:
                    logger.debug(f"Skill outcome record skipped: {e}")

            if self._event_bus:
                from packages.learning_engine.event_bus import LearningEvent

                self._event_bus.publish(
                    LearningEvent(
                        source="delegation",
                        task_id=task_id,
                        action="complete" if success else "failed",
                        success=success,
                        context=outcome,
                    )
                )

            logger.info(
                f"Logged outcome: {task_id} → {agent} (L{level}) → {'success' if success else 'failed'}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to log outcome: {e}")
            return False

    def get_outcome_stats(
        self, agent: Optional[str] = None, level: Optional[int] = None
    ) -> OutcomeStats:
        """Get outcome statistics, optionally filtered by agent or level."""
        filtered = self._outcomes
        if agent:
            filtered = [o for o in filtered if o["agent"] == agent]
        if level:
            filtered = [o for o in filtered if o["level"] == level]

        if not filtered:
            return OutcomeStats()

        success_count = sum(1 for o in filtered if o["success"])
        total = len(filtered)

        stats = OutcomeStats(
            total=total,
            success=success_count,
            failure=total - success_count,
            success_rate=success_count / total if total > 0 else 0.0,
            avg_latency_ms=sum(o["latency_ms"] for o in filtered) / total,
            avg_tokens=sum(o["tokens_used"] for o in filtered) / total,
        )

        for lvl in range(1, 6):
            level_outcomes = [o for o in filtered if o["level"] == lvl]
            if level_outcomes:
                level_success = sum(1 for o in level_outcomes if o["success"])
                stats.by_level[lvl] = {
                    "total": len(level_outcomes),
                    "success": level_success,
                    "success_rate": level_success / len(level_outcomes),
                }

        agents = set(o["agent"] for o in filtered)
        for ag in agents:
            agent_outcomes = [o for o in filtered if o["agent"] == ag]
            agent_success = sum(1 for o in agent_outcomes if o["success"])
            stats.by_agent[ag] = {
                "total": len(agent_outcomes),
                "success": agent_success,
                "success_rate": agent_success / len(agent_outcomes),
                "avg_latency_ms": sum(o["latency_ms"] for o in agent_outcomes)
                / len(agent_outcomes),
            }

        return stats

    def get_agent_performance(self, agent: str) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific agent."""
        agent_outcomes = [o for o in self._outcomes if o["agent"] == agent]
        if not agent_outcomes:
            return {"agent": agent, "total": 0, "message": "No outcomes recorded"}

        total = len(agent_outcomes)
        success = sum(1 for o in agent_outcomes if o["success"])

        by_level = {}
        for lvl in range(1, 6):
            level_outcomes = [o for o in agent_outcomes if o["level"] == lvl]
            if level_outcomes:
                level_success = sum(1 for o in level_outcomes if o["success"])
                by_level[lvl] = {
                    "total": len(level_outcomes),
                    "success": level_success,
                    "success_rate": level_success / len(level_outcomes),
                }

        recent_errors = [o["error"] for o in agent_outcomes[-10:] if o.get("error")]

        return {
            "agent": agent,
            "total": total,
            "success": success,
            "success_rate": success / total,
            "avg_latency_ms": sum(o["latency_ms"] for o in agent_outcomes) / total,
            "avg_tokens": sum(o["tokens_used"] for o in agent_outcomes) / total,
            "by_level": by_level,
            "recent_errors": recent_errors[:5],
        }

    def get_outcomes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent outcomes."""
        return self._outcomes[-limit:]

    def clear(self) -> None:
        """Clear all stored outcomes."""
        self._outcomes.clear()


_outcome_logger: Optional[DelegationOutcomeLogger] = None


def get_outcome_logger() -> DelegationOutcomeLogger:
    """Get or create the global outcome logger."""
    global _outcome_logger
    if _outcome_logger is None:
        _outcome_logger = DelegationOutcomeLogger()
    return _outcome_logger
