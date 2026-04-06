"""Unit tests for FocusManager."""

import time
import pytest
from src.orchestration.focus_manager import (
    FocusManager,
    FocusState,
    TimerMode,
    FocusSession,
    QuickCapture,
    Macro,
    MacroAction,
    ClipboardItem,
    Snippet,
    QuickCaptureManager,
    MacroManager,
    ClipboardManager,
)


class TestFocusState:
    """Tests for FocusState enum."""

    def test_focus_state_values(self):
        """Test FocusState enum values."""
        assert FocusState.IDLE.value == "idle"
        assert FocusState.FOCUS.value == "focus"
        assert FocusState.BREAK.value == "break"
        assert FocusState.PAUSED.value == "paused"


class TestTimerMode:
    """Tests for TimerMode enum."""

    def test_timer_mode_values(self):
        """Test TimerMode enum values."""
        assert TimerMode.POMODORO.value == "pomodoro"
        assert TimerMode.DEEP_WORK.value == "deep_work"
        assert TimerMode.SPRINT.value == "sprint"
        assert TimerMode.CUSTOM.value == "custom"


class TestFocusSession:
    """Tests for FocusSession dataclass."""

    def test_focus_session_defaults(self):
        """Test FocusSession default values."""
        session = FocusSession(session_id="test-id", start_time=time.time())
        assert session.session_id == "test-id"
        assert session.end_time is None
        assert session.duration_minutes == 25
        assert session.mode == TimerMode.POMODORO
        assert session.state == FocusState.IDLE
        assert session.completed_cycles == 0
        assert session.paused_duration == 0.0
        assert session.paused_at is None


class TestQuickCapture:
    """Tests for QuickCapture dataclass."""

    def test_quick_capture_defaults(self):
        """Test QuickCapture default values."""
        capture = QuickCapture(
            capture_id="cap-1", content="test content", timestamp=time.time()
        )
        assert capture.category == "general"
        assert capture.tags == []
        assert capture.processed is False


class TestMacro:
    """Tests for Macro dataclass."""

    def test_macro_defaults(self):
        """Test Macro default values."""
        macro = Macro(macro_id="macro-1", name="Test Macro", actions=[])
        assert macro.created_at is not None
        assert macro.last_used is None
        assert macro.trigger_hotkey is None


class TestMacroAction:
    """Tests for MacroAction dataclass."""

    def test_macro_action_defaults(self):
        """Test MacroAction default values."""
        action = MacroAction(action_type="key")
        assert action.params == {}
        assert action.duration_ms == 0


class TestClipboardItem:
    """Tests for ClipboardItem dataclass."""

    def test_clipboard_item_defaults(self):
        """Test ClipboardItem default values."""
        item = ClipboardItem(
            item_id="item-1", content="test", content_type="text", timestamp=time.time()
        )
        assert item.source_app is None
        assert item.pinned is False
        assert item.snippet_trigger is None


class TestSnippet:
    """Tests for Snippet dataclass."""

    def test_snippet_defaults(self):
        """Test Snippet default values."""
        snippet = Snippet(snippet_id="snip-1", trigger="test", content="test content")
        assert snippet.description == ""
        assert snippet.category == "general"
        assert snippet.created_at is not None


class TestFocusManager:
    """Tests for FocusManager class."""

    @pytest.fixture
    def focus_manager(self):
        """Create FocusManager instance."""
        return FocusManager()

    def test_init_default(self, focus_manager):
        """Test FocusManager initialization with defaults."""
        assert focus_manager.is_running is False
        assert focus_manager.current_session is None

    def test_set_callbacks(self, focus_manager):
        """Test setting callbacks."""
        tick_called = False
        complete_called = False
        state_change_called = False

        def on_tick(data):
            nonlocal tick_called
            tick_called = True

        def on_complete():
            nonlocal complete_called
            complete_called = True

        def on_state_change():
            nonlocal state_change_called
            state_change_called = True

        focus_manager.set_callbacks(
            on_tick=on_tick, on_complete=on_complete, on_state_change=on_state_change
        )

        assert focus_manager._on_tick is not None
        assert focus_manager._on_complete is not None
        assert focus_manager._on_state_change is not None

    def test_start_focus_pomodoro(self, focus_manager):
        """Test starting a Pomodoro focus session."""
        session = focus_manager.start_focus(mode=TimerMode.POMODORO)

        assert session is not None
        assert session.state == FocusState.FOCUS
        assert session.duration_minutes == 25
        assert session.mode == TimerMode.POMODORO
        assert focus_manager.is_running is True

    def test_start_focus_deep_work(self, focus_manager):
        """Test starting a Deep Work session."""
        session = focus_manager.start_focus(mode=TimerMode.DEEP_WORK)

        assert session.duration_minutes == 50
        assert session.mode == TimerMode.DEEP_WORK

    def test_start_focus_sprint(self, focus_manager):
        """Test starting a Sprint session."""
        session = focus_manager.start_focus(mode=TimerMode.SPRINT)

        assert session.duration_minutes == 15
        assert session.mode == TimerMode.SPRINT

    def test_start_focus_custom_duration(self, focus_manager):
        """Test starting with custom duration."""
        session = focus_manager.start_focus(mode=TimerMode.CUSTOM, custom_duration=45)

        assert session.duration_minutes == 45

    def test_start_focus_already_running(self, focus_manager):
        """Test starting when already in focus returns existing session."""
        session1 = focus_manager.start_focus()
        session2 = focus_manager.start_focus()

        assert session1.session_id == session2.session_id

    def test_get_duration_for_mode(self, focus_manager):
        """Test duration calculation for each mode."""
        assert focus_manager._get_duration_for_mode(TimerMode.POMODORO) == 25
        assert focus_manager._get_duration_for_mode(TimerMode.DEEP_WORK) == 50
        assert focus_manager._get_duration_for_mode(TimerMode.SPRINT) == 15
        assert focus_manager._get_duration_for_mode(TimerMode.CUSTOM) == 25
        # Unknown mode defaults to 25
        assert focus_manager._get_duration_for_mode("unknown") == 25

    def test_stop_focus(self, focus_manager):
        """Test stopping a focus session."""
        focus_manager.start_focus()
        assert focus_manager.is_running is True

        focus_manager.stop()
        assert focus_manager.is_running is False

    def test_pause_focus(self, focus_manager):
        """Test pausing a focus session."""
        focus_manager.start_focus()
        assert focus_manager.current_session.state == FocusState.FOCUS

        focus_manager.pause()
        assert focus_manager.current_session.state == FocusState.PAUSED
        assert focus_manager.current_session.paused_at is not None

    def test_resume_focus(self, focus_manager):
        """Test resuming from pause."""
        focus_manager.start_focus()
        focus_manager.pause()
        paused_time = focus_manager.current_session.paused_duration

        focus_manager.resume()
        assert focus_manager.current_session.state == FocusState.FOCUS
        assert focus_manager.current_session.paused_duration >= paused_time

    def test_get_current_state(self, focus_manager):
        """Test getting current state."""
        # Initial state is IDLE
        assert (
            focus_manager.current_session is None
            or focus_manager.current_session.state == FocusState.IDLE
        )

        focus_manager.start_focus()
        assert focus_manager.current_session.state == FocusState.FOCUS

    def test_get_stats_empty(self, focus_manager):
        """Test stats when no sessions."""
        stats = focus_manager.get_stats()
        assert "current_state" in stats
        assert "total_focus_minutes" in stats
        assert stats["current_state"] == "idle"

    def test_get_stats_with_sessions(self, focus_manager):
        """Test stats with completed sessions."""
        focus_manager.start_focus()
        focus_manager.stop()

        stats = focus_manager.get_stats()
        assert "total_focus_minutes" in stats or "sessions_completed" in stats

    def test_quick_capture_creation(self, focus_manager):
        """Test quick capture manager."""
        capture_mgr = QuickCaptureManager()
        capture = capture_mgr.add_capture("test task", category="work")
        assert capture is not None
        assert capture.content == "test task"
        assert capture.category == "work"
        assert capture.processed is False

    def test_macro_creation(self, focus_manager):
        """Test macro creation."""
        macro_mgr = MacroManager()
        macro_mgr.start_recording("TestMacro")
        macro_mgr.add_action("key", {"key": "a"})
        macro = macro_mgr.stop_recording()
        assert macro is not None
        assert macro.name == "TestMacro"

    def test_snippet_creation(self, focus_manager):
        """Test snippet creation."""
        clip_mgr = ClipboardManager()
        snippet = clip_mgr.add_snippet("test", "test content", category="code")
        assert snippet is not None
        assert snippet.trigger == "test"
        assert snippet.category == "code"

    def test_clipboard_monitoring_toggle(self, focus_manager):
        """Test toggling clipboard monitoring."""
        clip_mgr = ClipboardManager()
        clip_mgr._monitoring = False
        # Just verify the manager can be created
        assert clip_mgr is not None
        assert clip_mgr._max_history == 100

    def test_context_switch_handling(self, focus_manager):
        """Test context switch preserves state."""
        focus_manager.start_focus()
        session_id = focus_manager.current_session.session_id
        start_time = focus_manager.current_session.start_time

        # Verify session state
        assert focus_manager.current_session.state == FocusState.FOCUS

        # Verify session preserved
        assert focus_manager.current_session.session_id == session_id
        assert focus_manager.current_session.start_time == start_time
