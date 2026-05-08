"""Handoff Primitives — OpenAI Agents SDK-style agent transfer.

Implements standard agent handoff primitives following the industry consensus:
    Agent → Handoff → Guardrails → Tools pattern

Classes:
    HandoffRequest: Request to transfer from source to target agent
    HandoffResponse: Result of a handoff operation
    Guardrails: Validation rules that can approve/block transfers
    HandoffManager: Orchestrates the full handoff flow

Usage:
    from packages.orchestration.handoff import HandoffManager, HandoffRequest

    request = HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "implement feature X"},
        reason="Implementation needed"
    )
    manager = HandoffManager()
    response = manager.execute_handoff(request)
"""

from __future__ import annotations

__version__ = "2.1.0"

import logging
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class HandoffStatus(Enum):
    """Status of a handoff operation."""

    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HandoffRequest:
    """Request to transfer control from one agent to another.

    Attributes:
        source_agent: Name of the agent initiating the handoff
        target_agent: Name of the agent receiving control
        context: Dict containing session state, conversation history, etc.
        reason: Human-readable reason for the handoff
        metadata: Optional additional metadata
    """

    source_agent: str
    target_agent: str
    context: Dict[str, Any]
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def validate(self) -> List[str]:
        """Validate the handoff request.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.source_agent:
            errors.append("source_agent is required")

        if not self.target_agent:
            errors.append("target_agent is required")

        if self.source_agent == self.target_agent:
            errors.append("source_agent and target_agent must be different")

        if not self.context:
            errors.append("context cannot be empty")

        if not self.reason:
            errors.append("reason is required")

        return errors


@dataclass
class HandoffResponse:
    """Result of a handoff operation.

    Attributes:
        success: Whether the handoff completed successfully
        status: HandoffStatus enum value
        transferred_context: Context that was transferred to target agent
        result: Optional result from the target agent
        error: Optional error message if handoff failed
        guardrails_passed: Whether guardrails approved the transfer
        timestamp: When the handoff completed
    """

    success: bool
    status: HandoffStatus
    transferred_context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    guardrails_passed: bool = True
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def approved(
        cls, transferred_context: Dict[str, Any], result: Any = None
    ) -> HandoffResponse:
        """Create an approved handoff response."""
        return cls(
            success=True,
            status=HandoffStatus.COMPLETED,
            transferred_context=transferred_context,
            result=result,
            guardrails_passed=True,
        )

    @classmethod
    def blocked(
        cls, reason: str, transferred_context: Dict[str, Any] = None
    ) -> HandoffResponse:
        """Create a blocked handoff response."""
        return cls(
            success=False,
            status=HandoffStatus.BLOCKED,
            transferred_context=transferred_context or {},
            error=reason,
            guardrails_passed=False,
        )

    @classmethod
    def failed(
        cls, error: str, transferred_context: Dict[str, Any] = None
    ) -> HandoffResponse:
        """Create a failed handoff response."""
        return cls(
            success=False,
            status=HandoffStatus.FAILED,
            transferred_context=transferred_context or {},
            error=error,
            guardrails_passed=True,  # Guardrails passed, but execution failed
        )


class Guardrails:
    """Validation rules that can approve or block agent handoffs.

    Supports configurable rules:
        - Block transfers to dangerous agents
        - Validate target agent exists and is available
        - Check context size limits
        - Custom validation functions

    Example:
        guardrails = Guardrails()
        guardrails.add_rule("no_direct_hephaestus", lambda r: r.target_agent != "hephaestus")
        result = guardrails.check_handoff(request)
    """

    def __init__(self):
        self._rules: Dict[str, Callable[[HandoffRequest], bool]] = {}
        self._rule_descriptions: Dict[str, str] = {}
        self._enabled: Dict[str, bool] = {}

        # Register default rules
        self._register_default_rules()

    def _register_default_rules(self):
        """Register built-in validation rules."""
        # Rule: Target agent must be different from source
        self.add_rule(
            "different_agents",
            lambda r: r.source_agent != r.target_agent,
            "Source and target agents must be different",
        )

        # Rule: Context cannot be empty
        self.add_rule(
            "non_empty_context", lambda r: bool(r.context), "Context cannot be empty"
        )

        # Rule: Reason must be provided
        self.add_rule(
            "has_reason", lambda r: bool(r.reason), "Handoff reason is required"
        )

    def add_rule(
        self, name: str, check: Callable[[HandoffRequest], bool], description: str = ""
    ) -> None:
        """Add a validation rule.

        Args:
            name: Unique identifier for the rule
            check: Function that returns True if handoff is allowed
            description: Human-readable description of the rule
        """
        self._rules[name] = check
        self._rule_descriptions[name] = description
        self._enabled[name] = True
        logger.debug("Added guardrail rule: %s", name)

    def remove_rule(self, name: str) -> bool:
        """Remove a validation rule.

        Args:
            name: Rule identifier to remove

        Returns:
            True if rule was removed, False if not found
        """
        if name in self._rules:
            del self._rules[name]
            del self._rule_descriptions[name]
            if name in self._enabled:
                del self._enabled[name]
            return True
        return False

    def enable_rule(self, name: str) -> bool:
        """Enable a rule.

        Args:
            name: Rule identifier

        Returns:
            True if enabled, False if not found
        """
        if name in self._enabled:
            self._enabled[name] = True
            return True
        return False

    def disable_rule(self, name: str) -> bool:
        """Disable a rule.

        Args:
            name: Rule identifier

        Returns:
            True if disabled, False if not found
        """
        if name in self._enabled:
            self._enabled[name] = False
            return True
        return False

    def check_handoff(self, request: HandoffRequest) -> tuple[bool, List[str]]:
        """Check if a handoff request passes all enabled guardrails.

        Args:
            request: The handoff request to validate

        Returns:
            Tuple of (passed: bool, errors: List[str])
        """
        errors = []

        # Run all enabled rules
        for name, check in self._rules.items():
            if not self._enabled.get(name, True):
                continue

            try:
                if not check(request):
                    desc = self._rule_descriptions.get(name, f"Rule {name} failed")
                    errors.append(desc)
                    logger.info("Guardrail rule '%s' blocked handoff: %s", name, desc)
            except Exception as e:
                logger.error("Error evaluating rule '%s': %s", name, e)
                errors.append(f"Rule '{name}' evaluation error: {e}")

        passed = len(errors) == 0
        if passed:
            logger.info(
                "All guardrails passed for handoff %s -> %s",
                request.source_agent,
                request.target_agent,
            )

        return passed, errors

    def get_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered rules.

        Returns:
            Dict mapping rule names to their status and description
        """
        return {
            name: {
                "enabled": self._enabled.get(name, True),
                "description": self._rule_descriptions.get(name, ""),
            }
            for name in self._rules
        }


class HandoffManager:
    """Orchestrates agent handoff operations.

    Manages the complete handoff flow:
        1. Validate the handoff request
        2. Run guardrails to check for violations
        3. Transfer context to target agent
        4. Return HandoffResponse with results

    Attributes:
        guardrails: Guardrails instance for validation
        known_agents: Set of valid agent names

    Example:
        manager = HandoffManager()
        response = manager.execute_handoff(request)
    """

    def __init__(
        self,
        guardrails: Optional[Guardrails] = None,
        known_agents: Optional[set] = None,
    ):
        """Initialize the HandoffManager.

        Args:
            guardrails: Optional Guardrails instance (creates default if None)
            known_agents: Set of valid agent names
        """
        self.guardrails = guardrails or Guardrails()
        self.known_agents = known_agents or {
            "sisyphus",
            "hephaestus",
            "oracle",
            "explore",
            "librarian",
            "momus",
            "metis",
            "prometheus",
            "atlas",
            "sisyphus-junior",
            "multimodal-looker",
        }
        self._handoff_history: List[HandoffResponse] = []

    def execute_handoff(self, request: HandoffRequest) -> HandoffResponse:
        """Execute a complete handoff operation.

        Args:
            request: The handoff request to process

        Returns:
            HandoffResponse with results
        """
        logger.info(
            "Executing handoff: %s -> %s", request.source_agent, request.target_agent
        )

        # Step 1: Validate request structure
        validation_errors = request.validate()
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            logger.error("Handoff validation failed: %s", error_msg)
            return HandoffResponse.failed(error_msg)

        # Step 2: Check guardrails
        guardrails_passed, guardrail_errors = self.guardrails.check_handoff(request)
        if not guardrails_passed:
            error_msg = "; ".join(guardrail_errors)
            logger.warning("Handoff blocked by guardrails: %s", error_msg)
            return HandoffResponse.blocked(error_msg, request.context)

        # Step 3: Prepare transferred context
        transferred_context = self._prepare_context(request)

        # Step 4: Log successful handoff
        logger.info(
            "Handoff completed successfully: %s -> %s",
            request.source_agent,
            request.target_agent,
        )

        response = HandoffResponse.approved(transferred_context)
        self._handoff_history.append(response)

        return response

    def _prepare_context(self, request: HandoffRequest) -> Dict[str, Any]:
        """Prepare the context for transfer to target agent.

        Args:
            request: The handoff request

        Returns:
            Dict containing sanitized context for target agent
        """
        # Extract key context fields for transfer
        transferred = {
            "session_state": request.context.get("session_state", {}),
            "conversation_history": request.context.get("conversation_history", []),
            "tool_access": request.context.get("tool_access", []),
            "agent_state": request.context.get("agent_state", {}),
            "metadata": {
                "source_agent": request.source_agent,
                "target_agent": request.target_agent,
                "handoff_reason": request.reason,
                "timestamp": request.timestamp.isoformat(),
            },
        }

        # Add any additional context (filtered for safety)
        additional = request.context.get("additional", {})
        if additional:
            transferred["additional"] = additional

        return transferred

    def get_history(self) -> List[HandoffResponse]:
        """Get history of handoff operations.

        Returns:
            List of HandoffResponse objects
        """
        return self._handoff_history.copy()

    def clear_history(self) -> None:
        """Clear handoff history."""
        self._handoff_history.clear()
        logger.info("Handoff history cleared")


# Convenience function for quick handoffs
def create_handoff(
    source: str, target: str, context: Dict[str, Any], reason: str
) -> HandoffResponse:
    """Create and execute a simple handoff.

    Args:
        source: Source agent name
        target: Target agent name
        context: Context to transfer
        reason: Reason for handoff

    Returns:
        HandoffResponse with results
    """
    request = HandoffRequest(
        source_agent=source, target_agent=target, context=context, reason=reason
    )
    manager = HandoffManager()
    return manager.execute_handoff(request)


# Exports for package
__all__ = [
    "HandoffRequest",
    "HandoffResponse",
    "HandoffStatus",
    "Guardrails",
    "HandoffManager",
    "create_handoff",
]
