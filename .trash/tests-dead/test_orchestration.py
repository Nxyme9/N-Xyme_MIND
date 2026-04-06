"""Tests for orchestration modules."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestOrchestrationImports:
    """Verify all orchestration modules import correctly."""

    def test_tool_registry_import(self):
        from src.orchestration.tool_registry import registry
        assert registry is not None

    def test_tool_factory_import(self):
        from src.orchestration.tool_factory import build_tool, ToolContext, ToolResult
        assert build_tool is not None
        assert ToolContext is not None
        assert ToolResult is not None

    def test_tool_errors_import(self):
        from src.orchestration.tool_errors import ToolError
        assert ToolError is not None

    def test_resilience_middleware_import(self):
        from src.orchestration.resilience_middleware import ResilienceMiddleware
        assert ResilienceMiddleware is not None

    def test_parallel_executor_import(self):
        from src.orchestration.parallel_executor import ParallelExecutor
        assert ParallelExecutor is not None

    def test_task_router_import(self):
        from src.orchestration.task_router import TaskRouter
        assert TaskRouter is not None

    def test_progress_import(self):
        from src.orchestration.progress import ProgressTracker
        assert ProgressTracker is not None

    def test_permissions_import(self):
        from src.orchestration.permissions import PermissionChecker
        assert PermissionChecker is not None

    def test_a2a_protocol_import(self):
        from src.orchestration.a2a_protocol import A2AProtocol
        assert A2AProtocol is not None

    def test_agent_card_registry_import(self):
        from src.orchestration.agent_card_registry import AgentCardRegistry
        assert AgentCardRegistry is not None


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_registry_list_tools(self):
        from src.orchestration.tool_registry import registry
        tools = registry.get_tool_list()
        assert isinstance(tools, list)

    def test_registry_get_nonexistent(self):
        from src.orchestration.tool_registry import registry
        result = registry.get("nonexistent_tool")
        assert result is None


class TestToolContext:
    """Test ToolContext dataclass."""

    def test_tool_context_creation(self):
        from src.orchestration.tool_factory import ToolContext
        ctx = ToolContext(working_directory="/tmp")
        assert ctx.working_directory == "/tmp"


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_tool_result_success(self):
        from src.orchestration.tool_factory import ToolResult
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}

    def test_tool_result_error(self):
        from src.orchestration.tool_factory import ToolResult
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestResilienceMiddleware:
    """Test resilience middleware."""

    def test_middleware_creation(self):
        from src.orchestration.resilience_middleware import ResilienceMiddleware
        mw = ResilienceMiddleware()
        assert mw is not None


class TestParallelExecutor:
    """Test parallel executor."""

    def test_executor_creation(self):
        from src.orchestration.parallel_executor import ParallelExecutor
        executor = ParallelExecutor(max_concurrent=4)
        assert executor.max_concurrent == 4


class TestProgressTracker:
    """Test progress tracker."""

    def test_tracker_creation(self):
        from src.orchestration.progress import ProgressTracker
        tracker = ProgressTracker()
        assert tracker is not None
