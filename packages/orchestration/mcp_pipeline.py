"""MCP Pipeline Server — exposes UnifiedPipeline as MCP tools.

This MCP server exposes the orchestration pipeline to OpenCode with:
- execute_task: Execute a task through unified pipeline
- get_health: Health check for pipeline components
- get_stats: Pipeline execution statistics
- list_bmad_workflows: List available BMAD workflows
- run_bmad_workflow: Run a specific BMAD workflow

Usage:
    python -m packages.orchestration.mcp_pipeline --help

    # Or import directly:
    from packages.orchestration.mcp_pipeline import execute_task
    result = execute_task("hello", "speed")
    print(result)
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from typing import Any, Dict, List

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("N-Xyme Pipeline")

# ============================================================================
# Pipeline Singleton — Connection Pooling
# ============================================================================

# Module-level cache for pipeline instance (singleton pattern)
_pipeline_instance = None  # type: ignore[assignment]


def _get_pipeline(force_reload: bool = False):
    """Get unified pipeline instance (singleton with connection pooling).

    This function caches the pipeline instance to avoid recreating it on every
    call. The pipeline maintains internal state (connections, statistics, etc.)
    that should be reused across calls for efficiency.

    Args:
        force_reload: If True, force recreate the pipeline instance even if
                      a cached instance exists. Default False.

    Returns:
        UnifiedPipeline: Reused pipeline instance (or new if force_reload=True)

    Example:
        # Get cached instance
        pipeline = _get_pipeline()

        # Force reload (useful for testing or after configuration changes)
        pipeline = _get_pipeline(force_reload=True)
    """
    global _pipeline_instance

    if force_reload:
        # Cleanup existing instance before creating new one
        if _pipeline_instance is not None:
            _cleanup()

    if _pipeline_instance is None:
        from packages.orchestration.unified_pipeline import UnifiedPipeline

        _pipeline_instance = UnifiedPipeline()

    return _pipeline_instance


def _cleanup() -> None:
    """Cleanup pipeline resources for proper shutdown.

    This should be called during application shutdown or when the pipeline
    needs to be fully reset. It clears the cached instance and releases
    any held resources.
    """
    global _pipeline_instance

    if _pipeline_instance is not None:
        # Give the pipeline a chance to clean up resources
        if hasattr(_pipeline_instance, "cleanup"):
            try:
                _pipeline_instance.cleanup()
            except Exception as e:
                logger.warning(f"Pipeline cleanup warning: {e}")

        _pipeline_instance = None
        logger.debug("Pipeline instance cleaned up")


def _get_bmad_executor():
    """Get BMAD executor for workflow operations."""
    try:
        from packages.orchestration.bmad.executor import get_executor

        return get_executor()
    except ImportError:
        return None


# ============================================================================
# MCP Tools
# ============================================================================


@mcp.tool()
def execute_task(task: str, target: str = "success") -> Dict[str, Any]:
    """Execute a task through the unified pipeline.

    Args:
        task: Task description to execute
        target: Optimization target - "success", "speed", or "cost"

    Returns:
        Dict with PipelineResult:
        - success: bool
        - user_input: str
        - intent_type: str
        - selected_agent: str
        - workflow_name: Optional[str]
        - workflow_confidence: float
        - pipeline_mode: str
        - stages: List[stage dicts]
        - injected_context_length: int
        - output: Dict
        - error: Optional[str]
        - total_duration_ms: int
    """
    try:
        pipeline = _get_pipeline()
        result = pipeline.execute(task, target)

        # Convert PipelineResult to dict
        return {
            "success": result.success,
            "user_input": result.user_input,
            "intent_type": result.intent_type.value,
            "selected_agent": result.selected_agent,
            "workflow_name": result.workflow_name,
            "workflow_confidence": result.workflow_confidence,
            "pipeline_mode": result.pipeline_mode,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "output": s.output,
                    "error": s.error,
                }
                for s in result.stages
            ],
            "injected_context_length": len(result.injected_context),
            "output": result.output,
            "error": result.error,
            "total_duration_ms": result.total_duration_ms,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@mcp.tool()
def get_health() -> Dict[str, Any]:
    """Get health status of pipeline components.

    Returns:
        Dict with:
        - status: "healthy" or "degraded"
        - components: Dict of component -> status
        - message: str
    """
    try:
        pipeline = _get_pipeline()
        health = pipeline.health_check()
        return health
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@mcp.tool()
def get_stats() -> Dict[str, Any]:
    """Get pipeline execution statistics.

    Returns:
        Dict with:
        - total_tasks_executed: int
        - success_rate: float (0.0-1.0)
        - average_latency_ms: int
        - stage_timing_breakdown: Dict
    """
    try:
        pipeline = _get_pipeline()
        stats = pipeline.get_stats()
        return {"status": "success", **stats}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@mcp.tool()
def list_bmad_workflows() -> List[Dict[str, Any]]:
    """List available BMAD workflows.

    Returns:
        List of workflow info dicts with name, description, tags
    """
    try:
        executor = _get_bmad_executor()
        if executor is None:
            return [
                {
                    "status": "error",
                    "error": "BMAD executor not available",
                }
            ]

        workflows = executor.list_workflows()
        registry = executor.get_registry()

        result = []
        for name in workflows:
            workflow_data = registry.get(name, {})
            if isinstance(workflow_data, dict):
                result.append(
                    {
                        "name": name,
                        "description": workflow_data.get("description", ""),
                        "tags": workflow_data.get("tags", []),
                    }
                )
            else:
                result.append({"name": name})

        return result
    except Exception as e:
        return [{"status": "error", "error": str(e)}]


@mcp.tool()
def run_bmad_workflow(workflow: str, input: str = "") -> Dict[str, Any]:
    """Run a specific BMAD workflow.

    Args:
        workflow: Workflow name to execute
        input: Optional input/context for the workflow

    Returns:
        Dict with workflow execution result
    """
    try:
        executor = _get_bmad_executor()
        if executor is None:
            return {
                "status": "error",
                "error": "BMAD executor not available",
            }

        # Load workflow first, then execute
        workflow_def = executor.load(workflow)
        if workflow_def is None:
            return {
                "status": "error",
                "error": f"Workflow '{workflow}' not found",
            }
        result = executor.execute(workflow_def, "create", {"input": input})

        return {
            "status": "success",
            "workflow": workflow,
            "result": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    """CLI entry point for direct execution OR MCP server mode."""
    # Check if running as MCP server (stdin/stdout for MCP protocol)
    import sys

    if not sys.stdin.isatty():
        # MCP server mode - run the FastMCP server
        # Disable banner to prevent stdout pollution (breaks MCP JSON-RPC)
        mcp.run(show_banner=False)
        return

    parser = argparse.ArgumentParser(
        description="MCP Pipeline Server for N-Xyme Orchestration",
        prog="python -m packages.orchestration.mcp_pipeline",
    )
    parser.add_argument("task", nargs="?", help="Task to execute (for direct mode)")
    parser.add_argument(
        "target",
        nargs="?",
        default="success",
        choices=["success", "speed", "cost"],
        help="Optimization target (default: success)",
    )

    args = parser.parse_args()

    def show_help():
        """Show extended help for MCP pipeline."""
        parser.print_help()
        print("\n---")
        print("MCP Tools available:")
        print("  execute_task(task, target) - Execute task through pipeline")
        print("  get_health() - Get pipeline health")
        print("  get_stats() - Get pipeline statistics")
        print("  list_bmad_workflows() - List BMAD workflows")
        print("  run_bmad_workflow(workflow, input) - Run BMAD workflow")
        print("\n---")
        print("As MCP server:")
        print("  Add to opencode.json:")
        print('  "mcpServers": {')
        print('    "pipeline": {')
        print('      "command": "python",')
        print('      "args": ["-m", "packages.orchestration.mcp_pipeline"]')
        print("    }")
        print("  }")

    # Show help if no args
    if len(sys.argv) == 1:
        show_help()
        return 0

    # Direct execution mode (not MCP)
    if args.task:
        result = execute_task(args.task, args.target)
        import json as json_mod

        print(json_mod.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    # No task - run as MCP server
    print("Starting MCP Pipeline server...", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
