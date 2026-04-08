"""Phase Gate System for BMAD Workflows.

Enforces the 5-phase progression:
    1. analysis
    2. plan-workflows
    3. solutioning
    4. implementation
    5. test-architecture

Usage:
    from packages.orchestration.bmad.phase_gate import PhaseGate

    gate = PhaseGate()
    if gate.can_enter_phase("my-workflow", "plan-workflows"):
        # Execute plan phase
        gate.complete_phase("my-workflow", "plan-workflows")
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Phase order - must match directory names in _bmad/bmm/workflows/
PHASES = [
    "analysis",
    "plan-workflows",
    "solutioning",
    "implementation",
    "test-architecture",
]

# Default state file location
DEFAULT_STATE_FILE = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.sisyphus/bmad-phase-state.json")


class PhaseGateError(Exception):
    """Base exception for PhaseGate errors."""

    pass


class InvalidPhaseError(PhaseGateError):
    """Raised when an invalid phase name is provided."""

    pass


class PhaseOrderError(PhaseGateError):
    """Raised when attempting to skip phases."""

    pass


class PhaseGate:
    """Phase gate system for BMAD workflow progression.

    Tracks which phases have been completed for each workflow
    and enforces the ordered progression through the 5 phases.
    """

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize the PhaseGate.

        Args:
            state_file: Path to the state file. Defaults to DEFAULT_STATE_FILE.
        """
        self.state_file = state_file or DEFAULT_STATE_FILE
        self._state: Dict[str, List[str]] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load state from the JSON file."""
        if not self.state_file.exists():
            self._state = {}
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self._state = json.load(f)
            logger.debug(f"Loaded phase state from {self.state_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse state file, resetting: {e}")
            self._state = {}
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")
            self._state = {}

    def _save_state(self) -> None:
        """Save state to the JSON file."""
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            logger.debug(f"Saved phase state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
            raise PhaseGateError(f"Failed to save state: {e}") from e

    def _get_phase_index(self, phase: str) -> int:
        """Get the index of a phase in the PHASES list.

        Args:
            phase: Phase name

        Returns:
            Index of the phase

        Raises:
            InvalidPhaseError: If phase is not valid
        """
        try:
            return PHASES.index(phase)
        except ValueError:
            valid_phases = ", ".join(PHASES)
            raise InvalidPhaseError(f"Invalid phase: '{phase}'. Valid phases: {valid_phases}")

    def get_completed_phases(self, workflow_name: str) -> List[str]:
        """Get the list of completed phases for a workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            List of completed phase names
        """
        return self._state.get(workflow_name, [])

    def is_phase_completed(self, workflow_name: str, phase: str) -> bool:
        """Check if a specific phase is completed for a workflow.

        Args:
            workflow_name: Name of the workflow
            phase: Phase name to check

        Returns:
            True if the phase is completed, False otherwise
        """
        return phase in self._state.get(workflow_name, [])

    def can_enter_phase(self, workflow_name: str, target_phase: str) -> bool:
        """Check if a workflow can enter a specific phase.

        A workflow can enter a phase only if all previous phases are completed.

        Args:
            workflow_name: Name of the workflow
            target_phase: Phase to enter

        Returns:
            True if all previous phases are completed, False otherwise

        Raises:
            InvalidPhaseError: If target_phase is not a valid phase name
        """
        # Validate phase
        self._get_phase_index(target_phase)

        completed = self.get_completed_phases(workflow_name)
        completed_indices = {self._get_phase_index(p) for p in completed}

        target_index = self._get_phase_index(target_phase)

        # Check if all previous phases are completed
        required_indices = set(range(target_index))
        return required_indices.issubset(completed_indices)

    def complete_phase(self, workflow_name: str, phase: str) -> None:
        """Mark a phase as completed for a workflow.

        Args:
            workflow_name: Name of the workflow
            phase: Phase to mark as completed

        Raises:
            InvalidPhaseError: If phase is not valid
            PhaseOrderError: If previous phases are not completed
        """
        # Validate phase
        self._get_phase_index(phase)

        # Check if can enter this phase
        if not self.can_enter_phase(workflow_name, phase):
            raise PhaseOrderError(
                f"Cannot complete phase '{phase}' for workflow '{workflow_name}'. "
                f"Previous phases must be completed first."
            )

        # Add to completed phases
        if workflow_name not in self._state:
            self._state[workflow_name] = []

        if phase not in self._state[workflow_name]:
            self._state[workflow_name].append(phase)
            self._save_state()
            logger.info(f"Completed phase '{phase}' for workflow '{workflow_name}'")

    def reset_workflow(self, workflow_name: str) -> None:
        """Reset all phase completions for a workflow.

        Args:
            workflow_name: Name of the workflow
        """
        if workflow_name in self._state:
            del self._state[workflow_name]
            self._save_state()
            logger.info(f"Reset phase state for workflow '{workflow_name}'")

    def get_phase_progress(self, workflow_name: str) -> Dict[str, Any]:
        """Get the progress status for a workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Dictionary with current phase, completed phases, and next available phase
        """
        completed = self.get_completed_phases(workflow_name)

        # Find current phase (first incomplete one)
        current_phase = None
        next_phase = None

        for i, phase in enumerate(PHASES):
            if phase not in completed:
                if current_phase is None:
                    current_phase = phase
                if i > 0 and next_phase is None:
                    next_phase = phase
                break
        else:
            # All phases completed
            current_phase = "completed"

        return {
            "workflow": workflow_name,
            "completed_phases": completed,
            "current_phase": current_phase,
            "next_phase": next_phase,
            "total_phases": len(PHASES),
            "progress_percent": (len(completed) / len(PHASES)) * 100,
        }

    @staticmethod
    def get_valid_phases() -> List[str]:
        """Get the list of valid phase names.

        Returns:
            List of valid phase names
        """
        return PHASES.copy()


# Module-level convenience functions

_gate: Optional[PhaseGate] = None


def get_phase_gate() -> PhaseGate:
    """Get the default PhaseGate instance."""
    global _gate
    if _gate is None:
        _gate = PhaseGate()
    return _gate


def can_enter_phase(workflow_name: str, target_phase: str) -> bool:
    """Check if a workflow can enter a specific phase.

    Args:
        workflow_name: Name of the workflow
        target_phase: Phase to enter

    Returns:
        True if all previous phases are completed, False otherwise
    """
    return get_phase_gate().can_enter_phase(workflow_name, target_phase)


def complete_phase(workflow_name: str, phase: str) -> None:
    """Mark a phase as completed for a workflow.

    Args:
        workflow_name: Name of the workflow
        phase: Phase to mark as completed
    """
    get_phase_gate().complete_phase(workflow_name, phase)


def get_phase_progress(workflow_name: str) -> Dict[str, Any]:
    """Get the progress status for a workflow.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Dictionary with progress information
    """
    return get_phase_gate().get_phase_progress(workflow_name)
