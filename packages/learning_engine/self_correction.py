#!/usr/bin/env python3
"""Self-Correction Loop — Phase 2.1 component for failure detection and auto-correction.

This module implements:
- Failure detection: Analyze outcomes to identify failure patterns
- Root cause analysis: Use chain-of-thought to trace failure to source
- Pattern extraction: Extract actionable patterns from failures
- Auto-correction: Generate and apply fixes for identified patterns
- Loop closure: Feed corrections back into training pipeline

Usage:
    from packages.learning_engine.self_correction import FailureAnalyzer

    analyzer = FailureAnalyzer()
    failures = analyzer.detect_failures()
    root_cause = analyzer.analyze_root_cause(failures[0])
    patterns = analyzer.extract_patterns(failures)
    correction = analyzer.generate_correction(patterns)
    analyzer.apply_correction(correction)
"""

from __future__ import annotations

import json
import sqlite3
import logging
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
PATTERNS_DB = PROJECT_ROOT / ".sisyphus" / "correction_patterns.json"

# Detection thresholds
MIN_FAILURE_COUNT = 3
FAILURE_WINDOW_HOURS = 24
SEVERITY_THRESHOLD = 0.3

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class Failure:
    """Represents a detected failure."""

    task_id: str
    task_description: str
    agent: str
    level: int
    failure_type: str  # "timeout", "error", "partial", "quality"
    severity: float  # 0-1
    latency_ms: float
    error_context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RootCause:
    """Represents the root cause of a failure pattern."""

    pattern: str
    likely_cause: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-1


@dataclass
class Correction:
    """Represents a generated correction/fix."""

    pattern_id: str
    description: str
    action_type: str  # "route_change", "param_adjust", "retrain", "config_update"
    target_agent: Optional[str] = None
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-5, 1 is highest
    applied: bool = False


# ============================================================================
# FailureAnalyzer Class
# ============================================================================


class FailureAnalyzer:
    """Analyzes outcomes to detect failures, extract patterns, and generate corrections."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(PROJECT_ROOT / ".sisyphus" / "outcomes.db")
        self._ensure_db()

    def _ensure_db(self):
        """Ensure outcomes database exists."""
        if not Path(self.db_path).exists():
            logger.warning(f"Outcomes database not found: {self.db_path}")
            return

    def detect_failures(
        self,
        window_hours: int = FAILURE_WINDOW_HOURS,
        min_count: int = MIN_FAILURE_COUNT,
    ) -> list[Failure]:
        """Detect failures from recent outcomes.

        Args:
            window_hours: Time window to look back (hours)
            min_count: Minimum failures to trigger analysis

        Returns:
            List of Failure objects
        """
        if not Path(self.db_path).exists():
            logger.warning("No outcomes database, no failures to detect")
            return []

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()

        cursor.execute(
            """SELECT task_id, task_description, agent, level, success, 
                      latency_ms, context_json, timestamp
               FROM outcomes 
               WHERE timestamp > ? AND success = 0
               ORDER BY timestamp DESC""",
            (cutoff,),
        )

        failures = []
        for row in cursor.fetchall():
            failure_type = self._classify_failure(row[5], row[6])
            severity = self._calculate_severity(row[5], row[6])

            failures.append(
                Failure(
                    task_id=row[0],
                    task_description=row[1],
                    agent=row[2],
                    level=row[3],
                    failure_type=failure_type,
                    severity=severity,
                    latency_ms=row[5],
                    error_context=json.loads(row[6]) if row[6] else {},
                    timestamp=row[7],
                )
            )

        conn.close()

        if len(failures) >= min_count:
            logger.info(f"Detected {len(failures)} failures in last {window_hours}h")
        else:
            logger.debug(f"Only {len(failures)} failures (min: {min_count})")

        return failures

    def _classify_failure(self, latency: float, context_json: str) -> str:
        """Classify failure type based on context."""
        try:
            context = json.loads(context_json) if context_json else {}
        except (json.JSONDecodeError, TypeError):
            context = {}

        if latency > 300000:
            return "timeout"
        if context.get("error"):
            return "error"
        if context.get("partial"):
            return "partial"
        return "quality"

    def _calculate_severity(self, latency: float, context_json: str) -> float:
        """Calculate severity score (0-1)."""
        severity = 0.3

        if latency > 300000:
            severity += 0.3
        elif latency > 120000:
            severity += 0.1

        try:
            context = json.loads(context_json) if context_json else {}
            if context.get("critical"):
                severity += 0.4
        except (json.JSONDecodeError, TypeError):
            pass

        return min(severity, 1.0)

    def analyze_root_cause(self, failure: Failure) -> RootCause:
        """Use chain-of-thought to analyze root cause of a failure.

        Args:
            failure: Failure object to analyze

        Returns:
            RootCause with analysis
        """
        evidence = []
        likely_cause = "unknown"

        if failure.failure_type == "timeout":
            likely_cause = "Task complexity exceeds agent capability"
            evidence.append(f"Latency: {failure.latency_ms}ms exceeded threshold")
            evidence.append(f"Agent: {failure.agent} (level {failure.level})")

        elif failure.failure_type == "error":
            likely_cause = "Implementation error in agent code"
            error_msg = failure.error_context.get("error", "")
            evidence.append(f"Error: {error_msg[:100]}")
            evidence.append(f"Task: {failure.task_description[:50]}")

        elif failure.failure_type == "partial":
            likely_cause = "Incomplete task resolution"
            evidence.append(f"Agent: {failure.agent} did not complete all steps")

        else:
            likely_cause = "Quality below acceptable threshold"
            evidence.append(f"Severity: {failure.severity}")
            evidence.append(f"Level: L{failure.level} may be insufficient")

        confidence = 0.5 + (failure.severity * 0.3)

        return RootCause(
            pattern=f"{failure.failure_type}:{failure.agent}:L{failure.level}",
            likely_cause=likely_cause,
            evidence=evidence,
            confidence=confidence,
        )

    def extract_patterns(self, failures: list[Failure]) -> dict[str, list[Failure]]:
        """Extract patterns from failures.

        Args:
            failures: List of detected failures

        Returns:
            Dictionary mapping pattern_key to list of failures
        """
        patterns: dict[str, list[Failure]] = {}

        for f in failures:
            key = f"{f.failure_type}:{f.agent}:L{f.level}"
            if key not in patterns:
                patterns[key] = []
            patterns[key].append(f)

        significant_patterns = {
            k: v for k, v in patterns.items() if len(v) >= MIN_FAILURE_COUNT
        }

        logger.info(f"Extracted {len(significant_patterns)} significant patterns")
        for pattern, fails in significant_patterns.items():
            logger.debug(f"  {pattern}: {len(fails)} failures")

        return significant_patterns

    def generate_correction(
        self, patterns: dict[str, list[Failure]]
    ) -> list[Correction]:
        """Generate corrections for identified patterns.

        Args:
            patterns: Dictionary of pattern_key -> failures

        Returns:
            List of Correction objects
        """
        corrections = []

        for pattern_key, failures in patterns.items():
            if len(failures) < MIN_FAILURE_COUNT:
                continue

            parts = pattern_key.split(":")
            if len(parts) != 3:
                continue

            failure_type, agent, level_str = parts
            level = int(level_str.replace("L", ""))

            if failure_type == "timeout":
                correction = Correction(
                    pattern_id=pattern_key,
                    description=f"Increase timeout or route to higher-level agent for {agent}",
                    action_type="route_change",
                    target_agent=agent,
                    parameters={"increase_level": True, "timeout_ms": 600000},
                    priority=2 if len(failures) > 5 else 3,
                )

            elif failure_type == "error":
                correction = Correction(
                    pattern_id=pattern_key,
                    description=f"Retrain {agent} on similar task types",
                    action_type="retrain",
                    target_agent=agent,
                    parameters={
                        "task_type": failures[0].task_type,
                        "retrain_samples": len(failures),
                    },
                    priority=2,
                )

            elif failure_type == "partial":
                correction = Correction(
                    pattern_id=pattern_key,
                    description=f"Add verification step for {agent} on level {level} tasks",
                    action_type="config_update",
                    target_agent=agent,
                    parameters={"verify_completion": True},
                    priority=3,
                )

            else:
                correction = Correction(
                    pattern_id=pattern_key,
                    description=f"Review quality metrics for {agent} at level {level}",
                    action_type="param_adjust",
                    target_agent=agent,
                    parameters={"quality_threshold": 0.8},
                    priority=3,
                )

            corrections.append(correction)

        corrections.sort(key=lambda c: c.priority)
        logger.info(f"Generated {len(corrections)} corrections")

        return corrections

    def apply_correction(self, correction: Correction) -> bool:
        """Apply a correction by triggering training pipeline or config update.

        Args:
            correction: Correction to apply

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Applying correction: {correction.pattern_id}")

        if correction.action_type == "retrain":
            return self._trigger_retraining(correction)

        elif correction.action_type == "route_change":
            return self._update_routing(correction)

        elif correction.action_type == "config_update":
            return self._update_config(correction)

        elif correction.action_type == "param_adjust":
            return self._adjust_params(correction)

        return False

    def _trigger_retraining(self, correction: Correction) -> bool:
        """Trigger retraining for the target agent."""
        try:
            from packages.training.training_trigger import trigger_training_run

            result = trigger_training_run()

            if result.get("status") == "success":
                correction.applied = True
                logger.info(f"Retraining triggered for {correction.target_agent}")
                self._save_correction(correction)
                return True
            else:
                logger.error(f"Retraining failed: {result}")
                return False

        except ImportError:
            logger.error("Training trigger not available")
            return False
        except Exception as e:
            logger.error(f"Error triggering retraining: {e}")
            return False

    def _update_routing(self, correction: Correction) -> bool:
        """Update routing configuration."""
        try:
            config_path = PROJECT_ROOT / ".sisyphus" / "routing_overrides.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)

            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
            else:
                config = {}

            agent_config = config.get(correction.target_agent, {})
            agent_config.update(correction.parameters)
            config[correction.target_agent] = agent_config

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            correction.applied = True
            self._save_correction(correction)
            logger.info(f"Routing updated for {correction.target_agent}")
            return True

        except Exception as e:
            logger.error(f"Error updating routing: {e}")
            return False

    def _update_config(self, correction: Correction) -> bool:
        """Update agent configuration."""
        try:
            config_path = PROJECT_ROOT / ".sisyphus" / "agent_configs.json"

            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
            else:
                config = {}

            agent_key = correction.target_agent or "default"
            if agent_key not in config:
                config[agent_key] = {}

            config[agent_key].update(correction.parameters)

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            correction.applied = True
            self._save_correction(correction)
            logger.info(f"Config updated for {correction.target_agent}")
            return True

        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False

    def _adjust_params(self, correction: Correction) -> bool:
        """Adjust agent parameters."""
        return self._update_config(correction)

    def _save_correction(self, correction: Correction):
        """Save correction to patterns database."""
        PATTERNS_DB.parent.mkdir(parents=True, exist_ok=True)

        corrections = []
        if PATTERNS_DB.exists():
            with open(PATTERNS_DB) as f:
                corrections = json.load(f)

        corrections.append(
            {
                "pattern_id": correction.pattern_id,
                "description": correction.description,
                "action_type": correction.action_type,
                "target_agent": correction.target_agent,
                "parameters": correction.parameters,
                "priority": correction.priority,
                "applied": correction.applied,
                "timestamp": datetime.now().isoformat(),
            }
        )

        with open(PATTERNS_DB, "w") as f:
            json.dump(corrections, f, indent=2)

    def run_self_correction_loop(
        self, window_hours: int = FAILURE_WINDOW_HOURS
    ) -> dict[str, Any]:
        """Run the complete self-correction loop.

        Args:
            window_hours: Time window for failure detection

        Returns:
            Summary dictionary with results
        """
        result = {
            "failures_detected": 0,
            "patterns_extracted": 0,
            "corrections_generated": 0,
            "corrections_applied": 0,
            "status": "no_action",
        }

        failures = self.detect_failures(window_hours=window_hours)
        result["failures_detected"] = len(failures)

        if not failures:
            result["status"] = "no_failures"
            return result

        patterns = self.extract_patterns(failures)
        result["patterns_extracted"] = len(patterns)

        if not patterns:
            result["status"] = "no_patterns"
            return result

        corrections = self.generate_correction(patterns)
        result["corrections_generated"] = len(corrections)

        applied_count = 0
        for correction in corrections:
            if self.apply_correction(correction):
                applied_count += 1

        result["corrections_applied"] = applied_count

        if applied_count > 0:
            result["status"] = "corrected"
        else:
            result["status"] = "failed_apply"

        logger.info(f"Self-correction loop complete: {result}")
        return result


# ============================================================================
# CLI Interface
# ============================================================================


def main():
    """CLI interface for manual testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Correction Loop")
    parser.add_argument("--detect", action="store_true", help="Detect failures")
    parser.add_argument("--analyze", action="store_true", help="Analyze root causes")
    parser.add_argument("--extract", action="store_true", help="Extract patterns")
    parser.add_argument("--generate", action="store_true", help="Generate corrections")
    parser.add_argument("--apply", action="store_true", help="Apply corrections")
    parser.add_argument(
        "--run-loop", action="store_true", help="Run complete self-correction loop"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=FAILURE_WINDOW_HOURS,
        help=f"Detection window in hours (default: {FAILURE_WINDOW_HOURS})",
    )
    parser.add_argument("--agent", type=str, help="Filter by agent")

    args = parser.parse_args()

    analyzer = FailureAnalyzer()

    if args.run_loop:
        result = analyzer.run_self_correction_loop(window_hours=args.window)
        print(json.dumps(result, indent=2))
        return

    failures = analyzer.detect_failures(window_hours=args.window)

    if args.agent:
        failures = [f for f in failures if f.agent == args.agent]

    print(f"Detected {len(failures)} failures")

    if args.detect:
        for f in failures:
            print(
                f"  - [{f.failure_type}] {f.agent} L{f.level}: {f.task_description[:50]}..."
            )

    if args.analyze and failures:
        for f in failures[:5]:
            cause = analyzer.analyze_root_cause(f)
            print(f"\nRoot cause for {f.task_id}:")
            print(f"  Pattern: {cause.pattern}")
            print(f"  Cause: {cause.likely_cause}")
            print(f"  Confidence: {cause.confidence:.2f}")
            for e in cause.evidence:
                print(f"    - {e}")

    if args.extract and failures:
        patterns = analyzer.extract_patterns(failures)
        print(f"\nExtracted {len(patterns)} patterns:")
        for pattern, fails in patterns.items():
            print(f"  {pattern}: {len(fails)} failures")

    if args.generate and failures:
        patterns = analyzer.extract_patterns(failures)
        corrections = analyzer.generate_correction(patterns)
        print(f"\nGenerated {len(corrections)} corrections:")
        for c in corrections:
            print(f"  [{c.priority}] {c.action_type}: {c.description[:60]}...")

    if args.apply and failures:
        patterns = analyzer.extract_patterns(failures)
        corrections = analyzer.generate_correction(patterns)
        applied = 0
        for c in corrections:
            if analyzer.apply_correction(c):
                applied += 1
        print(f"\nApplied {applied}/{len(corrections)} corrections")


if __name__ == "__main__":
    main()
