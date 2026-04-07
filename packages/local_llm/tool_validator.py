#!/usr/bin/env python3
"""Tool Validation Layer for Local LLM.

Provides:
- ValidationResult dataclass for validation outcomes
- ToolCallValidator class for thread-safe tool call validation
- Validates tool existence, required arguments, and argument types
"""

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of tool call validation.

    Attributes:
        is_valid: Whether the tool call is valid
        error_message: Error message if invalid, empty string if valid
        tool_name: Name of the tool being validated
    """

    is_valid: bool
    error_message: str
    tool_name: str


class ToolCallValidator:
    """Validates tool calls against available tool schemas.

    Thread-safe validator that checks:
    1. Tool exists in available tools
    2. Required arguments are present
    3. Argument types match the schema

    Tool schema format (OpenAI format):
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "...",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg_name": {"type": "string|integer|number|boolean|array|object"},
                    ...
                },
                "required": ["arg_name", ...]
            }
        }
    }
    """

    # Valid JSON schema types
    VALID_TYPES = {"string", "integer", "number", "boolean", "array", "object"}

    def __init__(self):
        self._lock = threading.Lock()

    def validate(
        self, tool_call: Dict[str, Any], available_tools: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Validate a tool call against available tools.

        Args:
            tool_call: Tool call to validate with keys:
                - name: str - tool name
                - arguments: dict - tool arguments
            available_tools: List of tool definitions in OpenAI format

        Returns:
            ValidationResult with validation status and error message
        """
        with self._lock:
            # Extract tool name
            tool_name = tool_call.get("name", "")
            if not tool_name:
                return ValidationResult(
                    is_valid=False,
                    error_message="Tool call missing 'name' field",
                    tool_name="",
                )

            # Extract arguments
            arguments = tool_call.get("arguments", {})
            if arguments is None:
                arguments = {}

            # Find matching tool schema
            tool_schema = self._find_tool_schema(tool_name, available_tools)
            if tool_schema is None:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Tool '{tool_name}' not found in available tools",
                    tool_name=tool_name,
                )

            # Validate required arguments
            required_args = tool_schema.get("required", [])
            missing_required = self._check_required_args(arguments, required_args)
            if missing_required:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument(s): {', '.join(missing_required)}",
                    tool_name=tool_name,
                )

            # Validate argument types
            type_errors = self._validate_argument_types(arguments, tool_schema)
            if type_errors:
                return ValidationResult(
                    is_valid=False,
                    error_message="; ".join(type_errors),
                    tool_name=tool_name,
                )

            return ValidationResult(
                is_valid=True,
                error_message="",
                tool_name=tool_name,
            )

    def _find_tool_schema(
        self, tool_name: str, available_tools: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find tool schema by name in available tools.

        Args:
            tool_name: Name of the tool to find
            available_tools: List of tool definitions

        Returns:
            Tool schema if found, None otherwise
        """
        for tool in available_tools:
            if not isinstance(tool, dict):
                continue

            # Handle OpenAI format: {"type": "function", "function": {...}}
            if tool.get("type") == "function" and "function" in tool:
                func_def = tool["function"]
                if func_def.get("name") == tool_name:
                    return func_def

            # Handle MCP format: {"name": "...", ...}
            if tool.get("name") == tool_name:
                return tool

        return None

    def _check_required_args(
        self, arguments: Dict[str, Any], required: List[str]
    ) -> List[str]:
        """Check for missing required arguments.

        Args:
            arguments: Provided arguments
            required: List of required argument names

        Returns:
            List of missing argument names
        """
        missing = []
        for arg_name in required:
            if arg_name not in arguments:
                missing.append(arg_name)
        return missing

    def _validate_argument_types(
        self, arguments: Dict[str, Any], tool_schema: Dict[str, Any]
    ) -> List[str]:
        """Validate argument types against schema.

        Args:
            arguments: Provided arguments
            tool_schema: Tool schema with parameters

        Returns:
            List of type error messages (empty if valid)
        """
        errors = []
        parameters = tool_schema.get("parameters", {})
        properties = parameters.get("properties", {})

        for arg_name, arg_value in arguments.items():
            if arg_name not in properties:
                # Unknown argument - skip type validation
                continue

            expected_type = properties[arg_name].get("type")
            if expected_type not in self.VALID_TYPES:
                # Unknown type - skip validation
                continue

            # Check type compatibility
            if not self._is_type_compatible(arg_value, expected_type):
                errors.append(
                    f"Argument '{arg_name}' expected {expected_type}, "
                    f"got {type(arg_value).__name__}"
                )

        return errors

    def _is_type_compatible(self, value: Any, expected_type: str) -> bool:
        """Check if value type is compatible with expected type.

        Args:
            value: Value to check
            expected_type: Expected JSON schema type

        Returns:
            True if compatible, False otherwise
        """
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)

        return True  # Unknown type - assume valid


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================


def validate_tool_call(
    tool_call: Dict[str, Any], available_tools: List[Dict[str, Any]]
) -> ValidationResult:
    """Convenience function for quick validation.

    Args:
        tool_call: Tool call to validate
        available_tools: Available tool definitions

    Returns:
        ValidationResult
    """
    validator = ToolCallValidator()
    return validator.validate(tool_call, available_tools)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import json

    # Sample tools
    sample_tools = [
        {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_memories",
                "description": "Search memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
        },
    ]

    validator = ToolCallValidator()

    # Test 1: Valid tool call
    print("=== Test 1: Valid tool call ===")
    result = validator.validate(
        {"name": "add", "arguments": {"a": 5, "b": 3}}, sample_tools
    )
    print(f"Valid: {result.is_valid}, Error: '{result.error_message}'")

    # Test 2: Unknown tool
    print("\n=== Test 2: Unknown tool ===")
    result = validator.validate({"name": "unknown_tool", "arguments": {}}, sample_tools)
    print(f"Valid: {result.is_valid}, Error: '{result.error_message}'")

    # Test 3: Missing required argument
    print("\n=== Test 3: Missing required argument ===")
    result = validator.validate({"name": "add", "arguments": {"a": 5}}, sample_tools)
    print(f"Valid: {result.is_valid}, Error: '{result.error_message}'")

    # Test 4: Wrong argument type
    print("\n=== Test 4: Wrong argument type ===")
    result = validator.validate(
        {"name": "add", "arguments": {"a": "five", "b": 3}}, sample_tools
    )
    print(f"Valid: {result.is_valid}, Error: '{result.error_message}'")

    # Test 5: Valid search_memories
    print("\n=== Test 5: Valid search_memories ===")
    result = validator.validate(
        {"name": "search_memories", "arguments": {"query": "test"}}, sample_tools
    )
    print(f"Valid: {result.is_valid}, Error: '{result.error_message}'")

    # Test 6: Thread safety test
    print("\n=== Test 6: Thread safety ===")
    import threading

    results = []

    def validate_in_thread():
        r = validator.validate(
            {"name": "add", "arguments": {"a": 1, "b": 2}}, sample_tools
        )
        results.append(r)

    threads = [threading.Thread(target=validate_in_thread) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    all_valid = all(r.is_valid for r in results)
    print(f"All 10 parallel validations passed: {all_valid}")
