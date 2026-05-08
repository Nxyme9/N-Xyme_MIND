"""N-Xyme Delegate MCP Server — Reliable task delegation as MCP tools."""

# Suppress FastMCP banner - it prints to stdout and breaks JSON-RPC
import sys

_original_stdout = sys.stdout
_stdout_buffer = sys.stdout.buffer


class _QuietStdout:
    """stdout that silently discards writes but exposes .buffer for JSON-RPC"""

    def write(self, x):
        pass

    def flush(self):
        pass

    @property
    def buffer(self):
        return _stdout_buffer


sys.stdout = _QuietStdout()

from fastmcp import FastMCP

mcp = FastMCP("nx_delegate")


@mcp.tool()
def nx_delegate(task_description: str, context: dict = None) -> dict:
    """Delegate a task to the optimal agent using our routing system.

    Now auto-injects cross-session memory context BEFORE returning result.
    The 'injected_context' field contains memory from past sessions.
    """
    from packages.nx_delegate import nx_delegate as _delegate

    result = _delegate(task_description, context or {})

    # AUTO-INJECT: Get full context from brain and inject into result
    # This ensures memory context flows to the subagent's execution
    try:
        from packages.brain_mcp.namespaces.fingerprint import get_full_injected_context

        injected = get_full_injected_context(
            agent=result.get("agent", "hephaestus"),
            task=task_description,
            max_tokens=500,
        )

        # Add the injected context to result for OpenCode to use
        if injected.get("injected_context"):
            result["injected_context"] = injected.get("injected_context")
            result["memory_scope"] = injected.get("scope", "unknown")
            result["memory_tokens"] = injected.get("tokens_approx", 0)

    except Exception as e:
        result["injection_error"] = str(e)

    return result


@mcp.tool()
def nx_delegate_with_id(
    task_id: str, task_description: str, context: dict = None
) -> dict:
    """Delegate with explicit task ID for tracking."""
    from packages.nx_delegate import nx_delegate_with_id as _delegate

    return _delegate(task_id, task_description, context or {})


@mcp.tool()
def nx_delegate_record_outcome(
    task_id: str, success: bool, latency_ms: int = 0, tokens_used: int = 0
) -> dict:
    """Record delegation outcome for learning."""
    from packages.nx_delegate import nx_delegate_record_outcome as _record

    return _record(task_id, success, latency_ms, tokens_used)


@mcp.tool()
def health_check() -> dict:
    import time

    start = time.time()

    try:

        elapsed = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "message": "nx_delegate MCP operational",
            "modules": "loaded",
            "latency_ms": round(elapsed, 2),
        }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "status": "degraded",
            "message": f"nx_delegate MCP error: {str(e)[:100]}",
            "modules": "failed",
            "latency_ms": round(elapsed, 2),
        }


if __name__ == "__main__":
    # Pre-warm the router to avoid first-call timeout
    # The model loads once (~5s) and stays cached in memory
    print("Pre-warming delegation router...", file=sys.stderr)
    from packages.nx_delegate import nx_delegate as _delegate
    _delegate("warmup", {})  # First call loads model
    print("Router ready.", file=sys.stderr)
    
    mcp.run(transport="stdio")
