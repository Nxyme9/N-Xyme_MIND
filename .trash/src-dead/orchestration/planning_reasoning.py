"""Planning/Reasoning — Advanced multi-step planning with dependency tracking.

Based on docs LAYER10-PLANNING-REASONING.md.

Implements:
- Multi-step planning with dependency tracking
- Reasoning chains for complex decisions
- Plan validation and adjustment
- Parallel execution opportunities
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PlanStatus(str, Enum):
    """Plan status states."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class PlanStep:
    """A single step in a plan."""

    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    estimated_duration_minutes: float = 0.0
    actual_duration_minutes: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    result: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocked(self) -> bool:
        """Check if step is blocked by dependencies."""
        return self.status == StepStatus.BLOCKED

    @property
    def is_ready(self) -> bool:
        """Check if step is ready to execute (all deps completed)."""
        return self.status == StepStatus.PENDING and not self.is_blocked


@dataclass
class Plan:
    """A multi-step plan with dependency tracking."""

    id: str
    title: str
    description: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[PlanStep] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def progress_pct(self) -> float:
        return (self.completed_steps / max(1, self.total_steps)) * 100

    @property
    def is_complete(self) -> bool:
        return all(s.status == StepStatus.COMPLETED for s in self.steps)

    @property
    def has_failures(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)


class PlanningEngine:
    """Advanced planning and reasoning engine."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize planning engine.

        Args:
            storage_path: Path to store plans.
        """
        self.storage_path = storage_path or Path(".sisyphus/plans")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.plans: dict[str, Plan] = {}
        self._load_plans()

    def create_plan(
        self,
        title: str,
        description: str,
        steps: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> Plan:
        """Create a new plan.

        Args:
            title: Plan title.
            description: Plan description.
            steps: List of step dicts with description, dependencies, etc.
            metadata: Additional metadata.

        Returns:
            Created Plan.
        """
        plan_id = str(uuid.uuid4())[:8]
        plan_steps = []

        for step_data in steps:
            step = PlanStep(
                id=str(uuid.uuid4())[:8],
                description=step_data.get("description", ""),
                dependencies=step_data.get("dependencies", []),
                estimated_duration_minutes=step_data.get(
                    "estimated_duration_minutes", 0.0
                ),
                metadata=step_data.get("metadata", {}),
            )
            plan_steps.append(step)

        plan = Plan(
            id=plan_id,
            title=title,
            description=description,
            steps=plan_steps,
            metadata=metadata or {},
        )
        self.plans[plan_id] = plan
        self._save_plan(plan)
        return plan

    def start_plan(self, plan_id: str) -> bool:
        """Start a plan.

        Args:
            plan_id: Plan ID.

        Returns:
            True if plan was started.
        """
        plan = self.plans.get(plan_id)
        if not plan or plan.status != PlanStatus.DRAFT:
            return False

        plan.status = PlanStatus.ACTIVE
        plan.started_at = datetime.now(timezone.utc).isoformat()

        # Check for blocked steps
        self._update_step_statuses(plan)
        self._save_plan(plan)
        return True

    def complete_step(self, plan_id: str, step_id: str, result: str = "") -> bool:
        """Complete a plan step.

        Args:
            plan_id: Plan ID.
            step_id: Step ID.
            result: Step result.

        Returns:
            True if step was completed.
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return False

        step = next((s for s in plan.steps if s.id == step_id), None)
        if not step or step.status not in (StepStatus.PENDING, StepStatus.IN_PROGRESS):
            return False

        step.status = StepStatus.COMPLETED
        step.result = result
        step.completed_at = datetime.now(timezone.utc).isoformat()

        # Update dependent steps
        self._update_step_statuses(plan)

        # Check if plan is complete
        if plan.is_complete:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now(timezone.utc).isoformat()

        self._save_plan(plan)
        return True

    def fail_step(self, plan_id: str, step_id: str, reason: str = "") -> bool:
        """Fail a plan step.

        Args:
            plan_id: Plan ID.
            step_id: Step ID.
            reason: Failure reason.

        Returns:
            True if step was failed.
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return False

        step = next((s for s in plan.steps if s.id == step_id), None)
        if not step:
            return False

        step.status = StepStatus.FAILED
        step.result = f"Failed: {reason}"
        step.completed_at = datetime.now(timezone.utc).isoformat()

        # Block dependent steps
        for other_step in plan.steps:
            if step_id in other_step.dependencies:
                other_step.status = StepStatus.BLOCKED

        self._save_plan(plan)
        return True

    def get_next_steps(self, plan_id: str) -> list[PlanStep]:
        """Get steps that are ready to execute.

        Args:
            plan_id: Plan ID.

        Returns:
            List of ready steps.
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return []

        return [s for s in plan.steps if s.is_ready]

    def get_parallel_groups(self, plan_id: str) -> list[list[PlanStep]]:
        """Get groups of steps that can be executed in parallel.

        Args:
            plan_id: Plan ID.

        Returns:
            List of step groups (each group can run in parallel).
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return []

        # Topological sort with parallel grouping
        completed = set()
        groups = []
        remaining = list(plan.steps)

        while remaining:
            # Find steps with all dependencies completed
            ready = []
            for step in remaining:
                if all(dep in completed for dep in step.dependencies):
                    ready.append(step)

            if not ready:
                # Circular dependency or all remaining are blocked
                break

            groups.append(ready)
            for step in ready:
                completed.add(step.id)
                remaining.remove(step)

        return groups

    def validate_plan(self, plan_id: str) -> list[str]:
        """Validate a plan for issues.

        Args:
            plan_id: Plan ID.

        Returns:
            List of validation issues.
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return ["Plan not found"]

        issues = []
        step_ids = {s.id for s in plan.steps}

        # Check for invalid dependencies
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    issues.append(f"Step {step.id} has invalid dependency: {dep_id}")

        # Check for circular dependencies
        visited = set()
        for step in plan.steps:
            if self._has_circular_dependency(step, plan.steps, visited):
                issues.append(f"Circular dependency detected involving step {step.id}")
                break

        # Check for orphaned steps (no path from start)
        start_steps = [s for s in plan.steps if not s.dependencies]
        if not start_steps:
            issues.append("No start steps (all steps have dependencies)")

        return issues

    def _has_circular_dependency(
        self,
        step: PlanStep,
        all_steps: list[PlanStep],
        visited: set[str],
        path: set[str] | None = None,
    ) -> bool:
        """Check for circular dependencies."""
        if path is None:
            path = set()

        if step.id in path:
            return True

        path.add(step.id)
        for dep_id in step.dependencies:
            dep_step = next((s for s in all_steps if s.id == dep_id), None)
            if dep_step and self._has_circular_dependency(
                dep_step, all_steps, visited, path
            ):
                return True

        path.discard(step.id)
        return False

    def _update_step_statuses(self, plan: Plan) -> None:
        """Update step statuses based on dependencies."""
        completed_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}
        failed_ids = {s.id for s in plan.steps if s.status == StepStatus.FAILED}

        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                # Check if any dependency failed
                if any(dep in failed_ids for dep in step.dependencies):
                    step.status = StepStatus.BLOCKED
                # Check if all dependencies completed
                elif all(dep in completed_ids for dep in step.dependencies):
                    step.status = StepStatus.PENDING  # Ready to execute

    def _save_plan(self, plan: Plan) -> None:
        """Save plan to storage."""
        plan_file = self.storage_path / f"{plan.id}.json"
        data = {
            "id": plan.id,
            "title": plan.title,
            "description": plan.description,
            "status": plan.status.value,
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "metadata": plan.metadata,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "status": s.status.value,
                    "estimated_duration_minutes": s.estimated_duration_minutes,
                    "actual_duration_minutes": s.actual_duration_minutes,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "result": s.result,
                    "metadata": s.metadata,
                }
                for s in plan.steps
            ],
        }
        plan_file.write_text(json.dumps(data, indent=2))

    def _load_plans(self) -> None:
        """Load plans from storage."""
        for plan_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(plan_file.read_text())
                steps = [
                    PlanStep(
                        id=s["id"],
                        description=s["description"],
                        dependencies=s.get("dependencies", []),
                        status=StepStatus(s.get("status", "pending")),
                        estimated_duration_minutes=s.get(
                            "estimated_duration_minutes", 0.0
                        ),
                        actual_duration_minutes=s.get("actual_duration_minutes", 0.0),
                        started_at=s.get("started_at", ""),
                        completed_at=s.get("completed_at", ""),
                        result=s.get("result", ""),
                        metadata=s.get("metadata", {}),
                    )
                    for s in data.get("steps", [])
                ]
                plan = Plan(
                    id=data["id"],
                    title=data["title"],
                    description=data["description"],
                    status=PlanStatus(data.get("status", "draft")),
                    steps=steps,
                    created_at=data.get("created_at", ""),
                    started_at=data.get("started_at", ""),
                    completed_at=data.get("completed_at", ""),
                    metadata=data.get("metadata", {}),
                )
                self.plans[plan.id] = plan
            except Exception as e:
                logger.warning(f"Failed to load plan {plan_file}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get planning statistics."""
        by_status: dict[str, int] = {}
        for plan in self.plans.values():
            by_status[plan.status.value] = by_status.get(plan.status.value, 0) + 1

        return {
            "total_plans": len(self.plans),
            "by_status": by_status,
            "total_steps": sum(p.total_steps for p in self.plans.values()),
            "completed_steps": sum(p.completed_steps for p in self.plans.values()),
        }


# Global singleton
_planning_engine = PlanningEngine()


def create_plan(
    title: str,
    description: str,
    steps: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> Plan:
    """Convenience function to create a plan."""
    return _planning_engine.create_plan(title, description, steps, metadata)


def get_parallel_groups(plan_id: str) -> list[list[PlanStep]]:
    """Convenience function to get parallel groups."""
    return _planning_engine.get_parallel_groups(plan_id)
