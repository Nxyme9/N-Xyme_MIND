# n-xyme-core-mcp

Core MCP server for N-Xyme integration.

Provides the FastMCP instance for tool registration across memory, learning, and intelligence subsystems.

## Installation

```bash
uv sync --no-dev
```

## Usage

```bash
# Stdio mode (default)
uv run --package n-xyme-core-mcp core-mcp

# SSE mode
uv run --package n-xyme-core-mcp core-mcp sse localhost 8000
```

## Architecture

This package serves as the integration layer connecting:
- `n-xyme-memory-core` - Memory subsystem
- `n-xyme-learning-engine` - Learning/routing
- `n-xyme-intelligence` - Intelligence layer
- `nx-mind-mcp` - Project state management
