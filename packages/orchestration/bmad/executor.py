"""BMAD Workflow Executor — Load and execute BMAD workflows from _bmad/.

BMAD workflows are defined in:
    - _bmad/bmm/workflows/<workflow-name>/     (50+ workflows)
    - _bmad/tea/workflows/<workflow-name>/     (6 workflows)
    - _bmad/catalyst/workflows/<workflow-name>/ (3 workflows)

Each workflow contains:
    - workflow.yaml     : Metadata and configuration (optional)
    - workflow.md       : Entrypoint with mode routing
    - steps/            : Steps directory (BMM format)
    - steps-c/          : Create mode steps (TEA format)
    - steps-e/          : Edit mode steps (TEA format)
    - steps-v/          : Validate mode steps (TEA format)
"""

import logging
import os
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default BMAD workflows root directories
BMAD_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/_bmad")

# Module directories
BMM_WORKFLOWS_DIR = BMAD_ROOT / "bmm" / "workflows"
TEA_WORKFLOWS_DIR = BMAD_ROOT / "tea" / "workflows"
CATALYST_WORKFLOWS_DIR = BMAD_ROOT / "catalyst" / "workflows"


@dataclass
class WorkflowStep:
    """A single step in a workflow phase."""

    name: str
    path: Path
    order: int


@dataclass
class WorkflowPhase:
    """A phase in a workflow (create, edit, validate)."""

    name: str
    steps: List[WorkflowStep] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""

    name: str
    description: str
    path: Path
    phases: Dict[str, WorkflowPhase] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Result of executing a workflow."""

    workflow_name: str
    phase: str
    success: bool
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BMADExecutor:
    """Executor for BMAD workflows.

    Supports loading workflows from:
    - BMM: _bmad/bmm/workflows/<workflow>/
    - TEA: _bmad/tea/workflows/<workflow>/
    - Catalyst: _bmad/catalyst/workflows/<workflow>/

    Usage:
        executor = BMADExecutor()
        workflow = executor.load("bmad-create-product-brief")
        result = executor.execute(workflow, phase="create")
    """

    def __init__(
        self,
        bmm_dir: Optional[Path] = None,
        tea_dir: Optional[Path] = None,
        catalyst_dir: Optional[Path] = None,
    ):
        """Initialize the executor.

        Args:
            bmm_dir: Path to _bmad/bmm/workflows directory.
            tea_dir: Path to _bmad/tea/workflows directory.
            catalyst_dir: Path to _bmad/catalyst/workflows directory.
        """
        self.bmm_dir = bmm_dir or BMM_WORKFLOWS_DIR
        self.tea_dir = tea_dir or TEA_WORKFLOWS_DIR
        self.catalyst_dir = catalyst_dir or CATALYST_WORKFLOWS_DIR
        self._workflow_cache: Dict[str, WorkflowDefinition] = {}
        self._registry_built: bool = False
        self._workflow_registry: Dict[str, Dict[str, Any]] = {}

    def _build_registry(self) -> None:
        """Build workflow registry mapping names to paths and modules.

        Uses lazy initialization - only builds when first accessed.
        """
        if self._registry_built:
            return

        self._workflow_registry = {}

        # Scan all three module directories
        for module_dir, module_name in [
            (self.bmm_dir, "bmm"),
            (self.tea_dir, "tea"),
            (self.catalyst_dir, "catalyst"),
        ]:
            if not module_dir.exists():
                logger.warning(f"Module directory does not exist: {module_dir}")
                continue

            try:
                for category in module_dir.iterdir():
                    if not category.is_dir():
                        continue

                    # Scan workflows in category
                    for workflow_dir in category.iterdir():
                        if not workflow_dir.is_dir():
                            continue

                        workflow_name = workflow_dir.name
                        full_path = workflow_dir

                        # Check if it's a valid workflow (has workflow.md or workflow.yaml)
                        is_valid = (
                            (workflow_dir / "workflow.md").exists()
                            or (workflow_dir / "workflow.yaml").exists()
                        ) and (workflow_dir / "steps").exists()

                        # TEA format uses workflow.yaml with steps-c/e/v
                        is_valid_tea = (workflow_dir / "workflow.yaml").exists() and (
                            (workflow_dir / "steps-c").exists()
                            or (workflow_dir / "steps-e").exists()
                            or (workflow_dir / "steps-v").exists()
                        )

                        if is_valid or is_valid_tea:
                            self._workflow_registry[workflow_name] = {
                                "path": full_path,
                                "module": module_name,
                                "category": category.name,
                            }
                            logger.debug(
                                f"Registered workflow: {workflow_name} ({module_name})"
                            )

            except Exception as e:
                logger.error(f"Error scanning module {module_name}: {e}")

        self._registry_built = True
        logger.info(
            f"Workflow registry built: {len(self._workflow_registry)} workflows"
        )

    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the workflow registry.

        Returns:
            Dict mapping workflow names to {path, module, category}
        """
        self._build_registry()
        return self._workflow_registry

    def list_workflows(self) -> List[str]:
        """List all available workflow names from all modules.

        Returns:
            List of workflow directory names
        """
        self._build_registry()
        return sorted(self._workflow_registry.keys())

    def list_workflows_by_module(self) -> Dict[str, List[str]]:
        """List workflows grouped by module.

        Returns:
            Dict with module -> list of workflow names
        """
        self._build_registry()
        result = {"bmm": [], "tea": [], "catalyst": []}
        for name, info in self._workflow_registry.items():
            module = info["module"]
            if module in result:
                result[module].append(name)
        return result

    def load(self, workflow_name: str) -> Optional[WorkflowDefinition]:
        """Load a workflow definition by name.

        Args:
            workflow_name: Name of the workflow (e.g., "bmad-create-product-brief")

        Returns:
            WorkflowDefinition or None if not found
        """
        # Check cache first
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]

        # Use registry to find workflow path
        self._build_registry()
        registry_entry = self._workflow_registry.get(workflow_name)
        
        if not registry_entry:
            logger.error(f"Workflow not found in registry: {workflow_name}")
            return None

        workflow_path = registry_entry["path"]
        if not workflow_path.exists():
            logger.error(f"Workflow path does not exist: {workflow_path}")
            return None

        try:
            # Load workflow.yaml or workflow.md
            yaml_path = workflow_path / "workflow.yaml"
            md_path = workflow_path / "workflow.md"
            
            config = {}
            description = ""
            
            if yaml_path.exists():
                with open(yaml_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                description = config.get("description", "")
            elif md_path.exists():
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                # Extract description from first heading or first paragraph
                lines = md_content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("# "):
                        description = line.replace("#", "").strip()
                        break
                    elif line.strip() and not line.strip().startswith("<!--"):
                        description = line.strip()[:200]
                        break

            # Parse phases based on module type
            module = registry_entry["module"]
            phases = self._load_phases(workflow_path, module)

            workflow = WorkflowDefinition(
                name=config.get("name", workflow_name),
                description=description,
                path=workflow_path,
                phases=phases,
                config=config,
                tags=config.get("tags", []),
                required_tools=config.get("required_tools", []),
            )

            # Cache it
            self._workflow_cache[workflow_name] = workflow
            return workflow

        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_name}: {e}")
            return None

    def _load_phases(self, workflow_path: Path, module: str) -> Dict[str, WorkflowPhase]:
        """Load workflow phases from steps directories.
        
        Args:
            workflow_path: Path to workflow directory
            module: Module type (bmm, tea, catalyst)
        """
        phases = {}

        if module == "bmm":
            # BMM format: steps/ directory with numbered steps
            steps_dir = workflow_path / "steps"
            steps = []
            
            if steps_dir.exists():
                for step_file in sorted(steps_dir.glob("*.md")):
                    # Extract order from filename like "01-xxx.md" or just use sorted order
                    name = step_file.stem
                    order = 0
                    match = re.match(r"(\d+)", name)
                    if match:
                        order = int(match.group(1))
                    else:
                        # Use alphabetical order as fallback
                        order = list(sorted(steps_dir.glob("*.md"))).index(step_file)
                    
                    steps.append(
                        WorkflowStep(
                            name=name,
                            path=step_file,
                            order=order,
                        )
                    )
            
            # Sort by order
            steps.sort(key=lambda s: s.order)
            
            # BMM workflows have a single "create" phase by default
            phases["create"] = WorkflowPhase(name="create", steps=steps)
            
        else:
            # TEA/Catalyst format: steps-c, steps-e, steps-v directories
            phase_dirs = {
                "create": "steps-c",
                "edit": "steps-e",
                "validate": "steps-v",
            }

            for phase_name, dir_name in phase_dirs.items():
                phase_path = workflow_path / dir_name
                steps = []

                if phase_path.exists():
                    # Load step files in order
                    for step_file in sorted(phase_path.glob("step-*.md")):
                        # Extract order from filename like "step-01-xxx.md"
                        match = re.match(r"step-(\d+)", step_file.stem)
                        if match:
                            order = int(match.group(1))
                            steps.append(
                                WorkflowStep(
                                    name=step_file.stem,
                                    path=step_file,
                                    order=order,
                                )
                            )

                # Sort steps by order
                steps.sort(key=lambda s: s.order)
                phases[phase_name] = WorkflowPhase(name=phase_name, steps=steps)

        return phases

    def execute(
        self,
        workflow: WorkflowDefinition,
        phase: str = "create",
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute a workflow phase.

        Args:
            workflow: Loaded workflow definition
            phase: Phase to execute ("create", "edit", "validate")
            context: Optional execution context

        Returns:
            WorkflowResult with execution details
        """
        context = context or {}
        result = WorkflowResult(
            workflow_name=workflow.name,
            phase=phase,
            success=True,
        )

        try:
            phase_data = workflow.phases.get(phase)
            if not phase_data or not phase_data.steps:
                result.success = False
                result.error = f"No steps found for phase: {phase}"
                return result

            logger.info(
                f"Executing {workflow.name} phase '{phase}' with {len(phase_data.steps)} steps"
            )

            # Execute each step
            for step in phase_data.steps:
                try:
                    # Read step content (for now, just track completion)
                    # In a full implementation, this would execute the step
                    with open(step.path, "r", encoding="utf-8") as f:
                        content = f.read()

                    result.steps_completed.append(step.name)
                    result.output[step.name] = {
                        "path": str(step.path),
                        "lines": len(content.splitlines()),
                    }
                    logger.debug(f"Completed step: {step.name}")

                except Exception as e:
                    result.steps_failed.append(step.name)
                    result.success = False
                    logger.error(f"Failed step {step.name}: {e}")
                    result.error = f"Step {step.name} failed: {e}"
                    break

        except Exception as e:
            result.success = False
            result.error = f"Workflow execution failed: {e}"
            logger.error(f"Workflow {workflow.name} failed: {e}")

        return result

    def get_step_content(
        self, workflow: WorkflowDefinition, phase: str, step_name: str
    ) -> Optional[str]:
        """Get the content of a specific step file.

        Args:
            workflow: Loaded workflow definition
            phase: Phase name ("create", "edit", "validate")
            step_name: Step name (e.g., "step-01-load-context")

        Returns:
            Step content or None if not found
        """
        phase_data = workflow.phases.get(phase)
        if not phase_data:
            return None

        for step in phase_data.steps:
            if step.name == step_name:
                try:
                    with open(step.path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    logger.error(f"Failed to read step {step_name}: {e}")
                    return None

        return None


# Module-level convenience functions

_executor: Optional[BMADExecutor] = None


def get_executor() -> BMADExecutor:
    """Get the default executor instance."""
    global _executor
    if _executor is None:
        _executor = BMADExecutor()
    return _executor


def load_workflow(workflow_name: str) -> Optional[WorkflowDefinition]:
    """Load a workflow by name.

    Args:
        workflow_name: Name of the workflow

    Returns:
        WorkflowDefinition or None
    """
    return get_executor().load(workflow_name)


def list_workflows() -> List[str]:
    """List all available workflows.

    Returns:
        List of workflow names
    """
    return get_executor().list_workflows()


def execute_workflow(
    workflow_name: str,
    phase: str = "create",
    context: Optional[Dict[str, Any]] = None,
) -> WorkflowResult:
    """Execute a workflow by name.

    Args:
        workflow_name: Name of the workflow
        phase: Phase to execute
        context: Optional execution context

    Returns:
        WorkflowResult
    """
    executor = get_executor()
    workflow = executor.load(workflow_name)
    if workflow is None:
        return WorkflowResult(
            workflow_name=workflow_name,
            phase=phase,
            success=False,
            error=f"Workflow not found: {workflow_name}",
        )
    return executor.execute(workflow, phase, context)


def get_registry() -> Dict[str, Dict[str, Any]]:
    """Get the workflow registry.

    Returns:
        Dict mapping workflow names to {path, module, category}
    """
    return get_executor().get_registry()


def list_workflows_by_module() -> Dict[str, List[str]]:
    """List workflows grouped by module.

    Returns:
        Dict with module -> list of workflow names
    """
    return get_executor().list_workflows_by_module()
