"""
Tests for cancellation.py: CancellationToken, TaskState, TaskTracker.
"""

import unittest
from ..src.cancellation import CancellationToken, TaskState, TaskTracker


class TestTaskState(unittest.TestCase):
    """Tests for TaskState enum."""

    def test_enum_values(self):
        """Test that all expected TaskState values exist."""
        self.assertEqual(TaskState.IDLE.value, "idle")
        self.assertEqual(TaskState.RUNNING.value, "running")
        self.assertEqual(TaskState.CANCELLED.value, "cancelled")
        self.assertEqual(TaskState.COMPLETED.value, "completed")
        self.assertEqual(TaskState.ERROR.value, "error")

    def test_enum_members(self):
        """Test that TaskState has exactly 5 members."""
        self.assertEqual(len(TaskState), 5)

    def test_enum_from_value(self):
        """Test creating TaskState from string value."""
        self.assertEqual(TaskState("running"), TaskState.RUNNING)
        self.assertEqual(TaskState("cancelled"), TaskState.CANCELLED)


class TestCancellationToken(unittest.TestCase):
    """Tests for CancellationToken."""

    def test_initial_state_not_cancelled(self):
        """Test that new token is not cancelled."""
        token = CancellationToken()
        self.assertFalse(token.is_cancelled())

    def test_cancel_sets_flag(self):
        """Test that cancel() sets the cancelled flag."""
        token = CancellationToken()
        token.cancel()
        self.assertTrue(token.is_cancelled())

    def test_reset_clears_flag(self):
        """Test that reset() clears the cancelled flag."""
        token = CancellationToken()
        token.cancel()
        self.assertTrue(token.is_cancelled())
        token.reset()
        self.assertFalse(token.is_cancelled())

    def test_double_cancel(self):
        """Test that calling cancel() twice is safe."""
        token = CancellationToken()
        token.cancel()
        token.cancel()
        self.assertTrue(token.is_cancelled())

    def test_reset_without_cancel(self):
        """Test that reset() on non-cancelled token is safe."""
        token = CancellationToken()
        token.reset()
        self.assertFalse(token.is_cancelled())

    def test_multiple_resets(self):
        """Test multiple resets."""
        token = CancellationToken()
        token.cancel()
        token.reset()
        token.reset()
        self.assertFalse(token.is_cancelled())

    def test_cancel_after_reset(self):
        """Test cancel after reset works correctly."""
        token = CancellationToken()
        token.cancel()
        token.reset()
        token.cancel()
        self.assertTrue(token.is_cancelled())


class TestTaskTracker(unittest.TestCase):
    """Tests for TaskTracker."""

    def setUp(self):
        """Create a fresh TaskTracker for each test."""
        self.tracker = TaskTracker()

    def test_register_task_returns_token(self):
        """Test that register_task returns a CancellationToken."""
        token = self.tracker.register_task("task-1", "planner")
        self.assertIsInstance(token, CancellationToken)

    def test_register_task_initial_state_running(self):
        """Test that registered task starts in RUNNING state."""
        self.tracker.register_task("task-1", "planner")
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "running")

    def test_register_task_with_info(self):
        """Test registering a task with custom info."""
        info = {"priority": "high", "source": "api"}
        self.tracker.register_task("task-1", "planner", info=info)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["info"], info)

    def test_register_task_without_info(self):
        """Test registering a task without info defaults to empty dict."""
        self.tracker.register_task("task-1", "planner")
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["info"], {})

    def test_get_status_returns_correct_data(self):
        """Test get_status returns task_id, agent, state, info."""
        self.tracker.register_task("task-1", "oracle", {"key": "value"})
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["task_id"], "task-1")
        self.assertEqual(status["agent"], "oracle")
        self.assertEqual(status["state"], "running")
        self.assertEqual(status["info"], {"key": "value"})

    def test_get_status_nonexistent_task(self):
        """Test get_status returns None for non-existent task."""
        status = self.tracker.get_status("nonexistent")
        self.assertIsNone(status)

    def test_update_state(self):
        """Test updating task state."""
        self.tracker.register_task("task-1", "planner")
        self.tracker.update_state("task-1", TaskState.COMPLETED)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "completed")

    def test_update_state_to_error(self):
        """Test updating task state to ERROR."""
        self.tracker.register_task("task-1", "planner")
        self.tracker.update_state("task-1", TaskState.ERROR)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "error")

    def test_update_state_nonexistent_task(self):
        """Test updating state of non-existent task is safe (no error)."""
        self.tracker.update_state("nonexistent", TaskState.COMPLETED)

    def test_get_all_empty(self):
        """Test get_all returns empty list when no tasks."""
        tasks = self.tracker.get_all()
        self.assertEqual(tasks, [])

    def test_get_all_multiple_tasks(self):
        """Test get_all returns all registered tasks."""
        self.tracker.register_task("task-1", "planner")
        self.tracker.register_task("task-2", "oracle")
        self.tracker.register_task("task-3", "security")
        tasks = self.tracker.get_all()
        self.assertEqual(len(tasks), 3)
        task_ids = {t["task_id"] for t in tasks}
        self.assertEqual(task_ids, {"task-1", "task-2", "task-3"})

    def test_cancel_task(self):
        """Test cancelling a task."""
        token = self.tracker.register_task("task-1", "planner")
        result = self.tracker.cancel("task-1")
        self.assertTrue(result)
        self.assertTrue(token.is_cancelled())
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "cancelled")

    def test_cancel_nonexistent_task(self):
        """Test cancelling a non-existent task returns False."""
        result = self.tracker.cancel("nonexistent")
        self.assertFalse(result)

    def test_cancel_already_cancelled_task(self):
        """Test cancelling an already cancelled task."""
        self.tracker.register_task("task-1", "planner")
        self.tracker.cancel("task-1")
        result = self.tracker.cancel("task-1")
        self.assertTrue(result)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "cancelled")

    def test_token_isolation(self):
        """Test that each task gets its own cancellation token."""
        token1 = self.tracker.register_task("task-1", "planner")
        token2 = self.tracker.register_task("task-2", "oracle")
        token1.cancel()
        self.assertTrue(token1.is_cancelled())
        self.assertFalse(token2.is_cancelled())

    def test_state_transitions(self):
        """Test valid state transitions."""
        self.tracker.register_task("task-1", "planner")
        self.tracker.update_state("task-1", TaskState.COMPLETED)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "completed")
        self.tracker.update_state("task-1", TaskState.ERROR)
        status = self.tracker.get_status("task-1")
        assert status is not None
        self.assertEqual(status["state"], "error")


if __name__ == "__main__":
    unittest.main()
