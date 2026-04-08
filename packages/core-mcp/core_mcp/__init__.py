"""Core MCP server for N-Xyme integration."""

from fastmcp import FastMCP

mcp = FastMCP("n-xyme-core")

# Import domain modules to register tools on shared mcp instance
# (must be after mcp is defined to avoid circular import)
from core_mcp import nxmind  # noqa: F401
from core_mcp import memory  # noqa: F401
from core_mcp import learning  # noqa: F401
from core_mcp import intelligence  # noqa: F401


__all__ = [
    "mcp",
    "nxmind",
    "memory",
    "learning",
    "intelligence",
]
