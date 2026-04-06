"""
Governance — AI risk classification, doom loop prevention, governance state machine.

Implements EU AI Act risk tier classification (minimal/low/high/critical),
doom loop detection via max iterations and circuit breaker integration,
and a governance state machine for lifecycle management.

Usage:
    gov = Governance(risk_tier="high", max_iterations=5)
    gov.record_decision("Retrying LLM call", metadata={"attempt": 1})
    gov.transition(GovernanceState.REVIEW)
    state = gov.get_state()
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EU AI Act Risk Tiers
# ---------------------------------------------------------------------------


class RiskTier(Enum):
    """EU AI Act risk classification levels.

    Tiers determine required governance controls, audit frequency,
    and escalation thresholds.

    Attributes:
        MINIMAL: Negligible risk (e.g. spam filters, simple automation).
        LOW: Limited risk with specific transparency obligations (e.g. chatbots).
        HIGH: Significant risk requiring strict controls (e.g. medical, hiring).
        CRITICAL: Unacceptable risk — prohibited or requires explicit human oversight.
    """

    MINIMAL = "minimal"
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RiskProfile:
    """Immutable risk profile for a given tier.

    Defines the governance controls automatically applied per tier.
    """

    tier: RiskTier
    max_iterations: int
    audit_frequency_seconds: float
    requires_human_approval: bool
    requires_explainability: bool
    escalation_threshold: int  # number of consecutive failures before escalation


# Pre-computed profiles per EU AI Act tier.
RISK_PROFILES: dict[RiskTier, RiskProfile] = {
    RiskTier.MINIMAL: RiskProfile(
        tier=RiskTier.MINIMAL,
        max_iterations=20,
        audit_frequency_seconds=300.0,
        requires_human_approval=False,
        requires_explainability=False,
        escalation_threshold=10,
    ),
    RiskTier.LOW: RiskProfile(
        tier=RiskTier.LOW,
        max_iterations=10,
        audit_frequency_seconds=120.0,
        requires_human_approval=False,
        requires_explainability=True,
        escalation_threshold=5,
    ),
    RiskTier.HIGH: RiskProfile(
        tier=RiskTier.HIGH,
        max_iterations=5,
        audit_frequency_seconds=30.0,
        requires_human_approval=True,
        requires_explainability=True,
        escalation_threshold=3,
    ),
    RiskTier.CRITICAL: RiskProfile(
        tier=RiskTier.CRITICAL,
        max_iterations=1,
        audit_frequency_seconds=5.0,
        requires_human_approval=True,
        requires_explainability=True,
        escalation_threshold=1,
    ),
}


# ---------------------------------------------------------------------------
# Doom Loop Prevention
# ---------------------------------------------------------------------------


class DoomLoopDetected(Exception):
    """Raised when the system detects a repeating action pattern (doom loop)."""

    pass


@dataclass
class DoomLoopGuard:
    """Prevents infinite retry / doom-loop scenarios.

    Tracks iteration counts, action fingerprints, and enforces
    hard limits from the associated risk profile.

    Attributes:
        max_iterations: Hard cap on consecutive retries.
        escalation_threshold: Failures before escalation is triggered.
        _iteration_count: Current iteration counter.
        _consecutive_failures: Running count of unbroken failures.
        _action_history: Recent action fingerprints for pattern detection.
        _total_decisions: Lifetime decision counter.
    """

    max_iterations: int
    escalation_threshold: int
    _iteration_count: int = field(default=0, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _action_history: list[str] = field(default_factory=list, init=False)
    _total_decisions: int = field(default=0, init=False)

    def record_attempt(self, action_fingerprint: str = "") -> None:
        """Record a new iteration attempt.

        Raises DoomLoopDetected if max_iterations is exceeded or
        a repeating action pattern is found in recent history.
        """
        self._iteration_count += 1
        self._total_decisions += 1

        if action_fingerprint:
            self._action_history.append(action_fingerprint)
            # Keep only last 10 for pattern detection
            if len(self._action_history) > 10:
                self._action_history = self._action_history[-10:]
            self._check_repeating_pattern()

        if self._iteration_count > self.max_iterations:
            raise DoomLoopDetected(
                f"Doom loop detected: {self._iteration_count} iterations "
                f"exceeds limit of {self.max_iterations}"
            )

    def record_success(self) -> None:
        """Record a successful outcome, resetting failure counters."""
        self._consecutive_failures = 0
        self._iteration_count = 0
        self._action_history.clear()

    def record_failure(self) -> bool:
        """Record a failure. Returns True if escalation threshold is reached."""
        self._consecutive_failures += 1
        return self._consecutive_failures >= self.escalation_threshold

    def should_escalate(self) -> bool:
        """Check if escalation is warranted based on consecutive failures."""
        return self._consecutive_failures >= self.escalation_threshold

    def _check_repeating_pattern(self) -> None:
        """Detect A→B→A→B or exact-repeat patterns in recent history."""
        history = self._action_history
        if len(history) < 4:
            return

        # Exact repeat: same action as 2 steps ago AND 4 steps ago
        if len(history) >= 5 and history[-1] == history[-3] == history[-5]:
            raise DoomLoopDetected(
                f"Repeating pattern detected: '{history[-1]}' repeated "
                f"every 2 steps for {len(history)} iterations"
            )

        # A→B→A→B cycle
        if len(history) >= 4:
            a, b = history[-2], history[-1]
            if history[-4] == a and history[-3] == b:
                raise DoomLoopDetected(
                    f"Alternating pattern detected: '{a}' <-> '{b}' cycling"
                )

    def get_stats(self) -> Dict[str, Any]:
        """Return guard statistics."""
        return {
            "iteration_count": self._iteration_count,
            "consecutive_failures": self._consecutive_failures,
            "total_decisions": self._total_decisions,
            "action_history_length": len(self._action_history),
            "max_iterations": self.max_iterations,
            "escalation_threshold": self.escalation_threshold,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self._iteration_count = 0
        self._consecutive_failures = 0
        self._action_history.clear()


# ---------------------------------------------------------------------------
# Governance State Machine
# ---------------------------------------------------------------------------


class GovernanceState(Enum):
    """States in the governance lifecycle.

    State transitions follow a directed graph to ensure proper
    review and approval flow.
    """

    INIT = "init"
    RUNNING = "running"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    HALTED = "halted"


# Valid transitions per state.
_STATE_TRANSITIONS: dict[GovernanceState, set[GovernanceState]] = {
    GovernanceState.INIT: {GovernanceState.RUNNING, GovernanceState.HALTED},
    GovernanceState.RUNNING: {
        GovernanceState.REVIEW,
        GovernanceState.ESCALATED,
        GovernanceState.HALTED,
    },
    GovernanceState.REVIEW: {
        GovernanceState.APPROVED,
        GovernanceState.REJECTED,
        GovernanceState.RUNNING,
    },
    GovernanceState.APPROVED: {GovernanceState.RUNNING, GovernanceState.INIT},
    GovernanceState.REJECTED: {GovernanceState.INIT, GovernanceState.HALTED},
    GovernanceState.ESCALATED: {
        GovernanceState.RUNNING,
        GovernanceState.REJECTED,
        GovernanceState.HALTED,
    },
    GovernanceState.HALTED: {GovernanceState.INIT},
}


@dataclass
class DecisionRecord:
    """A single governance decision entry."""

    timestamp: float
    action: str
    outcome: str  # "success", "failure", "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Governance:
    """Main governance controller.

    Combines risk tier classification, doom loop prevention,
    and a state machine into a single orchestratable unit.

    Attributes:
        risk_tier: Current EU AI Act risk classification.
        profile: Immutable risk profile derived from the tier.
        state: Current governance state machine state.
        doom_guard: Doom loop prevention guard.
        decisions: Chronological log of governance decisions.
        audit_callback: Optional callback for audit integration.
    """

    def __init__(
        self,
        risk_tier: str = "low",
        max_iterations: Optional[int] = None,
        audit_callback: Optional[Any] = None,
    ) -> None:
        """Initialise governance with a risk tier.

        Args:
            risk_tier: One of "minimal", "low", "high", "critical".
            max_iterations: Override the tier's default max iterations.
            audit_callback: Optional callable(event_type, description, metadata)
                for integration with external audit systems.
        """
        self.risk_tier = self._resolve_tier(risk_tier)
        self.profile = RISK_PROFILES[self.risk_tier]
        self.state = GovernanceState.INIT
        self.doom_guard = DoomLoopGuard(
            max_iterations=max_iterations or self.profile.max_iterations,
            escalation_threshold=self.profile.escalation_threshold,
        )
        self.decisions: List[DecisionRecord] = []
        self.audit_callback = audit_callback
        self._created_at = time.time()
        self._last_audit = 0.0

        self._audit(
            "governance_init", f"Governance initialised at tier {self.risk_tier.value}"
        )

    # -- Risk tier classification -------------------------------------------

    @staticmethod
    def _resolve_tier(tier_str: str) -> RiskTier:
        """Resolve a string to a RiskTier enum value.

        Args:
            tier_str: Risk tier name (case-insensitive).

        Returns:
            The corresponding RiskTier enum member.

        Raises:
            ValueError: If the tier string is not recognised.
        """
        try:
            return RiskTier(tier_str.lower())
        except ValueError:
            valid = ", ".join(t.value for t in RiskTier)
            raise ValueError(
                f"Unknown risk tier '{tier_str}'. Valid tiers: {valid}"
            ) from None

    @classmethod
    def classify_risk(
        cls,
        has_human_oversight: bool = False,
        affects_fundamental_rights: bool = False,
        safety_critical: bool = False,
        is_prohibited_use: bool = False,
    ) -> RiskTier:
        """Classify risk based on system characteristics.

        Follows EU AI Act classification logic.

        Args:
            has_human_oversight: Whether meaningful human oversight exists.
            affects_fundamental_rights: Whether the system impacts fundamental rights.
            safety_critical: Whether the system is safety-critical (medical, transport).
            is_prohibited_use: Whether the use case is prohibited under the Act.

        Returns:
            The appropriate RiskTier.
        """
        if is_prohibited_use:
            return RiskTier.CRITICAL
        if safety_critical or affects_fundamental_rights:
            return RiskTier.HIGH
        if not has_human_oversight:
            return RiskTier.LOW
        return RiskTier.MINIMAL

    # -- State machine ------------------------------------------------------

    def transition(self, target: GovernanceState) -> bool:
        """Attempt a state transition.

        Args:
            target: The desired next state.

        Returns:
            True if the transition was valid and applied.

        Raises:
            ValueError: If the transition is not allowed from the current state.
        """
        allowed = _STATE_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {target.value}. "
                f"Allowed: {', '.join(s.value for s in allowed)}"
            )

        old_state = self.state
        self.state = target
        self._audit(
            "state_transition",
            f"Transitioned from {old_state.value} to {target.value}",
        )
        logger.info(f"Governance: {old_state.value} -> {target.value}")
        return True

    # -- Doom loop integration ----------------------------------------------

    def record_decision(
        self,
        action: str,
        outcome: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionRecord:
        """Record a governance decision with doom loop tracking.

        Args:
            action: Human-readable description of the action taken.
            outcome: One of "success", "failure", "pending".
            metadata: Optional additional context.

        Returns:
            The created DecisionRecord.

        Raises:
            DoomLoopDetected: If a doom loop pattern is detected.
        """
        record = DecisionRecord(
            timestamp=time.time(),
            action=action,
            outcome=outcome,
            metadata=metadata or {},
        )
        self.decisions.append(record)

        # Track iterations and detect loops
        self.doom_guard.record_attempt(action)

        if outcome == "success":
            self.doom_guard.record_success()
        elif outcome == "failure":
            needs_escalation = self.doom_guard.record_failure()
            if needs_escalation and self.state == GovernanceState.RUNNING:
                self.transition(GovernanceState.ESCALATED)
                self._audit(
                    "auto_escalation",
                    f"Escalated after {self.doom_guard._consecutive_failures} consecutive failures",
                )

        self._last_audit = time.time()
        return record

    def check_doom_loop(self) -> Dict[str, Any]:
        """Return current doom loop guard statistics."""
        return self.doom_guard.get_stats()

    def reset_guard(self) -> None:
        """Reset the doom loop guard counters."""
        self.doom_guard.reset()
        self._audit("guard_reset", "Doom loop guard counters reset")

    # -- Audit integration --------------------------------------------------

    def _audit(
        self,
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an audit event via callback and local logger.

        Non-blocking: callback failures are logged but do not
        interrupt governance operations.
        """
        meta = {"risk_tier": self.risk_tier.value, "state": self.state.value}
        if metadata:
            meta.update(metadata)

        # Local logger (always available)
        logger.info(f"Governance[{self.risk_tier.value}]: {description}")

        # External audit callback (optional, non-blocking)
        if self.audit_callback:
            try:
                self.audit_callback(event_type, description, meta)
            except Exception as e:
                logger.warning(f"Governance: audit callback failed: {e}")

    # -- State reporting ----------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Return a complete governance state snapshot."""
        return {
            "risk_tier": self.risk_tier.value,
            "state": self.state.value,
            "profile": {
                "max_iterations": self.profile.max_iterations,
                "audit_frequency_seconds": self.profile.audit_frequency_seconds,
                "requires_human_approval": self.profile.requires_human_approval,
                "requires_explainability": self.profile.requires_explainability,
                "escalation_threshold": self.profile.escalation_threshold,
            },
            "doom_guard": self.doom_guard.get_stats(),
            "total_decisions": len(self.decisions),
            "uptime_seconds": time.time() - self._created_at,
        }

    def needs_audit(self) -> bool:
        """Check if an audit is due based on the tier's frequency."""
        if self._last_audit == 0.0:
            return True
        elapsed = time.time() - self._last_audit
        return elapsed >= self.profile.audit_frequency_seconds

    def requires_approval(self) -> bool:
        """Check if the current tier requires human approval."""
        return self.profile.requires_human_approval

    def requires_explainability(self) -> bool:
        """Check if the current tier requires explainability."""
        return self.profile.requires_explainability
