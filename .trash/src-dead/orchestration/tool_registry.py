"""Tool Registry — Central registry for all tools.

Ported from Claude Code's tool registration pattern.
Provides discovery, search, and metadata for all registered tools.
"""

from typing import Dict, List, Optional, Type, Any
from .tool_factory import ToolContext, ToolResult


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, tool_class: Type) -> None:
        """Register a tool class (instantiates it)."""
        tool = tool_class()
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Any]:
        """Get a tool by name."""
        return self._tools.get(name)

    def all(self) -> List[Any]:
        """Get all registered tools."""
        return list(self._tools.values())

    def search(self, query: str) -> List[Any]:
        """Search tools by keyword."""
        query_lower = query.lower()
        return [
            tool
            for tool in self._tools.values()
            if query_lower in tool.name.lower()
            or query_lower in getattr(tool, "description", "").lower()
        ]

    def get_tool_list(self) -> List[Dict]:
        """Get list of all tools with metadata."""
        return [
            {
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "input_schema": getattr(tool, "input_schema", {}),
                "is_read_only": tool.is_read_only({}),
                "is_concurrency_safe": tool.is_concurrency_safe({}),
                "is_destructive": tool.is_destructive({}),
            }
            for tool in self._tools.values()
        ]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Global registry instance
registry = ToolRegistry()
