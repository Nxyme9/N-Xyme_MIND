"""Tool Errors — Standardized error rendering for tools."""
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class ToolErrorCode(Enum):
    VALIDATION_FAILED = 1001
    PERMISSION_DENIED = 1002
    FILE_NOT_FOUND = 1003
    FILE_READ_ERROR = 1004
    FILE_WRITE_ERROR = 1005
    TIMEOUT = 1006
    RATE_LIMITED = 1007
    INTERNAL_ERROR = 1008
    INVALID_INPUT = 1009
    RESOURCE_BUSY = 1010


@dataclass
class ToolError:
    """Standardized tool error."""
    code: ToolErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = {
            "error": True,
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


# Pre-built error factories
def validation_error(message: str, details: Optional[Dict] = None) -> ToolError:
    return ToolError(ToolErrorCode.VALIDATION_FAILED, message, details)

def permission_error(message: str, suggestion: Optional[str] = None) -> ToolError:
    return ToolError(ToolErrorCode.PERMISSION_DENIED, message, suggestion=suggestion)

def file_not_found(path: str) -> ToolError:
    return ToolError(
        ToolErrorCode.FILE_NOT_FOUND,
        f"File not found: {path}",
        suggestion="Check the file path and try again."
    )

def timeout_error(operation: str, timeout_ms: int) -> ToolError:
    return ToolError(
        ToolErrorCode.TIMEOUT,
        f"Operation timed out: {operation}",
        details={"timeout_ms": timeout_ms},
        suggestion="Try again with a smaller input or increase timeout."
    )

def internal_error(message: str) -> ToolError:
    return ToolError(ToolErrorCode.INTERNAL_ERROR, message)