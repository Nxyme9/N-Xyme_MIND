"""Tests for tool registry."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestration.tool_registry import ToolRegistry
from src.orchestration.tool_factory import build_tool


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get(self):
        """Register and retrieve tool."""

        @build_tool
        class TestTool:
            name = "test"
            description = "test tool"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        registry = ToolRegistry()
        registry.register(TestTool)

        assert len(registry) == 1
        assert "test" in registry

        tool = registry.get("test")
        assert tool is not None
        assert tool.name == "test"

    def test_get_nonexistent(self):
        """Get nonexistent tool returns None."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_all_tools(self):
        """Get all tools."""

        @build_tool
        class Tool1:
            name = "tool1"
            description = "tool 1"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        @build_tool
        class Tool2:
            name = "tool2"
            description = "tool 2"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        registry = ToolRegistry()
        registry.register(Tool1)
        registry.register(Tool2)

        tools = registry.all()
        assert len(tools) == 2

    def test_search_tools(self):
        """Search tools by keyword."""

        @build_tool
        class SearchTool:
            name = "search_memories"
            description = "Search across memory sources"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        @build_tool
        class CreateTool:
            name = "create_memory"
            description = "Create a memory"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        registry = ToolRegistry()
        registry.register(SearchTool)
        registry.register(CreateTool)

        results = registry.search("search")
        assert len(results) == 1
        assert results[0].name == "search_memories"

    def test_get_tool_list(self):
        """Get tool list with metadata."""

        @build_tool
        class ReadOnlyTool:
            name = "read_only"
            description = "Read only tool"
            input_schema = {}

            def is_read_only(self, input):
                return True

            async def execute(self, input, context):
                return {}

        registry = ToolRegistry()
        registry.register(ReadOnlyTool)

        tool_list = registry.get_tool_list()
        assert len(tool_list) == 1
        assert tool_list[0]["name"] == "read_only"
        assert tool_list[0]["is_read_only"] == True

    def test_clear_registry(self):
        """Clear all tools."""

        @build_tool
        class TestTool:
            name = "test"
            description = "test"
            input_schema = {}

            async def execute(self, input, context):
                return {}

        registry = ToolRegistry()
        registry.register(TestTool)
        registry.clear()

        assert len(registry) == 0
