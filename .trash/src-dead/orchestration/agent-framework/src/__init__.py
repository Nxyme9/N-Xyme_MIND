"""Agent Framework & Permissions for N-Xyme CATALYST"""

from .agent_config import AgentConfig
from .permission_manager import PermissionManager
from .router import Router
from .communicator import Communicator
from .tool_registry import (
    ToolRegistry,
    RoundCapEnforcer,
    ToolExecutionError,
    ToolNotRegisteredError,
    OutputValidationError,
    RoundCapExceededError,
)

__all__ = [
    "AgentConfig",
    "PermissionManager",
    "Router",
    "Communicator",
    "ToolRegistry",
    "RoundCapEnforcer",
    "ToolExecutionError",
    "ToolNotRegisteredError",
    "OutputValidationError",
    "RoundCapExceededError",
]
__version__ = "1.1.0"
