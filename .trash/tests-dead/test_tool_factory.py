"""Tests for tool factory pattern."""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestration.tool_factory import (
    build_tool,
    ToolResult,
    ToolContext,
    TOOL_DEFAULTS,
)


class TestToolFactory:
    """Tests for @build_tool decorator."""

    def test_build_tool_requires_name(self):
        """Tool must have name attribute."""
        with pytest.raises(ValueError, match="must have 'name'"):

            @build_tool
            class NoNameTool:
                description = "test"
                input_schema = {}

    def test_build_tool_requires_description(self):
        """Tool must have description attribute."""
        with pytest.raises(ValueError, match="must have 'description'"):

            @build_tool
            class NoDescTool:
                name = "test"
                input_schema = {}

    def test_build_tool_requires_input_schema(self):
        """Tool must have input_schema attribute."""
        with pytest.raises(ValueError, match="must have 'input_schema'"):

            @build_tool
            class NoSchemaTool:
                name = "test"
                description = "test"

    def test_build_tool_adds_defaults(self):
        """Tool gets default methods."""

        @build_tool
        class MinimalTool:
            name = "minimal"
            description = "minimal tool"
            input_schema = {}

        tool = MinimalTool()
        assert tool.is_enabled() == True
        assert tool.is_concurrency_safe({}) == False
        assert tool.is_read_only({}) == False
        assert tool.is_destructive({}) == False

    def test_build_tool_wraps_execute(self):
        """Tool execute is wrapped with validation."""

        @build_tool
        class SimpleTool:
            name = "simple"
            description = "simple tool"
            input_schema = {}

            async def execute(self, input, context):
                return {"result": "ok"}

        tool = SimpleTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({}, ToolContext(working_directory="."))
        )
        assert result.success == True
        assert result.data == {"result": "ok"}

    def test_build_tool_validation_failure(self):
        """Tool returns error on validation failure."""

        @build_tool
        class FailingValidationTool:
            name = "failing_validation"
            description = "fails validation"
            input_schema = {}

            def validate_input(self, input, context):
                return {"result": False, "message": "Invalid input"}

            async def execute(self, input, context):
                return {"result": "should not reach here"}

        tool = FailingValidationTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({}, ToolContext(working_directory="."))
        )
        assert result.success == False
        assert "Invalid input" in result.error

    def test_build_tool_permission_denial(self):
        """Tool returns error on permission denial."""

        @build_tool
        class DeniedTool:
            name = "denied"
            description = "permission denied"
            input_schema = {}

            def check_permissions(self, input, context):
                return {"behavior": "deny", "message": "Not allowed"}

            async def execute(self, input, context):
                return {"result": "should not reach here"}

        tool = DeniedTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({}, ToolContext(working_directory="."))
        )
        assert result.success == False
        assert "Not allowed" in result.error

    def test_build_tool_exception_handling(self):
        """Tool catches exceptions and returns error."""

        @build_tool
        class ErrorTool:
            name = "error"
            description = "throws error"
            input_schema = {}

            async def execute(self, input, context):
                raise ValueError("Something went wrong")

        tool = ErrorTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({}, ToolContext(working_directory="."))
        )
        assert result.success == False
        assert "Something went wrong" in result.error
