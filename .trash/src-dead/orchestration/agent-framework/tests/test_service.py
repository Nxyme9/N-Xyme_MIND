"""
Tests for service.py: FastAPI service endpoints.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

import httpx


class MockAgentConfig:
    """Mock AgentConfig for testing."""

    def __init__(self, name="planner"):
        self._name = name
        self.config = {
            "name": name,
            "type": "planner",
            "capabilities": ["planning", "coordination"],
            "skills": [],
        }

    def get_name(self):
        return self._name


def get_client(app):
    """Create an httpx.AsyncClient with ASGI transport for testing."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


class TestServiceHealth(unittest.TestCase):
    """Tests for GET /health endpoint."""

    def test_health_returns_200(self):
        """Test that /health returns 200 with status ok."""
        with patch("src.service.Router"), patch("src.service.PermissionManager"):
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.get("/health")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["status"], "ok")

            asyncio.get_event_loop().run_until_complete(run())


class TestServiceStatus(unittest.TestCase):
    """Tests for GET /status endpoint."""

    def test_status_returns_list(self):
        """Test that /status returns a list of tasks."""
        with patch("src.service.Router"), patch("src.service.PermissionManager"):
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.get("/status")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertIsInstance(data, list)

            asyncio.get_event_loop().run_until_complete(run())


class TestServiceRoute(unittest.TestCase):
    """Tests for POST /route endpoint."""

    def test_route_returns_200(self):
        """Test that /route returns 200 with agent config."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertIn("name", data)

            asyncio.get_event_loop().run_until_complete(run())

    def test_route_returns_task_id_header(self):
        """Test that /route returns X-Task-Id header."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    self.assertIn("x-task-id", response.headers)
                    task_id = response.headers["x-task-id"]
                    self.assertTrue(len(task_id) > 0)

            asyncio.get_event_loop().run_until_complete(run())

    def test_route_with_context(self):
        """Test that /route accepts context parameter."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.post(
                        "/route",
                        json={
                            "task": "plan a project",
                            "context": {"priority": "high"},
                        },
                    )
                    self.assertEqual(response.status_code, 200)

            asyncio.get_event_loop().run_until_complete(run())

    def test_route_without_context(self):
        """Test that /route works without context."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    self.assertEqual(response.status_code, 200)

            asyncio.get_event_loop().run_until_complete(run())


class TestServiceTaskStatus(unittest.TestCase):
    """Tests for GET /tasks/{task_id} endpoint."""

    def test_get_task_status_returns_200(self):
        """Test that GET /tasks/{task_id} returns task status."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    # First create a task via /route
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    task_id = response.headers["x-task-id"]

                    # Then get its status
                    response = await client.get(f"/tasks/{task_id}")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["task_id"], task_id)
                    self.assertIn("state", data)
                    self.assertIn("agent", data)

            asyncio.get_event_loop().run_until_complete(run())

    def test_get_task_status_nonexistent(self):
        """Test that GET /tasks/{task_id} returns 404 for non-existent task."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.get("/tasks/nonexistent-task-id")
                    self.assertEqual(response.status_code, 404)
                    data = response.json()
                    self.assertEqual(data["detail"], "Task not found")

            asyncio.get_event_loop().run_until_complete(run())


class TestServiceCancel(unittest.TestCase):
    """Tests for POST /tasks/{task_id}/cancel endpoint."""

    def test_cancel_task_returns_200(self):
        """Test that POST /tasks/{task_id}/cancel cancels a task."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    # First create a task
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    task_id = response.headers["x-task-id"]

                    # Cancel it
                    response = await client.post(f"/tasks/{task_id}/cancel")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["task_id"], task_id)
                    self.assertEqual(data["status"], "CANCELLING")

            asyncio.get_event_loop().run_until_complete(run())

    def test_cancel_task_updates_state(self):
        """Test that cancelling a task updates its state."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    # Create a task
                    response = await client.post(
                        "/route", json={"task": "plan a project"}
                    )
                    task_id = response.headers["x-task-id"]

                    # Cancel it
                    await client.post(f"/tasks/{task_id}/cancel")

                    # Check state
                    response = await client.get(f"/tasks/{task_id}")
                    data = response.json()
                    self.assertEqual(data["state"], "cancelled")

            asyncio.get_event_loop().run_until_complete(run())

    def test_cancel_nonexistent_task(self):
        """Test that cancelling non-existent task returns 404."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    response = await client.post("/tasks/nonexistent-task-id/cancel")
                    self.assertEqual(response.status_code, 404)
                    data = response.json()
                    self.assertEqual(data["detail"], "Task not found")

            asyncio.get_event_loop().run_until_complete(run())


class TestServiceStatusAfterRoute(unittest.TestCase):
    """Tests for GET /status after routing tasks."""

    def test_status_shows_routed_tasks(self):
        """Test that /status shows tasks created via /route."""
        with (
            patch("src.service.Router") as mock_router_cls,
            patch("src.service.PermissionManager"),
        ):
            mock_router = MagicMock()
            mock_router.route_task.return_value = MockAgentConfig("planner")
            mock_router_cls.return_value = mock_router
            from src.orchestration.agent-framework.src.service import app

            async def run():
                async with get_client(app) as client:
                    # Create two tasks
                    await client.post("/route", json={"task": "task one"})
                    await client.post("/route", json={"task": "task two"})

                    # Check status
                    response = await client.get("/status")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertGreaterEqual(len(data), 2)

            asyncio.get_event_loop().run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
