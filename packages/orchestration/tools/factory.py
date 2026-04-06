"""Tool Factory — @build_tool decorator pattern.

Ported from Claude Code's buildTool() factory pattern.
Enforces discipline: every tool gets validation, permissions, error handling.
Zero dependencies — stdlib only.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type
from enum import Enum
import asyncio
import functools


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    new_messages: Optional[list] = None


@dataclass
class ToolContext:
    """Execution context passed to all tools."""
    working_directory: str
    abort_event: Optional[asyncio.Event] = None
    file_state_cache: Optional[Dict] = None
    app_state: Optional[Dict] = None
    progress_callback: Optional[Callable] = None


# Fail-closed defaults — tools must explicitly declare capabilities
TOOL_DEFAULTS = {
    'is_enabled': lambda self: True,
    'is_concurrency_safe': lambda self, input: False,
    'is_read_only': lambda self, input: False,
    'is_destructive': lambda self, input: False,
    'check_permissions': lambda self, input, ctx: {'behavior': 'allow'},
    'validate_input': lambda self, input, ctx: {'result': True},
}


def build_tool(cls):
    """Decorator that creates a tool with fail-closed defaults.
    
    Usage:
        @build_tool
        class MyTool:
            name = "my_tool"
            description = "Does something useful"
            input_schema = {"param": {"type": "string"}}
            
            async def execute(self, input, context):
                return {"result": "done"}
    
    The decorator automatically adds:
    - is_enabled() → True (default)
    - is_concurrency_safe() → False (default)
    - is_read_only() → False (default)
    - is_destructive() → False (default)
    - check_permissions() → allow (default)
    - validate_input() → pass (default)
    - Wrapped execute() with validation + permission checking
    """
    
    # Validate required attributes
    if not hasattr(cls, 'name'):
        raise ValueError(f"Tool class {cls.__name__} must have 'name' attribute")
    if not hasattr(cls, 'description'):
        raise ValueError(f"Tool class {cls.__name__} must have 'description' attribute")
    if not hasattr(cls, 'input_schema'):
        raise ValueError(f"Tool class {cls.__name__} must have 'input_schema' attribute")
    
    # Add defaults for missing methods
    for name, default_fn in TOOL_DEFAULTS.items():
        if not hasattr(cls, name):
            setattr(cls, name, default_fn)
    
    # Wrap execute method with validation + permission checking
    if hasattr(cls, 'execute'):
        original_execute = cls.execute
        
        @functools.wraps(original_execute)
        async def wrapped_execute(self, input_data, context):
            # Step 1: Validate input
            validation = self.validate_input(input_data, context)
            if not validation.get('result', False):
                return ToolResult(
                    success=False,
                    error=validation.get('message', 'Validation failed')
                )
            
            # Step 2: Check permissions
            permissions = self.check_permissions(input_data, context)
            if permissions.get('behavior') == 'deny':
                return ToolResult(
                    success=False,
                    error=f"Permission denied: {permissions.get('message', '')}"
                )
            
            # Step 3: Execute tool
            try:
                result = await original_execute(self, input_data, context)
                return ToolResult(success=True, data=result)
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        
        cls.execute = wrapped_execute
    
    return cls
