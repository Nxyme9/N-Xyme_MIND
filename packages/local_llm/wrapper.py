#!/usr/bin/env python3
"""Local LLM Wrapper - Full tool execution pipeline.

Provides:
- execute_with_tools() - 2-pass: model → tools → results
- MCPToolExecutor - executes MCP tool calls
- normalize_tools() - converts MCP tool schemas to OpenAI format
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from packages.local_llm.ollama_client import LocalLLM, ChatResponse

logger = logging.getLogger("local_llm_wrapper")


# ============================================================================
# TOOL EXECUTOR
# ============================================================================


class MCPToolExecutor:
    """Execute MCP tools via JSON-RPC.

    In a real system, this would connect to MCP servers.
    For now, provides a registry for tool handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._mcp_servers: Dict[str, Any] = {}

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a tool handler.

        Args:
            name: Tool name
            handler: Async function(tool_args) -> result
        """
        self._handlers[name] = handler
        logger.info(f"Registered handler for tool: {name}")

    def register_mcp_server(self, name: str, server: Any) -> None:
        """Register an MCP server."""
        self._mcp_servers[name] = server
        logger.info(f"Registered MCP server: {name}")

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        if tool_name not in self._handlers:
            logger.warning(f"No handler for tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            handler = self._handlers[tool_name]
            result = await handler(arguments)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}

    def list_tools(self) -> List[str]:
        """List registered tool names."""
        return list(self._handlers.keys())


# ============================================================================
# BUILT-IN TOOLS (for testing)
# ============================================================================


async def tool_add(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add two numbers."""
    a = args.get("a", 0)
    b = args.get("b", 0)
    return {"result": a + b, "a": a, "b": b}


async def tool_search_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search memory (placeholder for now)."""
    query = args.get("query", "")
    # Would call unified-memory MCP in real implementation
    return {"matches": [f"Mock result for: {query}"], "count": 1, "query": query}


async def tool_get_time(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get current time."""
    from datetime import datetime

    return {
        "timestamp": datetime.now().isoformat(),
        "unix": int(datetime.now().timestamp()),
    }


# ============================================================================
# TOOL NORMALIZATION
# ============================================================================


def normalize_tool_schema(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize tool schemas to OpenAI format.

    Handles:
    - MCP format: {"name": "...", "description": "...", "parameters": {...}}
    - OpenAI format: {"type": "function", "function": {...}}
    - Already OpenAI format: passed through

    Args:
        tools: List of tool definitions in any format

    Returns:
        List of tools in OpenAI format
    """
    normalized = []

    for tool in tools:
        if not isinstance(tool, dict):
            continue

        # Already in OpenAI format: {"type": "function", "function": {...}}
        if tool.get("type") == "function" and "function" in tool:
            normalized.append(tool)
            continue

        # MCP format: {"name": "...", "description": "...", "parameters": {...}}
        if "name" in tool and "function" not in tool:
            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {"type": "object"}),
                    },
                }
            )
            continue

        # Has "function" key but not type - convert
        if "function" in tool:
            normalized.append({"type": "function", "function": tool["function"]})

    return normalized


# ============================================================================
# MAIN EXECUTE FUNCTION
# ============================================================================


class LocalLLMWrapper:
    """Full local LLM wrapper with tool execution.

    2-pass execution:
    1. Send message + tools to model → model decides tool call
    2. Execute tools → return results

    Returns pipeline-compatible format:
    - {"type": "tool_calls", "calls": [...], "executed": [...], "content": "..."}
    - {"type": "text", "content": "..."}
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        execute_mcp: bool = True,
    ):
        self.llm = LocalLLM(model=model, base_url=base_url, timeout=timeout)
        self.execute_mcp = execute_mcp

        # Tool executor
        self.executor = MCPToolExecutor()

        # Register built-in tools
        self._register_builtin_tools()

        logger.info(f"LocalLLMWrapper initialized: model={model}, mcp={execute_mcp}")

    def _register_builtin_tools(self):
        """Register built-in tools for testing."""
        self.executor.register_handler("add", tool_add)
        self.executor.register_handler("search_memories", tool_search_memory)
        self.executor.register_handler("get_time", tool_get_time)
        self.executor.register_handler("memory_search", tool_search_memory)

    async def execute_with_tools(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """Execute LLM with tools - full 2-pass pipeline.

        Args:
            messages: Chat history [{"role": "user", "content": "..."}]
            tools: Tool definitions (MCP or OpenAI format)
            **kwargs: Additional LLM parameters

        Returns:
            Pipeline-compatible result dict
        """
        # Normalize tools to OpenAI format
        normalized_tools = normalize_tool_schema(tools)

        logger.debug(
            f"execute_with_tools: {len(messages)} msgs, {len(normalized_tools)} tools"
        )

        # Pass 1: Call model with tools
        response = self.llm.chat_with_tools(
            messages=messages, tools=normalized_tools, **kwargs
        )

        # Handle text response (no tool call)
        if response.type == "text":
            return {"type": "text", "content": response.content or "No response"}

        # Handle tool calls
        if response.type == "tool_calls" and response.tool_calls:
            tool_calls = [
                {"name": tc.name, "arguments": tc.arguments}
                for tc in response.tool_calls
            ]

            # Execute MCP tools if enabled
            executed = []
            if self.execute_mcp:
                for tc in tool_calls:
                    tool_name = tc["name"]
                    args = tc["arguments"]

                    result = await self.executor.execute(tool_name, args)
                    executed.append(
                        {"tool": tool_name, "arguments": args, "result": result}
                    )
                    logger.info(f"Executed {tool_name}: {result}")

            # Format response with executed results
            return self._format_results(tool_calls, executed)

        # Fallback
        return {"type": "text", "content": "No tool called"}

    def _format_results(
        self, tool_calls: List[Dict], executed: List[Dict]
    ) -> Dict[str, Any]:
        """Format executed tool results into readable response.

        Args:
            tool_calls: Original tool calls from model
            executed: Executed tool results

        Returns:
            Pipeline-compatible result dict
        """
        if not executed:
            return {"type": "tool_calls", "calls": tool_calls}

        # Build readable response from results
        response_parts = []

        for exec_result in executed:
            tool_name = exec_result.get("tool", "unknown")
            result_data = exec_result.get("result", {})

            if isinstance(result_data, dict):
                if "error" in result_data:
                    response_parts.append(f"Error: {result_data['error']}")
                elif "result" in result_data:
                    # Numeric result
                    response_parts.append(f"Result: {result_data['result']}")
                elif "matches" in result_data:
                    matches = result_data.get("matches", [])
                    response_parts.append(f"Found {len(matches)}: {matches}")
                elif "timestamp" in result_data:
                    response_parts.append(f"Time: {result_data['timestamp']}")
                else:
                    # Generic dict - show keys
                    useful = {
                        k: v
                        for k, v in result_data.items()
                        if k not in ("success", "error")
                    }
                    if useful:
                        response_parts.append(str(useful))
            else:
                response_parts.append(str(result_data))

        final_content = " | ".join(response_parts) if response_parts else "Done"

        return {
            "type": "tool_calls",
            "calls": tool_calls,
            "executed": executed,
            "content": final_content,
        }

    def normalize_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Public method to normalize tools."""
        return normalize_tool_schema(tools)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================


async def execute_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str = "qwen2.5-coder:7b",
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function for one-shot tool execution.

    Args:
        messages: Chat history
        tools: Tool definitions
        model: Ollama model name
        **kwargs: Additional parameters

    Returns:
        Pipeline-compatible result dict
    """
    wrapper = LocalLLMWrapper(model=model)
    return await wrapper.execute_with_tools(messages, tools, **kwargs)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        wrapper = LocalLLMWrapper()

        # Test 1: Text response (no tool)
        print("=== Test 1: Text Response ===")
        result = await wrapper.execute_with_tools(
            [{"role": "user", "content": "Hello!"}], []
        )
        print(f"Result: {result}")

        # Test 2: Simple tool call
        print("\n=== Test 2: Tool Call (add) ===")
        tools = [
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
            }
        ]

        result = await wrapper.execute_with_tools(
            [{"role": "user", "content": "What is 5 + 3?"}], tools
        )
        print(f"Result: {json.dumps(result, indent=2)}")

        # Test 3: get_time tool
        print("\n=== Test 3: get_time tool ===")
        tools = [
            {
                "name": "get_time",
                "description": "Get current time",
                "parameters": {"type": "object"},
            }
        ]

        result = await wrapper.execute_with_tools(
            [{"role": "user", "content": "What time is it?"}], tools
        )
        print(f"Result: {json.dumps(result, indent=2)}")

    asyncio.run(test())
