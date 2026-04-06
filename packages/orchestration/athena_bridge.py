"""
Athena Bridge - Safe bridge between BMAD planning and oh-my-opencode execution

Converts BMAD plans into oh-my-opencode tasks for Sisyphus orchestration.

Usage:
    bridge = AthenaBridge()
    tasks = bridge.convert_plan(bmad_plan)
    bridge.execute(tasks)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.orchestration.thinking_effort import ThinkingEffort

logger = logging.getLogger(__name__)


@dataclass
class BMADStory:
    """A BMAD user story."""

    id: str
    title: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: str = "medium"
    estimated_hours: float = 0


@dataclass
class Task:
    """An oh-my-opencode task."""

    id: str
    title: str
    description: str
    agent: str  # Which oh-my-opencode agent should execute
    category: str  # deep, quick, writing, etc.
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    thinking_effort: str = "medium"  # Dynamic thinking level
    file_count: int = 1  # For complexity evaluation


class AthenaBridge:
    """Bridge BMAD planning to oh-my-opencode execution."""

    # BMAD role -> oh-my-opencode agent mapping
    # CORRECTED: Each role maps to agent with matching domain expertise
    AGENT_MAP = {
        "analyst": "oracle",  # Deep reasoning for market research and analysis
        "architect": "hephaestus",  # Code implementation for system design
        "dev": "hephaestus",  # Code implementation for development
        "pm": "prometheus",  # Planning for product management
        "qa": "tester",  # Testing agent for quality assurance
        "sm": "atlas",  # Orchestration for sprint management
        "tech-writer": "companion",  # Writing agent for documentation
        "ux-designer": "multimodal-looker",  # Visual analysis for UX design
    }

    # Task type -> oh-my-opencode category mapping
    CATEGORY_MAP = {
        "research": "deep",
        "analysis": "deep",
        "architecture": "ultrabrain",
        "coding": "deep",
        "testing": "quick",
        "documentation": "writing",
        "review": "deep",
        "debugging": "deep",
        "refactoring": "deep",
        "planning": "unspecified-high",
        "design": "visual-engineering",
        "sprint": "unspecified-high",
        "story": "unspecified-high",
        "prd": "writing",
    }

    def __init__(self, bmad_dir: str = "_bmad"):
        self.bmad_dir = Path(bmad_dir)
        self._plans: List[Dict] = []
        self.thinking = ThinkingEffort()
        self._coordinator = None
        logger.info("AthenaBridge: Initialized with dynamic thinking effort")

    def set_coordinator(self, coordinator) -> None:
        """Set the agent coordinator for task dispatch."""
        self._coordinator = coordinator

    def load_plan(self, plan_path: str) -> Dict:
        """Load a BMAD plan from file."""
        path = Path(plan_path)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def convert_plan(self, bmad_plan: Dict) -> List[Task]:
        """Convert BMAD plan to oh-my-opencode tasks."""
        tasks = []
        stories = bmad_plan.get("stories", [])

        for story in stories:
            # Determine which agent should execute
            role = story.get("assigned_to", "dev")
            agent = self.AGENT_MAP.get(role, "hephaestus")

            # Determine task category
            task_type = story.get("type", "coding")
            category = self.CATEGORY_MAP.get(task_type, "deep")

            task = Task(
                id=story.get("id", f"task_{len(tasks)}"),
                title=story.get("title", "Untitled"),
                description=story.get("description", ""),
                agent=agent,
                category=category,
                dependencies=story.get("depends_on", []),
                file_count=story.get("file_count", 1),
            )
            tasks.append(task)

        logger.info(f"AthenaBridge: Converted {len(stories)} stories to {len(tasks)} tasks")
        return tasks

    def convert_story(self, story: BMADStory) -> Task:
        """Convert a single BMAD story to an oh-my-opencode task."""
        return Task(
            id=story.id,
            title=story.title,
            description=story.description,
            agent="hephaestus",
            category="deep",
        )

    def execute(self, tasks: List[Task], output_dir: str = ".athena-queue") -> Dict[str, str]:
        """
        Execute tasks via oh-my-opencode agents.

        Writes tasks to a queue directory for Sisyphus orchestration.
        Each task becomes a JSON file that agents can pick up.
        Applies dynamic thinking effort based on task complexity.

        Args:
            tasks: List of tasks to execute
            output_dir: Directory to write task queue files

        Returns:
            Dict mapping task.id to status ("queued", "error: ...")
        """
        queue_path = Path(output_dir)
        queue_path.mkdir(parents=True, exist_ok=True)

        results = {}
        manifest = {
            "created_at": datetime.now().isoformat(),
            "task_count": len(tasks),
            "tasks": [],
        }

        for task in tasks:
            try:
                # Apply dynamic thinking effort
                task.thinking_effort = self.thinking.evaluate(
                    task_description=task.description,
                    file_count=task.file_count,
                    agent=task.agent,
                    category=task.category,
                )
                effort_config = self.thinking.get_effort_config(task.thinking_effort)

                logger.info(
                    f"AthenaBridge: Queuing {task.id} via {task.agent} (thinking: {task.thinking_effort})"
                )

                # Create task file with thinking effort config
                task_file = queue_path / f"{task.id}.json"
                task_data = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "agent": task.agent,
                    "category": task.category,
                    "dependencies": task.dependencies,
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "thinking_effort": task.thinking_effort,
                    "thinking_config": effort_config,
                    "file_count": task.file_count,
                }
                task_file.write_text(
                    json.dumps(task_data, indent=2, ensure_ascii=False), encoding="utf-8"
                )

                # Add to manifest
                manifest["tasks"].append(
                    {
                        "id": task.id,
                        "file": str(task_file),
                        "agent": task.agent,
                        "category": task.category,
                        "thinking_effort": task.thinking_effort,
                    }
                )

                results[task.id] = "queued"

                # Delegate to agent coordinator if available
                if self._coordinator:
                    coord_task_id = self._coordinator.assign_task(
                        task_type=task.category,
                        task_data={
                            "athena_task_id": task.id,
                            "title": task.title,
                            "description": task.description,
                            "agent": task.agent,
                            "thinking_effort": task.thinking_effort,
                        },
                    )
                    if coord_task_id:
                        logger.info(f"AthenaBridge: Delegated {task.id} to coordinator")

            except Exception as e:
                logger.error(f"AthenaBridge: Failed to queue {task.id}: {e}")
                results[task.id] = f"error: {e}"

        # Write manifest
        manifest_file = queue_path / "manifest.json"
        manifest_file.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        logger.info(
            f"AthenaBridge: Queued {len([v for v in results.values() if v == 'queued'])} tasks to {queue_path}"
        )
        return results

    def check_execution_status(self, task_id: str, queue_dir: str = ".athena-queue") -> str:
        """Check the execution status of a queued task."""
        task_file = Path(queue_dir) / f"{task_id}.json"
        if not task_file.exists():
            return "not_found"

        try:
            task_data = json.loads(task_file.read_text(encoding="utf-8"))
            return task_data.get("status", "unknown")
        except Exception:
            return "error_reading"

    def get_queue_manifest(self, queue_dir: str = ".athena-queue") -> Optional[Dict]:
        """Get the current queue manifest."""
        manifest_file = Path(queue_dir) / "manifest.json"
        if not manifest_file.exists():
            return None

        try:
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_bmad_agents(self) -> List[str]:
        """Get list of available BMAD agents."""
        agents_dir = self.bmad_dir / "_config" / "agents"
        if agents_dir.exists():
            return [f.stem.replace(".customize", "") for f in agents_dir.glob("*.yaml")]
        return []

    def get_bmad_workflows(self) -> Dict[str, List[str]]:
        """Get list of available BMAD workflows by phase."""
        workflows_dir = self.bmad_dir / "bmm" / "workflows"
        result = {}
        if workflows_dir.exists():
            for phase_dir in workflows_dir.iterdir():
                if phase_dir.is_dir():
                    phase = phase_dir.name
                    workflows = [d.name for d in phase_dir.iterdir() if d.is_dir()]
                    result[phase] = workflows
        return result

    def get_status(self) -> Dict:
        """Get bridge status."""
        return {
            "bmad_agents": len(self.get_bmad_agents()),
            "bmad_workflows": sum(len(v) for v in self.get_bmad_workflows().values()),
            "agent_map": self.AGENT_MAP,
            "category_map": self.CATEGORY_MAP,
        }
