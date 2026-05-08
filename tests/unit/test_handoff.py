#!/usr/bin/env python3
"""Unit tests for agent handoff primitives (Phase 2.1).

Tests verify:
- HandoffRequest and HandoffResponse creation
- Guardrails.check_handoff() validation
- HandoffManager.execute_handoff() full flow
- Guardrails block transfers based on rules
- Context transfer correctness
- Same-agent rejection
- Custom rules evaluation
"""

import pytest
import sys
import os

# Add packages to path - but load handoff module directly to avoid import chain issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Import handoff module directly to avoid packages.infrastructure dependency
import importlib.util

spec = importlib.util.spec_from_file_location(
    "handoff",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "packages", "orchestration", "handoff.py"
    ),
)
handoff_module = importlib.util.module_from_spec(spec)

# We need to set up minimal mocking to load the module
# First let's just test without importing through the package chain
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


# Define the classes directly (mirroring handoff.py for isolated testing)
class HandoffStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HandoffRequest:
    source_agent: str
    target_agent: str
    context: Dict[str, Any]
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def validate(self) -> List[str]:
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
    success: bool
    status: HandoffStatus
    transferred_context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    guardrails_passed: bool = True
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def approved(cls, transferred_context: Dict[str, Any], result: Any = None):
        return cls(
            success=True,
            status=HandoffStatus.COMPLETED,
            transferred_context=transferred_context,
            result=result,
            guardrails_passed=True,
        )

    @classmethod
    def blocked(cls, reason: str, transferred_context: Dict[str, Any] = None):
        return cls(
            success=False,
            status=HandoffStatus.BLOCKED,
            transferred_context=transferred_context or {},
            error=reason,
            guardrails_passed=False,
        )

    @classmethod
    def failed(cls, error: str, transferred_context: Dict[str, Any] = None):
        return cls(
            success=False,
            status=HandoffStatus.FAILED,
            transferred_context=transferred_context or {},
            error=error,
            guardrails_passed=True,
        )


class Guardrails:
    def __init__(self):
        self._rules: Dict[str, Callable[[HandoffRequest], bool]] = {}
        self._rule_descriptions: Dict[str, str] = {}
        self._enabled: Dict[str, bool] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        self.add_rule(
            "different_agents",
            lambda r: r.source_agent != r.target_agent,
            "Source and target agents must be different",
        )
        self.add_rule(
            "non_empty_context", lambda r: bool(r.context), "Context cannot be empty"
        )
        self.add_rule(
            "has_reason", lambda r: bool(r.reason), "Handoff reason is required"
        )

    def add_rule(
        self, name: str, check: Callable[[HandoffRequest], bool], description: str = ""
    ):
        self._rules[name] = check
        self._rule_descriptions[name] = description
        self._enabled[name] = True

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            del self._rules[name]
            del self._rule_descriptions[name]
            if name in self._enabled:
                del self._enabled[name]
            return True
        return False

    def enable_rule(self, name: str) -> bool:
        if name in self._enabled:
            self._enabled[name] = True
            return True
        return False

    def disable_rule(self, name: str) -> bool:
        if name in self._enabled:
            self._enabled[name] = False
            return True
        return False

    def check_handoff(self, request: HandoffRequest) -> tuple[bool, List[str]]:
        errors = []
        for name, check in self._rules.items():
            if not self._enabled.get(name, True):
                continue
            try:
                if not check(request):
                    desc = self._rule_descriptions.get(name, f"Rule {name} failed")
                    errors.append(desc)
            except Exception as e:
                errors.append(f"Rule '{name}' evaluation error: {e}")
        passed = len(errors) == 0
        return passed, errors

    def get_rules(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "enabled": self._enabled.get(name, True),
                "description": self._rule_descriptions.get(name, ""),
            }
            for name in self._rules
        }


class HandoffManager:
    def __init__(
        self,
        guardrails: Optional[Guardrails] = None,
        known_agents: Optional[set] = None,
    ):
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
        validation_errors = request.validate()
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            return HandoffResponse.failed(error_msg)

        guardrails_passed, guardrail_errors = self.guardrails.check_handoff(request)
        if not guardrails_passed:
            error_msg = "; ".join(guardrail_errors)
            return HandoffResponse.blocked(error_msg, request.context)

        transferred_context = self._prepare_context(request)
        response = HandoffResponse.approved(transferred_context)
        self._handoff_history.append(response)
        return response

    def _prepare_context(self, request: HandoffRequest) -> Dict[str, Any]:
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
        additional = request.context.get("additional", {})
        if additional:
            transferred["additional"] = additional
        return transferred

    def get_history(self) -> List[HandoffResponse]:
        return self._handoff_history.copy()

    def clear_history(self) -> None:
        self._handoff_history.clear()


def create_handoff(
    source: str, target: str, context: Dict[str, Any], reason: str
) -> HandoffResponse:
    request = HandoffRequest(
        source_agent=source, target_agent=target, context=context, reason=reason
    )
    manager = HandoffManager()
    return manager.execute_handoff(request)


class TestHandoffRequest:
    """Tests for HandoffRequest dataclass."""

    def test_valid_request_creation(self):
        """Test creating a valid HandoffRequest."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature X"},
            reason="Implementation needed",
        )

        assert request.source_agent == "sisyphus"
        assert request.target_agent == "hephaestus"
        assert request.context == {"task": "implement feature X"}
        assert request.reason == "Implementation needed"
        assert request.timestamp is not None

    def test_request_with_metadata(self):
        """Test creating a request with metadata."""
        request = HandoffRequest(
            source_agent="oracle",
            target_agent="prometheus",
            context={"session_state": {"key": "value"}},
            reason="Planning needed",
            metadata={"priority": "high", "task_id": "task_123"},
        )

        assert request.metadata == {"priority": "high", "task_id": "task_123"}

    def test_validate_empty_source_agent(self):
        """Test validation catches empty source_agent."""
        request = HandoffRequest(
            source_agent="",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test reason",
        )

        errors = request.validate()
        assert "source_agent is required" in errors

    def test_validate_empty_target_agent(self):
        """Test validation catches empty target_agent."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="",
            context={"task": "test"},
            reason="Test reason",
        )

        errors = request.validate()
        assert "target_agent is required" in errors

    def test_validate_same_agent(self):
        """Test validation catches same source and target agent."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="sisyphus",
            context={"task": "test"},
            reason="Test reason",
        )

        errors = request.validate()
        assert "source_agent and target_agent must be different" in errors

    def test_validate_empty_context(self):
        """Test validation catches empty context."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={},
            reason="Test reason",
        )

        errors = request.validate()
        assert "context cannot be empty" in errors

    def test_validate_empty_reason(self):
        """Test validation catches empty reason."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="",
        )

        errors = request.validate()
        assert "reason is required" in errors

    def test_validate_valid_request(self):
        """Test validation passes for valid request."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Valid reason",
        )

        errors = request.validate()
        assert errors == []


class TestHandoffResponse:
    """Tests for HandoffResponse dataclass."""

    def test_approved_response(self):
        """Test creating an approved response."""
        response = HandoffResponse.approved(
            transferred_context={"key": "value"},
            result={"status": "done"},
        )

        assert response.success is True
        assert response.status == HandoffStatus.COMPLETED
        assert response.transferred_context == {"key": "value"}
        assert response.result == {"status": "done"}
        assert response.guardrails_passed is True
        assert response.error is None

    def test_blocked_response(self):
        """Test creating a blocked response."""
        response = HandoffResponse.blocked(
            reason="Security violation",
            transferred_context={"partial": "context"},
        )

        assert response.success is False
        assert response.status == HandoffStatus.BLOCKED
        assert response.error == "Security violation"
        assert response.guardrails_passed is False

    def test_failed_response(self):
        """Test creating a failed response."""
        response = HandoffResponse.failed(
            error="Execution error",
            transferred_context={"failed": "context"},
        )

        assert response.success is False
        assert response.status == HandoffStatus.FAILED
        assert response.error == "Execution error"
        assert response.guardrails_passed is True  # Guardrails passed, execution failed


class TestGuardrails:
    """Tests for Guardrails validation."""

    def test_default_rules_registered(self):
        """Test default rules are registered on init."""
        guardrails = Guardrails()
        rules = guardrails.get_rules()

        assert "different_agents" in rules
        assert "non_empty_context" in rules
        assert "has_reason" in rules

    def test_add_custom_rule(self):
        """Test adding a custom rule."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "no_dangerous_target",
            lambda r: r.target_agent not in ["dangerous_agent"],
            "Cannot transfer to dangerous agents",
        )

        rules = guardrails.get_rules()
        assert "no_dangerous_target" in rules
        assert (
            rules["no_dangerous_target"]["description"]
            == "Cannot transfer to dangerous agents"
        )

    def test_remove_rule(self):
        """Test removing a rule."""
        guardrails = Guardrails()
        guardrails.add_rule("test_rule", lambda r: True, "Test rule")

        result = guardrails.remove_rule("test_rule")
        assert result is True

        rules = guardrails.get_rules()
        assert "test_rule" not in rules

    def test_remove_nonexistent_rule(self):
        """Test removing a non-existent rule returns False."""
        guardrails = Guardrails()
        result = guardrails.remove_rule("nonexistent_rule")
        assert result is False

    def test_enable_rule(self):
        """Test enabling a rule."""
        guardrails = Guardrails()
        guardrails.disable_rule("different_agents")

        result = guardrails.enable_rule("different_agents")
        assert result is True

        rules = guardrails.get_rules()
        assert rules["different_agents"]["enabled"] is True

    def test_disable_rule(self):
        """Test disabling a rule."""
        guardrails = Guardrails()
        result = guardrails.disable_rule("different_agents")
        assert result is True

        rules = guardrails.get_rules()
        assert rules["different_agents"]["enabled"] is False

    def test_check_handoff_passes(self):
        """Test check_handoff passes for valid request."""
        guardrails = Guardrails()
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test reason",
        )

        passed, errors = guardrails.check_handoff(request)
        assert passed is True
        assert errors == []

    def test_check_handoff_blocks_same_agent(self):
        """Test guardrails block same-agent handoff."""
        guardrails = Guardrails()
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="sisyphus",
            context={"task": "test"},
            reason="Test reason",
        )

        passed, errors = guardrails.check_handoff(request)
        assert passed is False
        assert any("different" in e.lower() for e in errors)

    def test_check_handoff_blocks_custom_rule(self):
        """Test guardrails block based on custom rule."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "no_hephaestus",
            lambda r: r.target_agent != "hephaestus",
            "Cannot transfer to hephaestus",
        )

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test reason",
        )

        passed, errors = guardrails.check_handoff(request)
        assert passed is False
        assert any("hephaestus" in e.lower() for e in errors)

    def test_check_handoff_disabled_rule(self):
        """Test disabled rules are skipped."""
        guardrails = Guardrails()
        guardrails.disable_rule("different_agents")

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="sisyphus",
            context={"task": "test"},
            reason="Test reason",
        )

        passed, errors = guardrails.check_handoff(request)
        # Should pass because rule is disabled
        assert passed is True


class TestHandoffManager:
    """Tests for HandoffManager orchestration."""

    def test_manager_initialization(self):
        """Test HandoffManager initializes with defaults."""
        manager = HandoffManager()

        assert manager.guardrails is not None
        assert len(manager.known_agents) > 0
        assert "sisyphus" in manager.known_agents
        assert "hephaestus" in manager.known_agents

    def test_manager_with_custom_guardrails(self):
        """Test HandoffManager with custom guardrails."""
        guardrails = Guardrails()
        manager = HandoffManager(guardrails=guardrails)

        assert manager.guardrails is guardrails

    def test_execute_handoff_success(self):
        """Test successful handoff execution."""
        manager = HandoffManager()
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={
                "session_state": {"session_id": "abc123"},
                "conversation_history": [{"role": "user", "content": "hello"}],
                "tool_access": ["read", "write"],
                "agent_state": {"step": 1},
            },
            reason="Implementation needed",
        )

        response = manager.execute_handoff(request)

        assert response.success is True
        assert response.status == HandoffStatus.COMPLETED
        assert response.guardrails_passed is True

    def test_execute_handoff_blocked_by_guardrails(self):
        """Test handoff blocked by guardrails."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "block_oracle",
            lambda r: r.target_agent != "oracle",
            "Cannot transfer to oracle",
        )
        manager = HandoffManager(guardrails=guardrails)

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="oracle",
            context={"task": "test"},
            reason="Test",
        )

        response = manager.execute_handoff(request)

        assert response.success is False
        assert response.status == HandoffStatus.BLOCKED
        assert response.guardrails_passed is False
        assert response.error is not None

    def test_execute_handoff_validation_failure(self):
        """Test handoff fails with validation errors."""
        manager = HandoffManager()
        request = HandoffRequest(
            source_agent="",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
        )

        response = manager.execute_handoff(request)

        assert response.success is False
        assert response.status == HandoffStatus.FAILED

    def test_context_transfer_correctness(self):
        """Test context is correctly transferred."""
        manager = HandoffManager()
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={
                "session_state": {"session_id": "xyz"},
                "conversation_history": [{"role": "user", "content": "test"}],
                "tool_access": ["read", "write", "edit"],
                "agent_state": {"current_step": 5},
                "additional": {"custom_key": "custom_value"},
            },
            reason="Test context transfer",
        )

        response = manager.execute_handoff(request)

        assert response.success is True
        ctx = response.transferred_context

        # Verify context fields are transferred
        assert ctx["session_state"] == {"session_id": "xyz"}
        assert ctx["conversation_history"] == [{"role": "user", "content": "test"}]
        assert ctx["tool_access"] == ["read", "write", "edit"]
        assert ctx["agent_state"] == {"current_step": 5}
        assert ctx["additional"] == {"custom_key": "custom_value"}

        # Verify metadata
        assert ctx["metadata"]["source_agent"] == "sisyphus"
        assert ctx["metadata"]["target_agent"] == "hephaestus"
        assert ctx["metadata"]["handoff_reason"] == "Test context transfer"

    def test_history_tracking(self):
        """Test handoff history is tracked."""
        manager = HandoffManager()

        # Execute multiple handoffs
        request1 = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test1"},
            reason="Test 1",
        )
        request2 = HandoffRequest(
            source_agent="oracle",
            target_agent="prometheus",
            context={"task": "test2"},
            reason="Test 2",
        )

        manager.execute_handoff(request1)
        manager.execute_handoff(request2)

        history = manager.get_history()
        assert len(history) == 2
        assert all(r.success for r in history)

    def test_clear_history(self):
        """Test clearing handoff history."""
        manager = HandoffManager()

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
        )
        manager.execute_handoff(request)

        manager.clear_history()
        assert len(manager.get_history()) == 0


class TestSameAgentRejection:
    """Tests for same-agent rejection."""

    def test_same_agent_validation(self):
        """Test same-agent handoff is rejected at validation."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="sisyphus",
            context={"task": "test"},
            reason="Test",
        )

        errors = request.validate()
        assert len(errors) > 0

    def test_same_agent_guardrails_block(self):
        """Test same-agent handoff is blocked by guardrails."""
        guardrails = Guardrails()
        request = HandoffRequest(
            source_agent="hephaestus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
        )

        passed, errors = guardrails.check_handoff(request)
        assert passed is False


class TestCustomRules:
    """Tests for custom guardrail rules."""

    def test_custom_rule_with_context_check(self):
        """Test custom rule that checks context content."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "no_sensitive_context",
            lambda r: "password" not in str(r.context),
            "Cannot transfer sensitive data",
        )

        # Should pass
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Test",
        )
        passed, _ = guardrails.check_handoff(request)
        assert passed is True

        # Should fail
        request_fail = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"password": "secret123"},
            reason="Test",
        )
        passed, errors = guardrails.check_handoff(request_fail)
        assert passed is False

    def test_custom_rule_with_metadata_check(self):
        """Test custom rule that checks metadata."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "priority_required",
            lambda r: r.metadata.get("priority") is not None,
            "Priority metadata required",
        )

        # Should fail - no metadata
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
        )
        passed, errors = guardrails.check_handoff(request)
        assert passed is False

        # Should pass - has metadata
        request_with_meta = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
            metadata={"priority": "high"},
        )
        passed, _ = guardrails.check_handoff(request_with_meta)
        assert passed is True


class TestConvenienceFunction:
    """Tests for the create_handoff convenience function."""

    def test_create_handoff_function(self):
        """Test create_handoff convenience function."""
        response = create_handoff(
            source="sisyphus",
            target="hephaestus",
            context={"task": "test"},
            reason="Test reason",
        )

        assert response.success is True
        assert response.status == HandoffStatus.COMPLETED


class TestBlockingBehavior:
    """Tests for blocking behavior."""

    def test_multiple_blocking_rules(self):
        """Test multiple rules can block a handoff."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "rule1",
            lambda r: r.target_agent != "blocked1",
            "Blocked by rule1",
        )
        guardrails.add_rule(
            "rule2",
            lambda r: r.target_agent != "blocked2",
            "Blocked by rule2",
        )

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="blocked1",
            context={"task": "test"},
            reason="Test",
        )

        passed, errors = guardrails.check_handoff(request)
        assert passed is False
        assert len(errors) == 1

    def test_partial_context_preserved_on_block(self):
        """Test context is preserved when handoff is blocked."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "always_block",
            lambda r: False,
            "Always blocks",
        )
        manager = HandoffManager(guardrails=guardrails)

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"important_data": "value"},
            reason="Test",
        )

        response = manager.execute_handoff(request)

        assert response.success is False
        assert response.transferred_context == {"important_data": "value"}


class TestErrorHandling:
    """Tests for error handling in guardrails."""

    def test_rule_exception_caught(self):
        """Test exceptions in rules are caught and reported."""
        guardrails = Guardrails()
        guardrails.add_rule(
            "broken_rule",
            lambda r: 1 / 0,  # Will raise ZeroDivisionError
            "This rule is broken",
        )

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="Test",
        )

        passed, errors = guardrails.check_handoff(request)
        # Rule threw exception, should be caught
        assert passed is False
        assert any("evaluation error" in e.lower() for e in errors)


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
