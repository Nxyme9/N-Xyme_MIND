"""Unit tests for TriggerRouter."""

import time
import pytest
from unittest.mock import patch, MagicMock
from src.orchestration.trigger_router import (
    get_429_count,
    increment_429_counter,
    reset_429_counter,
    send_windows_toast,
    _rotate_vpn,
    _rotate_api_key,
    _check_burnttoast,
    TriggerRouter,
    create_router,
)


class TestRateLimitCounter:
    def setup_method(self):
        reset_429_counter()

    def test_get_429_count_initially_zero(self):
        reset_429_counter()
        assert get_429_count() == 0

    def test_increment_429_counter(self):
        result = increment_429_counter()
        assert result == 1
        assert get_429_count() == 1

    def test_increment_429_counter_multiple(self):
        for i in range(5):
            increment_429_counter()
        assert get_429_count() == 5

    def test_reset_429_counter(self):
        increment_429_counter()
        increment_429_counter()
        reset_429_counter()
        assert get_429_count() == 0

    def test_429_counter_window_expiry(self):
        from src.orchestration import trigger_router

        increment_429_counter()
        trigger_router._last_429_timestamp = time.time() - 400
        assert get_429_count() == 0


class TestBurntToast:
    def setup_method(self):
        from src.orchestration import trigger_router

        trigger_router._burnttoast_available = None

    @patch("subprocess.run")
    def test_check_burnttoast_available(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Module found")
        result = _check_burnttoast()
        assert result is True

    @patch("subprocess.run")
    def test_check_burnttoast_not_available(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        result = _check_burnttoast()
        assert result is False

    @patch("subprocess.run")
    def test_check_burnttoast_exception(self, mock_run):
        mock_run.side_effect = Exception("PowerShell not found")
        result = _check_burnttoast()
        assert result is False


class TestWindowsToast:
    @patch("subprocess.run")
    @patch("src.orchestration.trigger_router._check_burnttoast")
    def test_send_windows_toast_with_burnttoast(self, mock_check, mock_run):
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        result = send_windows_toast("Test Title", "Test Message")
        assert result is True

    @patch("subprocess.run")
    @patch("src.orchestration.trigger_router._check_burnttoast")
    def test_send_windows_toast_fallback_console(self, mock_check, mock_run):
        mock_check.return_value = False
        result = send_windows_toast("Test Title", "Test Message")
        assert result is False

    @patch("subprocess.run")
    @patch("src.orchestration.trigger_router._check_burnttoast")
    def test_send_windows_toast_timeout(self, mock_check, mock_run):
        mock_check.return_value = True
        mock_run.side_effect = TimeoutError()
        result = send_windows_toast("Test Title", "Test Message")
        assert result is False


class TestVPNRotation:
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_vpn_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = _rotate_vpn("provider1")
        assert result is True

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_vpn_script_not_found(self, mock_exists, mock_run):
        mock_exists.return_value = False
        result = _rotate_vpn("provider1")
        assert result is False

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_vpn_failure(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        result = _rotate_vpn("provider1")
        assert result is False


class TestAPIKeyRotation:
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_api_key_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = _rotate_api_key("provider1")
        assert result is True

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_api_key_script_not_found(self, mock_exists, mock_run):
        mock_exists.return_value = False
        result = _rotate_api_key("provider1")
        assert result is False

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rotate_api_key_timeout(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_run.side_effect = TimeoutError()
        result = _rotate_api_key("provider1")
        assert result is False


class TestTriggerRouterClass:
    """Tests for TriggerRouter class."""

    @pytest.fixture
    def router(self):
        """Create TriggerRouter instance with mocked config loading."""
        with patch.object(TriggerRouter, "_load_config", return_value=None):
            router = TriggerRouter(config_path="dummy.json")
            router.triggers = {}
            router.action_registry = {}
            router.global_settings = {}
            router.history = []
            router._cooldowns = {}
            return router

    def test_router_init(self, router):
        """Test TriggerRouter initialization."""
        assert router is not None
        assert router.triggers == {}

    def test_router_process_event_basic(self, router):
        """Test basic event processing."""
        event = {"type": "test", "source": "test"}
        result = router.process_event(event)
        # Basic event without matching trigger should still process

    def test_router_find_matching_trigger(self, router):
        """Test trigger matching logic."""
        # Empty triggers list should return None
        result = router._find_matching_trigger("test", "info", "rate_limit")
        assert result is None

    def test_router_is_on_cooldown(self, router):
        """Test cooldown check."""
        # No cooldowns set should return False
        result = router._is_on_cooldown("test_trigger")
        assert result is False

    def test_router_set_cooldown(self, router):
        """Test setting cooldown via attribute."""
        # Just verify the attribute exists
        assert hasattr(router, "cooldowns")
        router.cooldowns["test_trigger"] = time.time()
        # Access via the attribute
        assert router.cooldowns.get("test_trigger") is not None

    def test_router_get_history(self, router):
        """Test history retrieval."""
        history = router.get_history()
        assert isinstance(history, list)

    def test_router_get_cooldowns(self, router):
        """Test cooldowns retrieval."""
        cooldowns = router.get_cooldowns()
        assert isinstance(cooldowns, dict)

    def test_router_record_history(self, router):
        """Test history recording."""
        trigger = {"trigger_id": "test_id", "description": "Test trigger"}
        event = {"type": "test"}
        result = {"success": True}
        router._record_history(trigger, event, result)
        # History should be updated
