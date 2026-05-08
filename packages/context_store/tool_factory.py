"""
Tool Factory Pattern for N-Xyme_MIND
====================================
BuildTool factory implementation based on leaked Anthropic source code patterns.

Reference: /home/nxyme/Documentos/CODE/source_code/ant-source-code-main/Tool.ts

Features:
- build_tool() factory function for standardized tool creation
- Pydantic-based input/output schema validation
- Default implementations for common methods
- Description generation
- Permission checking and validation

Usage:
    from packages.nx_context_mcp.tool_factory import build_tool, Tool, ToolResult, ToolCallContext

    tool = build_tool({
        name: "my_tool",
        input_schema: MyInputModel,
        output_schema: MyOutputModel,
        call: async def(args, context): ...
    })
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar, Protocol, Awaitable
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Type variables for generic tool types
TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput")
TProgress = TypeVar("TProgress", default=dict[str, Any])


# =============================================================================
# Core Types
# =============================================================================


class ToolInputJSONSchema(BaseModel):
    """JSON Schema representation of tool input."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)


class ValidationResult:
    """Result of input validation."""

    def __init__(self, result: bool, message: str = "", error_code: int = 0):
        self.result = result
        self.message = message
        self.error_code = error_code

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(result=True)

    @classmethod
    def failure(cls, message: str, error_code: int = 1) -> "ValidationResult":
        return cls(result=False, message=message, error_code=error_code)

    def to_dict(self) -> dict[str, Any]:
        if self.result:
            return {"result": True}
        return {
            "result": False,
            "message": self.message,
            "error_code": self.error_code,
        }


class PermissionResult:
    """Result of permission check."""

    def __init__(
        self,
        behavior: str,  # "allow" | "deny" | "ask"
        updated_input: dict[str, Any] | None = None,
        message: str = "",
    ):
        self.behavior = behavior
        self.updated_input = updated_input
        self.message = message

    @classmethod
    def allow(cls, updated_input: dict[str, Any] | None = None) -> "PermissionResult":
        return cls(behavior="allow", updated_input=updated_input)

    @classmethod
    def deny(cls, message: str = "") -> "PermissionResult":
        return cls(behavior="deny", message=message)

    @classmethod
    def ask(cls) -> "PermissionResult":
        return cls(behavior="ask")

    def to_dict(self) -> dict[str, Any]:
        result = {"behavior": self.behavior}
        if self.updated_input:
            result["updatedInput"] = self.updated_input
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class ToolCallProgress(Generic[TProgress]):
    """Progress callback for tool execution."""

    tool_use_id: str
    data: TProgress


@dataclass
class ToolResult(Generic[TOutput]):
    """Result returned by tool execution."""

    data: TOutput
    new_messages: list[dict[str, Any]] = field(default_factory=list)
    context_modifier: Callable[["ToolCallContext"], "ToolCallContext"] | None = None
    mcp_meta: dict[str, Any] | None = None


class ToolUseContext(Protocol):
    """Protocol for tool execution context."""

    @property
    def mode(self) -> str:
        """Permission mode (default, allow, deny, etc.)."""
        ...

    @property
    def is_non_interactive(self) -> bool:
        """Whether running in non-interactive mode."""
        ...


@dataclass
class ToolCallContext:
    """Concrete implementation of tool call context."""

    mode: str = "default"
    additional_working_directories: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    always_allow_rules: dict[str, Any] = field(default_factory=dict)
    always_deny_rules: dict[str, Any] = field(default_factory=dict)
    always_ask_rules: dict[str, Any] = field(default_factory=dict)
    is_bypass_permissions_available: bool = False
    is_auto_mode_available: bool = False
    stripped_dangerous_rules: dict[str, Any] = field(default_factory=dict)
    should_avoid_permission_prompts: bool = False
    await_automated_checks_before_dialog: bool = False
    is_non_interactive: bool = False
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_use_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for permission checking."""
        return {
            "mode": self.mode,
            "additionalWorkingDirectories": self.additional_working_directories,
            "alwaysAllowRules": self.always_allow_rules,
            "alwaysDenyRules": self.always_deny_rules,
            "alwaysAskRules": self.always_ask_rules,
            "isBypassPermissionsModeAvailable": self.is_bypass_permissions_available,
            "isAutoModeAvailable": self.is_auto_mode_available,
            "strippedDangerousRules": self.stripped_dangerous_rules,
            "shouldAvoidPermissionPrompts": self.should_avoid_permission_prompts,
            "awaitAutomatedChecksBeforeDialog": self.await_automated_checks_before_dialog,
            "isNonInteractiveSession": self.is_non_interactive,
        }


# =============================================================================
# Progress Data Types
# =============================================================================


@dataclass
class ToolProgressData:
    """Base class for tool progress data."""

    type: str = "generic"


@dataclass
class BashProgress(ToolProgressData):
    """Bash tool progress."""

    type: str = "bash"
    command: str = ""
    output: str = ""
    exit_code: int = 0


@dataclass
class MCPProgress(ToolProgressData):
    """MCP tool progress."""

    type: str = "mcp"
    server: str = ""
    tool: str = ""
    status: str = ""


@dataclass
class WebSearchProgress(ToolProgressData):
    """Web search progress."""

    type: str = "web_search"
    query: str = ""
    results_count: int = 0


# =============================================================================
# Tool Definition Types
# =============================================================================


# Type for tool call function
ToolCallFn = Callable[
    [Any, ToolCallContext],
    Awaitable[ToolResult[Any]],
]

# Type for description function
DescriptionFn = Callable[
    [Any, dict[str, Any]],
    Awaitable[str],
]

# Type for validation function
ValidateInputFn = Callable[
    [Any, ToolCallContext],
    Awaitable[ValidationResult],
]

# Type for permission check function
CheckPermissionsFn = Callable[
    [Any, ToolCallContext],
    Awaitable[PermissionResult],
]

# Type for is_* functions
IsEnabledFn = Callable[[], bool]
IsConcurrencySafeFn = Callable[[Any], bool]
IsReadOnlyFn = Callable[[Any], bool]
IsDestructiveFn = Callable[[Any], bool]
IsSearchOrReadFn = Callable[[Any], dict[str, bool]]
IsOpenWorldFn = Callable[[Any], bool]
RequiresUserInteractionFn = Callable[[], bool]
InterruptBehaviorFn = Callable[[], str]


@dataclass
class ToolDefinition:
    """
    Tool definition accepted by build_tool().

    Same shape as Tool but with defaultable methods optional.
    build_tool() fills them in so callers always see a complete Tool.
    """

    # Required fields
    name: str
    input_schema: type[BaseModel]
    call: ToolCallFn

    # Optional fields
    output_schema: type[BaseModel] | None = None
    description: DescriptionFn | None = None
    aliases: list[str] | None = None
    search_hint: str | None = None
    input_json_schema: ToolInputJSONSchema | None = None

    # Defaultable methods (provided by build_tool if not specified)
    is_enabled: IsEnabledFn | None = None
    is_concurrency_safe: IsConcurrencySafeFn | None = None
    is_read_only: IsReadOnlyFn | None = None
    is_destructive: IsDestructiveFn | None = None
    check_permissions: CheckPermissionsFn | None = None
    validate_input: ValidateInputFn | None = None
    get_path: Callable[[Any], str] | None = None
    to_auto_classifier_input: Callable[[Any], str] | None = None
    user_facing_name: Callable[[dict[str, Any] | None], str] | None = None
    is_search_or_read_command: IsSearchOrReadFn | None = None
    is_open_world: IsOpenWorldFn | None = None
    requires_user_interaction: RequiresUserInteractionFn | None = None
    interrupt_behavior: InterruptBehaviorFn | None = None

    # Metadata
    is_mcp: bool = False
    is_lsp: bool = False
    should_defer: bool = False
    always_load: bool = False
    max_result_size_chars: int = 100000
    strict: bool = False
    mcp_info: dict[str, str] | None = None

    # UI rendering (optional)
    render_result: Callable[[Any], Any] | None = None
    get_tool_use_summary: Callable[[dict[str, Any] | None], str | None] | None = None
    get_activity_description: Callable[[dict[str, Any] | None], str | None] | None = (
        None
    )

    def to_json_schema(self) -> dict[str, Any]:
        """Convert input schema to JSON schema."""
        if self.input_json_schema:
            return self.input_json_schema.model_dump()

        # Generate from Pydantic model
        schema = self.input_schema.model_json_schema()
        return schema


@dataclass
class Tool:
    """
    Complete Tool object with all methods implemented.

    This is the output of build_tool() - all defaultable methods
    have safe defaults filled in.
    """

    # Required fields
    name: str
    input_schema: type[BaseModel]
    call: ToolCallFn

    # Implementation methods
    description: DescriptionFn
    is_enabled: IsEnabledFn
    is_concurrency_safe: IsConcurrencySafeFn
    is_read_only: IsReadOnlyFn
    is_destructive: IsDestructiveFn
    check_permissions: CheckPermissionsFn

    # Optional but guaranteed to be present
    validate_input: ValidateInputFn | None = None
    get_path: Callable[[Any], str] | None = None
    to_auto_classifier_input: Callable[[Any], str] | None = None
    user_facing_name: Callable[[dict[str, Any] | None], str] | None = None
    is_search_or_read_command: IsSearchOrReadFn | None = None
    is_open_world: IsOpenWorldFn | None = None
    requires_user_interaction: RequiresUserInteractionFn | None = None
    interrupt_behavior: InterruptBehaviorFn | None = None
    output_schema: type[BaseModel] | None = None

    # Metadata
    aliases: list[str] | None = None
    search_hint: str | None = None
    input_json_schema: ToolInputJSONSchema | None = None
    is_mcp: bool = False
    is_lsp: bool = False
    should_defer: bool = False
    always_load: bool = False
    max_result_size_chars: int = 100000
    strict: bool = False
    mcp_info: dict[str, str] | None = None

    # UI rendering
    render_result: Callable[[Any], Any] | None = None
    get_tool_use_summary: Callable[[dict[str, Any] | None], str | None] | None = None
    get_activity_description: Callable[[dict[str, Any] | None], str | None] | None = (
        None
    )


# =============================================================================
# Default Implementations (fail-closed where it matters)
# =============================================================================


def _default_is_enabled() -> bool:
    """Default: tool is enabled."""
    return True


def _default_is_concurrency_safe(_input: Any = None) -> bool:
    """Default: assume not safe for concurrent execution."""
    return False


def _default_is_read_only(_input: Any = None) -> bool:
    """Default: assume writes."""
    return False


def _default_is_destructive(_input: Any = None) -> bool:
    """Default: not destructive."""
    return False


def _default_check_permissions(
    _input: dict[str, Any],
    _ctx: ToolCallContext | None = None,
) -> Awaitable[PermissionResult]:
    """Default: defer to general permission system."""
    return Awaitable(lambda: PermissionResult.allow())


def _default_to_auto_classifier_input(_input: Any = None) -> str:
    """Default: skip classifier - security-relevant tools must override."""
    return ""


def _default_user_facing_name(_input: dict[str, Any] | None = None) -> str:
    """Default: use tool name."""
    return ""


async def _default_description(
    input_dict: Any,
    options: dict[str, Any],
) -> str:
    """Default description generator."""
    return f"Execute {options.get('name', 'tool')}"


# =============================================================================
# build_tool() Factory
# =============================================================================


def build_tool(definition: ToolDefinition) -> Tool:
    """
    Build a complete Tool from a partial definition.

    Fills in safe defaults for commonly-stubbed methods. All tool exports
    should go through this so that defaults live in one place and callers
    never need `?.() ?? default`.

    Defaults (fail-closed where it matters):
    - is_enabled → True
    - is_concurrency_safe → False (assume not safe)
    - is_read_only → False (assume writes)
    - is_destructive → False
    - check_permissions → allow (defer to general permission system)
    - to_auto_classifier_input → '' (skip classifier)
    - user_facing_name → name
    - description → default generator

    Args:
        def: Tool definition with required and optional fields

    Returns:
        Complete Tool with all defaultable methods implemented

    Example:
        tool = build_tool(ToolDefinition(
            name="read_file",
            input_schema=ReadFileInput,
            call=async def(args, context):
                return ToolResult(data=read_file(args.path))
        ))
    """
    # Generate description if not provided
    description_fn = definition.description
    if description_fn is None:

        async def generated_description(
            input_dict: Any,
            options: dict[str, Any],
        ) -> str:
            # Try to generate from input schema
            schema = definition.input_schema.model_json_schema()
            props = schema.get("properties", {})
            prop_names = ", ".join(props.keys()) if props else "args"
            return f"{definition.name}({prop_names})"

        description_fn = generated_description

    # Build complete tool
    tool = Tool(
        # Required
        name=definition.name,
        input_schema=definition.input_schema,
        call=definition.call,
        # Generated/implemented methods
        description=description_fn,
        is_enabled=definition.is_enabled or _default_is_enabled,
        is_concurrency_safe=definition.is_concurrency_safe
        or _default_is_concurrency_safe,
        is_read_only=definition.is_read_only or _default_is_read_only,
        is_destructive=definition.is_destructive or _default_is_destructive,
        check_permissions=definition.check_permissions or _default_check_permissions,
        # Optional but filled
        validate_input=definition.validate_input,
        get_path=definition.get_path,
        to_auto_classifier_input=definition.to_auto_classifier_input
        or _default_to_auto_classifier_input,
        user_facing_name=definition.user_facing_name,
        is_search_or_read_command=definition.is_search_or_read_command,
        is_open_world=definition.is_open_world,
        requires_user_interaction=definition.requires_user_interaction,
        interrupt_behavior=definition.interrupt_behavior,
        output_schema=definition.output_schema,
        # Metadata
        aliases=definition.aliases,
        search_hint=definition.search_hint,
        input_json_schema=definition.input_json_schema,
        is_mcp=definition.is_mcp,
        is_lsp=definition.is_lsp,
        should_defer=definition.should_defer,
        always_load=definition.always_load,
        max_result_size_chars=definition.max_result_size_chars,
        strict=definition.strict,
        mcp_info=definition.mcp_info,
        # UI rendering
        render_result=definition.render_result,
        get_tool_use_summary=definition.get_tool_use_summary,
        get_activity_description=definition.get_activity_description,
    )

    return tool


# =============================================================================
# Helper Functions
# =============================================================================


def tool_matches_name(tool: Tool | dict[str, Any], name: str) -> bool:
    """
    Check if a tool matches the given name (primary name or alias).

    Args:
        tool: Tool object or dict with name/aliases
        name: Name to check

    Returns:
        True if name matches tool name or any alias
    """
    tool_name = tool.get("name") if isinstance(tool, dict) else tool.name
    tool_aliases = tool.get("aliases") if isinstance(tool, dict) else tool.aliases

    if tool_name == name:
        return True

    if tool_aliases and name in tool_aliases:
        return True

    return False


def find_tool_by_name(tools: list[Tool], name: str) -> Tool | None:
    """
    Find a tool by name or alias from a list of tools.

    Args:
        tools: List of Tool objects
        name: Name to search for

    Returns:
        Matching Tool or None
    """
    for tool in tools:
        if tool_matches_name(tool, name):
            return tool
    return None


def validate_tool_input(
    tool: Tool,
    input_data: dict[str, Any],
) -> ValidationResult:
    """
    Validate input data against tool's input schema.

    Args:
        tool: Tool with input schema
        input_data: Input data to validate

    Returns:
        ValidationResult indicating success or failure
    """
    try:
        tool.input_schema(**input_data)
        return ValidationResult.success()
    except ValidationError as e:
        errors = e.errors()
        message = "; ".join(f"{err['loc']}: {err['msg']}" for err in errors)
        return ValidationResult.failure(message=message, error_code=1)


# =============================================================================
# Export
# =============================================================================

__all__ = [
    # Core types
    "Tool",
    "ToolDefinition",
    "ToolResult",
    "ToolCallContext",
    "ToolCallProgress",
    "ValidationResult",
    "PermissionResult",
    "ToolProgressData",
    "BashProgress",
    "MCPProgress",
    "WebSearchProgress",
    "ToolInputJSONSchema",
    # Factory
    "build_tool",
    # Helpers
    "tool_matches_name",
    "find_tool_by_name",
    "validate_tool_input",
]
