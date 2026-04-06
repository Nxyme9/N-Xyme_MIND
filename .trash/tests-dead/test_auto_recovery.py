"""Unit tests for health.auto_recovery."""

import time
import pytest
from src.health.auto_recovery import (
    RecoveryTier,
    RecoveryAction,
    RecoveryState,
    AutoRecovery,
)


class TestRecoveryTier:
    def test_recovery_tier_values(self):
        assert RecoveryTier.TIER1_WAIT.value == "wait"
        assert RecoveryTier.TIER2_CLEAR_CACHE.value == "clear_cache"
        assert RecoveryTier.TIER3_RESTART.value == "restart"
        assert RecoveryTier.TIER4_DEGRADE.value == "degrade"


class TestRecoveryAction:
    def test_recovery_action_creation(self):
        action = RecoveryAction(
            tier=RecoveryTier.TIER1_WAIT, component="test_component", action="retry"
        )
        assert action.tier == RecoveryTier.TIER1_WAIT
        assert action.component == "test_component"
        assert action.action == "retry"
        assert action.success is False
        assert action.error is None

    def test_recovery_action_with_result(self):
        action = RecoveryAction(
            tier=RecoveryTier.TIER2_CLEAR_CACHE,
            component="cache",
            action="clear",
            success=True,
        )
        assert action.success is True


class TestRecoveryState:
    def test_recovery_state_creation(self):
        state = RecoveryState(component="test")
        assert state.component == "test"
        assert state.current_tier == RecoveryTier.TIER1_WAIT
        assert state.attempts == 0
        assert state.max_attempts == 4
        assert state.recovered is False

    def test_can_attempt_recovery_true_when_fresh(self):
        state = RecoveryState(component="test")
        assert state.can_attempt_recovery is True

    def test_can_attempt_recovery_false_at_max_attempts(self):
        state = RecoveryState(component="test")
        state.attempts = 4
        assert state.can_attempt_recovery is False

    def test_record_action_increments_attempts(self):
        state = RecoveryState(component="test")
        action = RecoveryAction(
            tier=RecoveryTier.TIER1_WAIT, component="test", action="retry"
        )
        state.record_action(action)
        assert state.attempts == 1

    def test_record_action_on_success_sets_recovered(self):
        state = RecoveryState(component="test")
        action = RecoveryAction(
            tier=RecoveryTier.TIER1_WAIT, component="test", action="retry", success=True
        )
        state.record_action(action)
        assert state.recovered is True


class TestAutoRecovery:
    def test_auto_recovery_init(self):
        recovery = AutoRecovery()
        assert recovery._recovery_states == {}
        assert recovery._recovery_handlers == {}

    def test_recovery_tiers_order(self):
        tiers = list(RecoveryTier)
        assert tiers[0] == RecoveryTier.TIER1_WAIT
        assert tiers[1] == RecoveryTier.TIER2_CLEAR_CACHE
        assert tiers[2] == RecoveryTier.TIER3_RESTART
        assert tiers[3] == RecoveryTier.TIER4_DEGRADE
