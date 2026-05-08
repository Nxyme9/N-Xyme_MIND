"""BMAD workflow state management for nx-mind-mcp.

Handles tracking of BMAD workflow phases, steps, and completion status.
State is persisted to .sisyphus/bmad-phase-state.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("nx-mind-mcp.bmad")

# Default state file location
BMAD_STATE_FILE = ".sisyphus/bmad-phase-state.json"


class BmadWorkflowState:
    """Manages BMAD workflow state persistence."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_file = project_root / BMAD_STATE_FILE

    def _read_state(self) -> dict[str, Any]:
        """Read state from file, return empty dict if not exists."""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read BMAD state: {e}")
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        """Write state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to write BMAD state: {e}")
            raise

    def get_workflow_status(self, workflow_name: str) -> dict[str, Any]:
        """Get status of a specific workflow.

        Args:
            workflow_name: Name of the workflow (e.g., 'bmad-testarch-trace')

        Returns:
            Dict with workflow status: name, phase, step, completed, timestamp
        """
        state = self._read_state()
        workflows = state.get("workflows", {})
        workflow = workflows.get(workflow_name, {})

        if not workflow:
            return {
                "name": workflow_name,
                "exists": False,
                "phase": None,
                "step": None,
                "completed": False,
                "message": f"Workflow '{workflow_name}' not found",
            }

        return {
            "name": workflow_name,
            "exists": True,
            "phase": workflow.get("phase"),
            "step": workflow.get("step"),
            "completed": workflow.get("completed", False),
            "timestamp": workflow.get("timestamp"),
            "message": f"Workflow '{workflow_name}' found",
        }

    def list_workflows(self) -> dict[str, Any]:
        """List all available BMAD workflows with their phases.

        Scans _bmad/tea/workflows/ for workflow directories.

        Returns:
            Dict with list of workflows and their current status
        """
        bmad_path = self.project_root / "_bmad" / "tea" / "workflows"
        state = self._read_state()
        workflows_state = state.get("workflows", {})

        workflows = []

        if bmad_path.exists():
            for category in bmad_path.iterdir():
                if not category.is_dir():
                    continue
                for workflow_dir in category.iterdir():
                    if not workflow_dir.is_dir():
                        continue

                    workflow_name = workflow_dir.name
                    workflow_info = workflows_state.get(workflow_name, {})

                    # Check for workflow.yaml to verify it's a valid workflow
                    workflow_yaml = workflow_dir / "workflow.yaml"
                    if workflow_yaml.exists():
                        # Try to read name from yaml
                        name = workflow_name
                        try:
                            with open(workflow_yaml, "r") as f:
                                for line in f:
                                    if line.startswith("name:"):
                                        name = line.replace("name:", "").strip()
                                        break
                        except IOError:
                            pass

                        workflows.append(
                            {
                                "name": workflow_name,
                                "display_name": name,
                                "phase": workflow_info.get("phase"),
                                "step": workflow_info.get("step"),
                                "completed": workflow_info.get("completed", False),
                                "category": category.name,
                            }
                        )

        return {
            "workflows": sorted(workflows, key=lambda w: w["name"]),
            "count": len(workflows),
            "active_workflow": state.get("active_workflow"),
        }

    def get_current_phase(self) -> dict[str, Any]:
        """Get the currently active workflow and phase.

        Returns:
            Dict with active workflow name, phase, step, and status
        """
        state = self._read_state()
        active = state.get("active_workflow")

        if not active:
            return {
                "active": False,
                "workflow": None,
                "phase": None,
                "step": None,
                "message": "No active BMAD workflow",
            }

        workflow_state = state.get("workflows", {}).get(active, {})

        return {
            "active": True,
            "workflow": active,
            "phase": workflow_state.get("phase"),
            "step": workflow_state.get("step"),
            "completed": workflow_state.get("completed", False),
            "timestamp": workflow_state.get("timestamp"),
            "message": f"Active workflow: {active}",
        }

    def set_workflow_status(
        self,
        workflow_name: str,
        phase: Optional[str] = None,
        step: Optional[str] = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        """Set status for a specific workflow.

        Args:
            workflow_name: Name of the workflow
            phase: Current phase (e.g., 'create', 'edit', 'validate')
            step: Current step (e.g., 'step-01', 'step-02')
            completed: Whether workflow is completed

        Returns:
            Dict with status of the update
        """
        from datetime import datetime

        state = self._read_state()

        if "workflows" not in state:
            state["workflows"] = {}

        timestamp = datetime.utcnow().isoformat() + "Z"

        state["workflows"][workflow_name] = {
            "phase": phase,
            "step": step,
            "completed": completed,
            "timestamp": timestamp,
        }

        # Set as active if not completed
        if not completed:
            state["active_workflow"] = workflow_name

        self._write_state(state)

        return {
            "status": "ok",
            "workflow": workflow_name,
            "phase": phase,
            "step": step,
            "completed": completed,
            "message": f"Updated workflow '{workflow_name}' status",
        }


# Singleton instance storage
_bmad_state: Optional[BmadWorkflowState] = None


def get_bmad_state(project_root: Path) -> BmadWorkflowState:
    """Get or create BmadWorkflowState singleton."""
    global _bmad_state
    if _bmad_state is None:
        _bmad_state = BmadWorkflowState(project_root)
    return _bmad_state
