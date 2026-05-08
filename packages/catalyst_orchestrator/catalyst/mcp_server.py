"""BMAD Workflow MCP Server — exposes BMAD workflows and Catalyst orchestration as MCP tools."""

from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

mcp = FastMCP("N-Xyme Catalyst")


@mcp.tool()
def orchestrate(
    user_input: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Orchestrate BMAD workflow based on user input.

    Analyzes user input, detects workflow triggers, and executes
    the appropriate BMAD workflow.

    Args:
        user_input: User's message or command
        context: Optional execution context

    Returns:
        Dict with state, workflow_triggered, execution_mode, and result
    """
    try:
        from packages.orchestration.catalyst import CatalystOrchestrator

        orchestrator = CatalystOrchestrator()
        result = orchestrator.orchestrate(user_input, context=context or {})

        return {
            "status": "success",
            "state": result.state.value,
            "execution_mode": result.execution_mode,
            "workflow_triggered": result.workflow_triggered,
            "agents_spawned": result.agents_spawned,
            "metadata": result.metadata,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def detect_state(user_input: str) -> Dict[str, Any]:
    """Detect user state (FLOW, FRICTION, or ADAPT) from input.

    Uses reaction time, message length, and explicit markers to
    determine if the user is in flow state or experiencing friction.

    Args:
        user_input: User's message

    Returns:
        Dict with state classification and details
    """
    try:
        from packages.orchestration.catalyst import CatalystOrchestrator

        orchestrator = CatalystOrchestrator()
        state = orchestrator.detect_state(user_input)

        return {
            "status": "success",
            "state": state.value,
            "user_input": user_input,
            "details": orchestrator.state_detector.get_state_details(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def list_workflows() -> Dict[str, Any]:
    """List all available BMAD workflows.

    Returns:
        Dict with workflow list grouped by module
    """
    try:
        from packages.orchestration.bmad.executor import BMADExecutor

        executor = BMADExecutor()
        workflows = executor.list_workflows()

        return {
            "status": "success",
            "workflows": workflows,
            "total": len(workflows),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def execute_workflow(
    workflow_name: str,
    phase: str = "create",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a BMAD workflow by name.

    Args:
        workflow_name: Name of the workflow (e.g., "bmad-catalyst-orchestration")
        phase: Phase to execute ("create", "edit", "validate")
        context: Optional execution context

    Returns:
        Dict with execution result
    """
    try:
        from packages.orchestration.bmad.executor import BMADExecutor

        executor = BMADExecutor()
        workflow = executor.load(workflow_name)

        if not workflow:
            return {"status": "error", "error": f"Workflow not found: {workflow_name}"}

        result = executor.execute(workflow, phase, context or {})

        return {
            "status": "success" if result.success else "error",
            "workflow_name": result.workflow_name,
            "phase": result.phase,
            "success": result.success,
            "steps_completed": result.steps_completed,
            "steps_failed": result.steps_failed,
            "output": result.output,
            "error": result.error,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def run_quality_gates(files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run quality gates on specified files.

    Executes type check, lint, format, and test gates.

    Args:
        files: Optional list of files to validate

    Returns:
        Dict with quality gate results
    """
    try:
        from packages.orchestration.catalyst import CatalystOrchestrator

        orchestrator = CatalystOrchestrator()
        metrics = orchestrator.run_quality_gates(files=files)

        return {
            "status": "success",
            "metrics": metrics.to_dict(),
            "overall_score": metrics.overall_score,
            "gates_passed": metrics.gates_passed,
            "gates_failed": metrics.gates_failed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def get_orchestrator_status() -> Dict[str, Any]:
    """Get current orchestrator status.

    Returns:
        Dict with state detector, workflows, and fractal delegation status
    """
    try:
        from packages.orchestration.catalyst import CatalystOrchestrator

        orchestrator = CatalystOrchestrator()
        status = orchestrator.get_status()

        return {
            "status": "success",
            "status_dict": status,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    mcp.run()
