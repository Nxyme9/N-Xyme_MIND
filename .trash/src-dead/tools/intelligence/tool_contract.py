"""Tool Contract System — Formalized tool definitions.

Adapted from ant-source-code Tool.ts buildTool() factory pattern.
Provides typed contracts for tool definitions with validation hooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolDef:
    """Formalized tool definition with validation and permission hooks.

    Attributes:
        name: Tool name (unique identifier)
        description: Human-readable description
        is_read_only: Whether tool can modify state
        is_destructive: Whether tool can delete/destroy resources
        is_concurrency_safe: Whether tool can run concurrently
        validate_input: Optional input validation function
        check_permissions: Optional permission check function
        metadata: Additional tool metadata
    """

    name: str
    description: str = ""
    is_read_only: bool = False
    is_destructive: bool = False
    is_concurrency_safe: bool = False
    validate_input: Optional[Callable[[dict[str, Any]], tuple[bool, str]]] = None
    check_permissions: Optional[Callable[[dict[str, Any]], tuple[bool, str]]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, input_data: dict[str, Any]) -> tuple[bool, str]:
        """Validate input against tool contract.

        Args:
            input_data: Input data to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if self.validate_input:
            return self.validate_input(input_data)
        return True, "No validation defined"

    def check_perms(self, input_data: dict[str, Any]) -> tuple[bool, str]:
        """Check permissions for tool execution.

        Args:
            input_data: Input data to check

        Returns:
            Tuple of (is_allowed, message)
        """
        if self.check_permissions:
            return self.check_permissions(input_data)
        return True, "No permission check defined"

    def to_dict(self) -> dict[str, Any]:
        """Convert tool definition to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "is_read_only": self.is_read_only,
            "is_destructive": self.is_destructive,
            "is_concurrency_safe": self.is_concurrency_safe,
            "metadata": self.metadata,
        }


class ToolRegistry:
    """Registry of tool definitions with lookup and validation."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        """Register a tool definition.

        Args:
            tool: Tool definition to register
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDef]:
        """Get a tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDef]:
        """List all registered tools.

        Returns:
            List of tool definitions
        """
        return list(self._tools.values())

    def get_read_only_tools(self) -> list[ToolDef]:
        """Get all read-only tools.

        Returns:
            List of read-only tool definitions
        """
        return [t for t in self._tools.values() if t.is_read_only]

    def get_destructive_tools(self) -> list[ToolDef]:
        """Get all destructive tools.

        Returns:
            List of destructive tool definitions
        """
        return [t for t in self._tools.values() if t.is_destructive]


# Global registry
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry.

    Returns:
        Global tool registry instance
    """
    return _tool_registry


def register_tool(tool: ToolDef) -> None:
    """Register a tool in the global registry.

    Args:
        tool: Tool definition to register
    """
    _tool_registry.register(tool)
