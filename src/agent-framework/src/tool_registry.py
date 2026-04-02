"""Tool registry and round cap enforcement for agent framework.

Provides:
- ToolRegistry: Register, validate, and execute tools with allowlist enforcement
- RoundCapEnforcer: Cap reasoning rounds to prevent runaway agent loops
"""

import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    pass


class ToolNotRegisteredError(ToolExecutionError):
    """Raised when attempting to execute an unregistered tool."""

    pass


class OutputValidationError(ToolExecutionError):
    """Raised when tool output fails JSON validation."""

    pass


class RoundCapExceededError(Exception):
    """Raised when reasoning round cap is exceeded."""

    pass


@dataclass
class ToolDefinition:
    """Definition of a registered tool."""

    name: str
    description: str
    schema: Dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry for tool allowlist enforcement and execution.

    Only registered tools can be executed. All outputs are JSON-validated
    against the tool's declared schema.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        schema: Dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Register a tool with its schema and handler.

        Args:
            name: Unique tool identifier.
            description: Human-readable description of what the tool does.
            schema: JSON Schema defining expected output structure.
            handler: Callable that executes the tool logic.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            schema=schema,
            handler=handler,
        )

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """Execute a registered tool with the given parameters.

        Args:
            name: Name of the tool to execute.
            params: Parameters to pass to the tool handler.

        Returns:
            The tool's output after JSON validation.

        Raises:
            ToolNotRegisteredError: If the tool is not in the allowlist.
            OutputValidationError: If the output fails schema validation.
            ToolExecutionError: If the tool handler raises an exception.
        """
        if name not in self._tools:
            raise ToolNotRegisteredError(
                f"Tool '{name}' is not registered. "
                f"Available tools: {list(self._tools.keys())}"
            )

        tool_def = self._tools[name]

        try:
            output = tool_def.handler(**params)
        except TypeError as e:
            raise ToolExecutionError(f"Tool '{name}' received invalid parameters: {e}")
        except Exception as e:
            raise ToolExecutionError(f"Tool '{name}' execution failed: {e}")

        # Validate output against schema
        self.validate_output(name, output, tool_def.schema)

        return output

    def validate_output(
        self, tool_name: str, output: Any, schema: Dict[str, Any]
    ) -> None:
        """Validate tool output against its JSON schema.

        Args:
            tool_name: Name of the tool (for error messages).
            output: The output value to validate.
            schema: JSON Schema to validate against.

        Raises:
            OutputValidationError: If validation fails.
        """
        try:
            import jsonschema as js
        except ImportError:
            js = None

        if js is not None:
            try:
                js.validate(instance=output, schema=schema)
            except js.ValidationError as e:
                raise OutputValidationError(
                    f"Tool '{tool_name}' output failed validation: {e.message}"
                )
        else:
            # Fallback: basic type check if jsonschema not available
            expected_type = schema.get("type")
            if expected_type:
                type_map = {
                    "object": dict,
                    "array": list,
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                }
                expected = type_map.get(expected_type)
                if expected and not isinstance(output, expected):
                    raise OutputValidationError(
                        f"Tool '{tool_name}' output type mismatch: "
                        f"expected {expected_type}, got {type(output).__name__}"
                    )

    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools.

        Returns:
            List of dicts with tool name and description.
        """
        return [
            {"name": t.name, "description": t.description} for t in self._tools.values()
        ]

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the output schema for a registered tool.

        Args:
            name: Tool name.

        Returns:
            The tool's schema dict, or None if not found.
        """
        tool = self._tools.get(name)
        return tool.schema if tool else None

    def is_registered(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name.

        Returns:
            True if the tool exists in the registry.
        """
        return name in self._tools

    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the registry.

        Args:
            name: Tool name to remove.

        Returns:
            True if tool was removed, False if it didn't exist.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def __repr__(self):
        return f"<ToolRegistry tools={list(self._tools.keys())}>"


class RoundCapEnforcer:
    """Enforces a maximum number of reasoning rounds per task.

    Prevents runaway agent loops by capping the number of reasoning
    iterations. When the cap is reached, the agent must synthesize
    its current state into a final response.
    """

    def __init__(self, max_rounds: int = 6):
        """Initialize the round cap enforcer.

        Args:
            max_rounds: Maximum number of reasoning rounds allowed.
        """
        self.max_rounds = max_rounds
        self._current_round: int = 0

    def start_round(self) -> int:
        """Start a new reasoning round.

        Increments the round counter and returns the current round number.

        Returns:
            The current round number (1-indexed).

        Raises:
            RoundCapExceededError: If the round cap has been reached.
        """
        if self._current_round >= self.max_rounds:
            raise RoundCapExceededError(
                f"Round cap of {self.max_rounds} exceeded. "
                f"Current round: {self._current_round}. "
                f"Agent must synthesize final response."
            )

        self._current_round += 1
        return self._current_round

    def should_synthesize(self) -> bool:
        """Check if the agent should synthesize a final response.

        Returns:
            True if the round cap has been reached or exceeded.
        """
        return self._current_round >= self.max_rounds

    def get_remaining_rounds(self) -> int:
        """Get the number of remaining rounds.

        Returns:
            Number of rounds left before cap is hit.
        """
        return max(0, self.max_rounds - self._current_round)

    def get_current_round(self) -> int:
        """Get the current round number.

        Returns:
            Current round (0 if no rounds started yet).
        """
        return self._current_round

    def reset(self) -> None:
        """Reset the round counter for a new task."""
        self._current_round = 0

    def __repr__(self):
        return f"<RoundCapEnforcer round={self._current_round}/{self.max_rounds}>"
