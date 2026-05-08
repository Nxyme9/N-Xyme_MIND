#!/usr/bin/env python3
"""SICA-Style Self-Improving Cognitive Architecture.

Self-Improving Cognitive Architecture (SICA) implements:
- Outcome analysis: Analyze task outcomes and extract improvement patterns
- Failure detection: Detect failure patterns and generate corrective actions
- Weight management: Update routing weights based on success/failure analysis
- Self-audit: Periodic comparison of current vs historical performance
- Retraining trigger: Trigger retraining when improvement threshold met

Usage:
    from packages.learning_engine.sica_style import SICAEngine

    sica = SICAEngine()
    analysis = sica.analyze_outcomes()
    patterns = sica.extract_improvement_patterns(analysis)
    corrections = sica.detect_failure_patterns()
    audit = sica.run_self_audit()
    sica.trigger_retraining_if_needed()
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTCOMES_DB = PROJECT_ROOT / ".sisyphus" / "outcomes.db"
WEIGHTS_DB = PROJECT_ROOT / ".sisyphus" / "routing_weights.json"
AUDIT_HISTORY_DB = PROJECT_ROOT / ".sisyphus" / "sica_audit_history.json"

# SICA configuration
IMPROVEMENT_THRESHOLD = 0.15  # 15% improvement triggers retraining
AUDIT_INTERVAL_HOURS = 24
MIN_SAMPLES_FOR_ANALYSIS = 10
HISTORICAL_WINDOW_DAYS = 7
SUCCESS_RATE_DECAY = 0.95  # Exponential decay for historical comparison

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TaskOutcome:
    """Represents a single task outcome for analysis."""

    task_id: str
    task_description: str
    agent: str
    level: int
    success: bool
    latency_ms: float
    tokens_used: int
    timestamp: str


@dataclass
class ImprovementPattern:
    """Represents a discovered improvement pattern."""

    pattern_id: str
    pattern_type: str  # "success_boost", "latency_reduction", "quality_improvement"
    agent: str
    level: int
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance at a point in time."""

    timestamp: str
    total_tasks: int
    success_rate: float
    average_latency_ms: float
    agent_stats: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SelfAuditResult:
    """Result of a self-audit comparison."""

    audit_timestamp: str
    current_performance: PerformanceSnapshot
    historical_performance: PerformanceSnapshot
    improvement_rate: float
    regression_detected: bool
    recommendations: list[str] = field(default_factory=list)


# ============================================================================
# SICAEngine Class
# ============================================================================


class SICAEngine:
    """Self-Improving Cognitive Architecture engine."""

    def __init__(self, db_path: str = None, weights_path: str = None):
        self.db_path = db_path or str(OUTCOMES_DB)
        self.weights_path = weights_path or str(WEIGHTS_DB)
        self._ensure_databases()

    def _ensure_databases(self):
        """Ensure required databases exist."""
        if not Path(self.db_path).exists():
            logger.warning(f"Outcomes database not found: {self.db_path}")

    def analyze_outcomes(
        self, window_hours: int = 24, min_samples: int = MIN_SAMPLES_FOR_ANALYSIS
    ) -> dict[str, Any]:
        """Analyze recent task outcomes to extract patterns.

        Args:
            window_hours: Time window for analysis
            min_samples: Minimum samples needed for analysis

        Returns:
            Dictionary with analysis results
        """
        if not Path(self.db_path).exists():
            return {"status": "no_data", "samples": 0}

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()

        cursor.execute(
            """SELECT task_id, task_description, agent, level, success,
                      latency_ms, tokens_used, timestamp
               FROM outcomes
               WHERE timestamp > ?
               ORDER BY timestamp DESC""",
            (cutoff,),
        )

        outcomes = []
        for row in cursor.fetchall():
            outcomes.append(
                TaskOutcome(
                    task_id=row[0],
                    task_description=row[1],
                    agent=row[2],
                    level=row[3],
                    success=bool(row[4]),
                    latency_ms=row[5],
                    tokens_used=row[6] or 0,
                    timestamp=row[7],
                )
            )

        conn.close()

        if len(outcomes) < min_samples:
            return {"status": "insufficient_data", "samples": len(outcomes)}

        analysis = self._compute_outcome_analysis(outcomes)
        analysis["status"] = "success"
        analysis["samples"] = len(outcomes)

        logger.info(f"Analyzed {len(outcomes)} outcomes")
        return analysis

    def _compute_outcome_analysis(self, outcomes: list[TaskOutcome]) -> dict[str, Any]:
        """Compute detailed analysis from outcomes."""
        total = len(outcomes)
        successful = sum(1 for o in outcomes if o.success)
        success_rate = successful / total if total > 0 else 0.0

        latencies = [o.latency_ms for o in outcomes]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        agent_stats: dict[str, dict[str, Any]] = {}
        for o in outcomes:
            if o.agent not in agent_stats:
                agent_stats[o.agent] = {"total": 0, "success": 0, "latencies": []}
            agent_stats[o.agent]["total"] += 1
            if o.success:
                agent_stats[o.agent]["success"] += 1
            agent_stats[o.agent]["latencies"].append(o.latency_ms)

        for agent, stats in agent_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = stats["success"] / stats["total"]
            if stats["latencies"]:
                stats["avg_latency"] = sum(stats["latencies"]) / len(stats["latencies"])
            del stats["latencies"]

        return {
            "total_tasks": total,
            "success_rate": success_rate,
            "average_latency_ms": avg_latency,
            "agent_stats": agent_stats,
            "timestamp": datetime.now().isoformat(),
        }

    def extract_improvement_patterns(
        self, analysis: dict[str, Any]
    ) -> list[ImprovementPattern]:
        """Extract improvement patterns from analysis.

        Args:
            analysis: Output from analyze_outcomes

        Returns:
            List of ImprovementPattern objects
        """
        patterns = []
        if analysis.get("status") != "success":
            return patterns

        agent_stats = analysis.get("agent_stats", {})
        for agent, stats in agent_stats.items():
            if stats.get("total", 0) < 3:
                continue

            success_rate = stats.get("success_rate", 0.0)
            avg_latency = stats.get("avg_latency", 0.0)

            if success_rate >= 0.8:
                pattern = ImprovementPattern(
                    pattern_id=f"success_boost:{agent}",
                    pattern_type="success_boost",
                    agent=agent,
                    level=stats.get("level", 1),
                    description=f"Agent {agent} shows high success rate ({success_rate:.1%})",
                    evidence={"success_rate": success_rate},
                    confidence=success_rate,
                )
                patterns.append(pattern)

            if avg_latency > 0 and avg_latency < 50000:
                pattern = ImprovementPattern(
                    pattern_id=f"latency_reduction:{agent}",
                    pattern_type="latency_reduction",
                    agent=agent,
                    level=stats.get("level", 1),
                    description=f"Agent {agent} has low latency ({avg_latency:.0f}ms)",
                    evidence={"avg_latency_ms": avg_latency},
                    confidence=min(1.0, 50000 / avg_latency),
                )
                patterns.append(pattern)

        logger.info(f"Extracted {len(patterns)} improvement patterns")
        return patterns

    def detect_failure_patterns(self) -> list[dict[str, Any]]:
        """Detect failure patterns using self_correction module.

        Returns:
            List of detected failure patterns with corrections
        """
        try:
            from packages.learning_engine.self_correction import FailureAnalyzer

            analyzer = FailureAnalyzer(db_path=self.db_path)
            failures = analyzer.detect_failures()

            if not failures:
                return []

            patterns = analyzer.extract_patterns(failures)
            corrections = analyzer.generate_correction(patterns)

            result = []
            for correction in corrections:
                result.append(
                    {
                        "pattern_id": correction.pattern_id,
                        "description": correction.description,
                        "action_type": correction.action_type,
                        "target_agent": correction.target_agent,
                        "parameters": correction.parameters,
                        "priority": correction.priority,
                    }
                )

            logger.info(f"Detected {len(result)} failure patterns")
            return result

        except ImportError:
            logger.error("self_correction module not available")
            return []

    def update_routing_weights(
        self, analysis: dict[str, Any], adjustments: dict[str, float] = None
    ) -> bool:
        """Update routing weights based on success/failure analysis.

        Args:
            analysis: Output from analyze_outcomes
            adjustments: Optional manual adjustments to apply

        Returns:
            True if successful
        """
        try:
            weights = {}
            if Path(self.weights_path).exists():
                with open(self.weights_path) as f:
                    weights = json.load(f)
            else:
                weights = {"agents": {}}

            agent_stats = analysis.get("agent_stats", {})
            for agent, stats in agent_stats.items():
                if agent not in weights["agents"]:
                    weights["agents"][agent] = {
                        "success_weight": 1.0,
                        "latency_weight": 1.0,
                    }

                success_rate = stats.get("success_rate", 0.5)
                weights["agents"][agent]["success_weight"] = success_rate

                if adjustments and agent in adjustments:
                    weights["agents"][agent]["success_weight"] *= adjustments[agent]

            weights["last_updated"] = datetime.now().isoformat()

            Path(self.weights_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.weights_path, "w") as f:
                json.dump(weights, f, indent=2)

            logger.info(f"Updated routing weights for {len(agent_stats)} agents")
            return True

        except Exception as e:
            logger.error(f"Error updating routing weights: {e}")
            return False

    def run_self_audit(self, window_hours: int = None) -> Optional[SelfAuditResult]:
        """Run periodic self-audit comparing current vs historical performance.

        Args:
            window_hours: Time window for current analysis (default: AUDIT_INTERVAL_HOURS)

        Returns:
            SelfAuditResult with comparison, or None if insufficient data
        """
        window_hours = window_hours or AUDIT_INTERVAL_HOURS
        historical_window = window_hours * HISTORICAL_WINDOW_DAYS

        current_analysis = self.analyze_outcomes(
            window_hours=window_hours, min_samples=MIN_SAMPLES_FOR_ANALYSIS
        )
        if current_analysis.get("status") != "success":
            logger.warning("Insufficient data for current performance snapshot")
            return None

        historical_analysis = self.analyze_outcomes(
            window_hours=historical_window, min_samples=MIN_SAMPLES_FOR_ANALYSIS * 2
        )
        if historical_analysis.get("status") != "success":
            logger.warning("Insufficient data for historical comparison")
            return None

        current_snapshot = self._analysis_to_snapshot(current_analysis)
        historical_snapshot = self._analysis_to_snapshot(historical_analysis)

        current_rate = current_analysis.get("success_rate", 0.0)
        historical_rate = historical_analysis.get("success_rate", 0.0)
        improvement_rate = current_rate - historical_rate

        regression = improvement_rate < -0.1

        recommendations = []
        if regression:
            recommendations.append("Regression detected - review recent changes")
            recommendations.append("Consider rolling back routing weight adjustments")
        elif improvement_rate > IMPROVEMENT_THRESHOLD:
            recommendations.append(
                "Significant improvement - document successful patterns"
            )
            recommendations.append("Consider triggering retraining to固化 gains")

        result = SelfAuditResult(
            audit_timestamp=datetime.now().isoformat(),
            current_performance=current_snapshot,
            historical_performance=historical_snapshot,
            improvement_rate=improvement_rate,
            regression_detected=regression,
            recommendations=recommendations,
        )

        self._save_audit_result(result)
        logger.info(
            f"Self-audit: {improvement_rate:+.1%} improvement, regression={regression}"
        )

        return result

    def _analysis_to_snapshot(self, analysis: dict[str, Any]) -> PerformanceSnapshot:
        """Convert analysis dict to PerformanceSnapshot."""
        return PerformanceSnapshot(
            timestamp=analysis.get("timestamp", datetime.now().isoformat()),
            total_tasks=analysis.get("total_tasks", 0),
            success_rate=analysis.get("success_rate", 0.0),
            average_latency_ms=analysis.get("average_latency_ms", 0.0),
            agent_stats=analysis.get("agent_stats", {}),
        )

    def _save_audit_result(self, result: SelfAuditResult):
        """Save audit result to history."""
        AUDIT_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)

        history = []
        if AUDIT_HISTORY_DB.exists():
            with open(AUDIT_HISTORY_DB) as f:
                history = json.load(f)

        history.append(
            {
                "audit_timestamp": result.audit_timestamp,
                "improvement_rate": result.improvement_rate,
                "regression_detected": result.regression_detected,
                "current_success_rate": result.current_performance.success_rate,
                "historical_success_rate": result.historical_performance.success_rate,
                "recommendations": result.recommendations,
            }
        )

        with open(AUDIT_HISTORY_DB, "w") as f:
            json.dump(history, f, indent=2)

    def trigger_retraining_if_needed(self) -> dict[str, Any]:
        """Trigger retraining when improvement threshold is met.

        Returns:
            Dictionary with trigger result
        """
        audit = self.run_self_audit()

        if not audit:
            return {"status": "skipped", "reason": "insufficient_data"}

        if audit.improvement_rate >= IMPROVEMENT_THRESHOLD:
            return self._trigger_retraining(audit)

        if audit.regression_detected:
            return self._handle_regression(audit)

        return {"status": "no_action", "reason": "performance_stable"}

    def _trigger_retraining(self, audit: SelfAuditResult) -> dict[str, Any]:
        """Trigger retraining based on audit results."""
        try:
            from packages.learning_engine.self_correction import FailureAnalyzer

            analyzer = FailureAnalyzer(db_path=self.db_path)
            failures = analyzer.detect_failures()

            if failures:
                patterns = analyzer.extract_patterns(failures)
                corrections = analyzer.generate_correction(patterns)

                applied = 0
                for correction in corrections:
                    if analyzer.apply_correction(correction):
                        applied += 1

                return {
                    "status": "retraining_triggered",
                    "improvement_rate": audit.improvement_rate,
                    "corrections_applied": applied,
                }

            return {"status": "no_patterns", "reason": "no_failure_patterns"}

        except ImportError:
            logger.error("self_correction module not available for retraining")
            return {"status": "error", "reason": "module_unavailable"}

    def _handle_regression(self, audit: SelfAuditResult) -> dict[str, Any]:
        """Handle performance regression."""
        logger.warning(f"Regression detected: {audit.improvement_rate:+.1%}")

        self.update_routing_weights({"status": "success", "agent_stats": {}}, {})

        return {
            "status": "regression_handled",
            "recommendations": audit.recommendations,
        }

    def run_full_cycle(self) -> dict[str, Any]:
        """Run the complete SICA self-improvement cycle.

        Returns:
            Summary dictionary with all results
        """
        result = {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
        }

        analysis = self.analyze_outcomes()
        result["analysis"] = analysis

        if analysis.get("status") == "success":
            patterns = self.extract_improvement_patterns(analysis)
            result["improvement_patterns"] = len(patterns)
            self.update_routing_weights(analysis)

        failure_patterns = self.detect_failure_patterns()
        result["failure_patterns"] = len(failure_patterns)

        audit = self.run_self_audit()
        if audit:
            result["audit"] = {
                "improvement_rate": audit.improvement_rate,
                "regression_detected": audit.regression_detected,
                "recommendations": audit.recommendations,
            }

        retrain_result = self.trigger_retraining_if_needed()
        result["retraining"] = retrain_result

        result["status"] = "completed"
        logger.info(f"SICA cycle completed: {result['status']}")

        return result


# ============================================================================
# CLI Interface
# ============================================================================


def main():
    """CLI interface for SICA engine."""
    import argparse

    parser = argparse.ArgumentParser(description="SICA-Style Self-Improvement")
    parser.add_argument(
        "--analyze", action="store_true", help="Analyze recent outcomes"
    )
    parser.add_argument(
        "--patterns", action="store_true", help="Extract improvement patterns"
    )
    parser.add_argument(
        "--failures", action="store_true", help="Detect failure patterns"
    )
    parser.add_argument(
        "--update-weights", action="store_true", help="Update routing weights"
    )
    parser.add_argument("--audit", action="store_true", help="Run self-audit")
    parser.add_argument(
        "--trigger", action="store_true", help="Trigger retraining if needed"
    )
    parser.add_argument("--cycle", action="store_true", help="Run full SICA cycle")
    parser.add_argument(
        "--window", type=int, default=24, help="Analysis window in hours"
    )

    args = parser.parse_args()

    sica = SICAEngine()

    if args.cycle:
        result = sica.run_full_cycle()
        print(json.dumps(result, indent=2))
        return

    if args.analyze:
        result = sica.analyze_outcomes(window_hours=args.window)
        print(json.dumps(result, indent=2))

    if args.patterns:
        analysis = sica.analyze_outcomes(window_hours=args.window)
        patterns = sica.extract_improvement_patterns(analysis)
        print(f"Extracted {len(patterns)} improvement patterns:")
        for p in patterns:
            print(f"  - [{p.pattern_type}] {p.description}")

    if args.failures:
        failures = sica.detect_failure_patterns()
        print(f"Detected {len(failures)} failure patterns:")
        for f in failures:
            print(f"  - [{f['action_type']}] {f['description']}")

    if args.update_weights:
        analysis = sica.analyze_outcomes(window_hours=args.window)
        if analysis.get("status") == "success":
            success = sica.update_routing_weights(analysis)
            print(f"Weights updated: {success}")

    if args.audit:
        audit = sica.run_self_audit()
        if audit:
            print(
                json.dumps(
                    {
                        "improvement_rate": audit.improvement_rate,
                        "regression_detected": audit.regression_detected,
                        "recommendations": audit.recommendations,
                    },
                    indent=2,
                )
            )
        else:
            print("Audit skipped: insufficient data")

    if args.trigger:
        result = sica.trigger_retraining_if_needed()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
