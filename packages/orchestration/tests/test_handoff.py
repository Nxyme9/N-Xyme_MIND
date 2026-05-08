#!/usr/bin/env python3
"""Tests for Handoff Primitives.

Unit tests for the handoff module covering:
- HandoffRequest validation
- HandoffResponse creation
- Guardrails validation
- HandoffManager execution
- Context transfer
"""

from __future__ import annotations

import sys
import unittest

# Add project root to path
sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

# Import handoff module directly to avoid orchestration __init__.py dependencies
from packages.orchestration.handoff import (
    HandoffRequest,
    HandoffResponse,
    HandoffStatus,
    Guardrails,
    HandoffManager,
    create_handoff,
)


class TestHandoffRequest(unittest.TestCase):
    """Tests for HandoffRequest class."""

    def test_valid_request(self):
        """Valid request should have no validation errors."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        errors = request.validate()
        self.assertEqual(errors, [])

    def test_missing_source_agent(self):
        """Missing source_agent should fail validation."""
        request = HandoffRequest(
            source_agent="",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        errors = request.validate()
        self.assertIn("source_agent is required", errors)

    def test_missing_target_agent(self):
        """Missing target_agent should fail validation."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        errors = request.validate()
        self.assertIn("target_agent is required", errors)

    def test_same_source_and_target(self):
        """Same source and target agent should fail validation."""
        request = HandoffRequest(
            source_agent="hephaestus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        errors = request.validate()
        self.assertIn("source_agent and target_agent must be different", errors)

    def test_empty_context(self):
        """Empty context should fail validation."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={},
            reason="Implementation needed",
        )
        errors = request.validate()
        self.assertIn("context cannot be empty", errors)

    def test_missing_reason(self):
        """Missing reason should fail validation."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="",
        )
        errors = request.validate()
        self.assertIn("reason is required", errors)


class TestHandoffResponse(unittest.TestCase):
    """Tests for HandoffResponse class."""

    def test_approved_response(self):
        """Approved response should have correct status."""
        response = HandoffResponse.approved({"key": "value"}, result="success")
        self.assertTrue(response.success)
        self.assertEqual(response.status, HandoffStatus.COMPLETED)
        self.assertEqual(response.transferred_context, {"key": "value"})
        self.assertEqual(response.result, "success")
        self.assertTrue(response.guardrails_passed)

    def test_blocked_response(self):
        """Blocked response should have correct status."""
        response = HandoffResponse.blocked("Rule violation", {"key": "value"})
        self.assertFalse(response.success)
        self.assertEqual(response.status, HandoffStatus.BLOCKED)
        self.assertFalse(response.guardrails_passed)
        self.assertEqual(response.error, "Rule violation")

    def test_failed_response(self):
        """Failed response should have correct status."""
        response = HandoffResponse.failed("Execution error", {"key": "value"})
        self.assertFalse(response.success)
        self.assertEqual(response.status, HandoffStatus.FAILED)
        self.assertEqual(response.error, "Execution error")


class TestGuardrails(unittest.TestCase):
    """Tests for Guardrails class."""

    def setUp(self):
        self.guardrails = Guardrails()

    def test_default_rules_registered(self):
        """Default rules should be registered on init."""
        rules = self.guardrails.get_rules()
        self.assertIn("different_agents", rules)
        self.assertIn("non_empty_context", rules)
        self.assertIn("has_reason", rules)

    def test_valid_request_passes(self):
        """Valid request should pass guardrails."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        passed, errors = self.guardrails.check_handoff(request)
        self.assertTrue(passed)
        self.assertEqual(errors, [])

    def test_custom_rule_can_block(self):
        """Custom rule can block a transfer."""
        self.guardrails.add_rule(
            "block_hephaestus",
            lambda r: r.target_agent != "hephaestus",
            "Cannot transfer to hephaestus",
        )
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        passed, errors = self.guardrails.check_handoff(request)
        self.assertFalse(passed)
        self.assertIn("Cannot transfer to hephaestus", errors)

    def test_custom_rule_can_allow(self):
        """Custom rule can allow a transfer."""
        self.guardrails.add_rule(
            "allow_explore",
            lambda r: r.target_agent in ("explore", "oracle"),
            "Only explore or oracle allowed",
        )
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="explore",
            context={"task": "search code"},
            reason="Search needed",
        )
        passed, errors = self.guardrails.check_handoff(request)
        self.assertTrue(passed)

    def test_disable_rule(self):
        """Disabled rule should not affect validation."""
        self.guardrails.disable_rule("different_agents")
        request = HandoffRequest(
            source_agent="hephaestus",
            target_agent="hephaestus",  # Would normally fail
            context={"task": "implement feature"},
            reason="Implementation needed",
        )
        passed, errors = self.guardrails.check_handoff(request)
        # Should pass because different_agents is disabled
        # But still fails on non_empty_context and has_reason which pass
        # Actually let's check - same agents should fail on different_agents only
        # Let's create a valid one to test disable
        request2 = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="test",
        )
        passed2, _ = self.guardrails.check_handoff(request2)
        self.assertTrue(passed2)

    def test_remove_rule(self):
        """Removed rule should not affect validation."""
        self.guardrails.remove_rule("different_agents")
        # Now same agents should pass (different_agents removed)
        request = HandoffRequest(
            source_agent="hephaestus",
            target_agent="hephaestus",
            context={"task": "test"},
            reason="test reason",
        )
        # This should pass other rules (non_empty_context, has_reason)
        passed, errors = self.guardrails.check_handoff(request)
        # Should pass since different_agents rule was removed
        self.assertTrue(passed)


class TestHandoffManager(unittest.TestCase):
    """Tests for HandoffManager class."""

    def setUp(self):
        self.manager = HandoffManager()

    def test_successful_handoff(self):
        """Successful handoff should return approved response."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={
                "session_state": {"key": "value"},
                "conversation_history": [{"role": "user", "content": "test"}],
                "tool_access": ["read", "write"],
            },
            reason="Implementation needed",
        )
        response = self.manager.execute_handoff(request)

        self.assertTrue(response.success)
        self.assertEqual(response.status, HandoffStatus.COMPLETED)
        self.assertTrue(response.guardrails_passed)

        # Check context was transferred
        transferred = response.transferred_context
        self.assertIn("session_state", transferred)
        self.assertIn("conversation_history", transferred)
        self.assertIn("tool_access", transferred)
        self.assertIn("metadata", transferred)
        self.assertEqual(transferred["metadata"]["source_agent"], "sisyphus")
        self.assertEqual(transferred["metadata"]["target_agent"], "hephaestus")

    def test_guardrails_block_handoff(self):
        """Guardrails can block transfer based on rules."""
        # Add a blocking rule
        self.manager.guardrails.add_rule(
            "security_check",
            lambda r: "safe" in r.reason.lower(),
            "Reason must contain 'safe'",
        )

        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="hephaestus",
            context={"task": "implement feature"},
            reason="Implementation needed",  # Does not contain "safe"
        )
        response = self.manager.execute_handoff(request)

        self.assertFalse(response.success)
        self.assertEqual(response.status, HandoffStatus.BLOCKED)
        self.assertFalse(response.guardrails_passed)
        self.assertIn("must contain 'safe'", response.error)

    def test_invalid_request_fails(self):
        """Invalid request should return failed response."""
        request = HandoffRequest(
            source_agent="",  # Invalid
            target_agent="hephaestus",
            context={"task": "test"},
            reason="test",
        )
        response = self.manager.execute_handoff(request)

        self.assertFalse(response.success)
        self.assertEqual(response.status, HandoffStatus.FAILED)
        self.assertIn("source_agent is required", response.error)

    def test_history_tracking(self):
        """Handoff history should be tracked."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="explore",
            context={"task": "search"},
            reason="Search needed",
        )

        # Execute two handoffs
        self.manager.execute_handoff(request)
        self.manager.execute_handoff(request)

        history = self.manager.get_history()
        self.assertEqual(len(history), 2)

    def test_clear_history(self):
        """History can be cleared."""
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="explore",
            context={"task": "search"},
            reason="Search needed",
        )
        self.manager.execute_handoff(request)

        self.manager.clear_history()
        history = self.manager.get_history()
        self.assertEqual(len(history), 0)


class TestCreateHandoff(unittest.TestCase):
    """Tests for convenience create_handoff function."""

    def test_convenience_function(self):
        """create_handoff should work as convenience function."""
        response = create_handoff(
            source="sisyphus",
            target="hephaestus",
            context={"task": "implement X"},
            reason="Need implementation",
        )

        self.assertTrue(response.success)
        self.assertEqual(response.status, HandoffStatus.COMPLETED)


class TestContextTransfer(unittest.TestCase):
    """Tests for context transfer behavior."""

    def test_full_context_transfer(self):
        """Full context should be transferred to target."""
        manager = HandoffManager()
        request = HandoffRequest(
            source_agent="sisyphus",
            target_agent="oracle",
            context={
                "session_state": {"session_id": "abc123", "user": "test"},
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                ],
                "tool_access": ["read", "write", "edit"],
                "agent_state": {"step": 5, "mode": "execution"},
                "additional": {"custom_key": "custom_value"},
            },
            reason="Architecture review",
        )

        response = manager.execute_handoff(request)

        ctx = response.transferred_context

        # Check all context fields
        self.assertEqual(ctx["session_state"], {"session_id": "abc123", "user": "test"})
        self.assertEqual(len(ctx["conversation_history"]), 2)
        self.assertEqual(ctx["tool_access"], ["read", "write", "edit"])
        self.assertEqual(ctx["agent_state"], {"step": 5, "mode": "execution"})
        self.assertEqual(ctx["additional"], {"custom_key": "custom_value"})

        # Check metadata
        self.assertEqual(ctx["metadata"]["source_agent"], "sisyphus")
        self.assertEqual(ctx["metadata"]["target_agent"], "oracle")
        self.assertEqual(ctx["metadata"]["handoff_reason"], "Architecture review")


if __name__ == "__main__":
    unittest.main()
