"""Tools subpackage — Tool registry, factory, search, errors."""

from .registry import ToolRegistry, registry
from .factory import build_tool, ToolContext, ToolResult, PermissionBehavior
from .search import ToolSearcher, get_tool_searcher
from .errors import ToolError, ToolErrorCode, validation_error, permission_error, file_not_found, timeout_error, internal_error

__all__ = [
    "ToolRegistry",
    "registry",
    "build_tool",
    "ToolContext",
    "ToolResult",
    "PermissionBehavior",
    "ToolSearcher",
    "get_tool_searcher",
    "ToolError",
    "ToolErrorCode",
    "validation_error",
    "permission_error",
    "file_not_found",
    "timeout_error",
    "internal_error",
]