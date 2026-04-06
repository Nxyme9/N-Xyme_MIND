"""Task Decomposition Engine

Automatically breaks down complex tasks into subtasks and routes them
to appropriate agents. Supports dependency tracking and result aggregation.
"""

import re
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("task-decomposer")


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    ARCHITECT = 4


@dataclass
class SubTask:
    """A decomposed subtask."""
    id: str
    description: str
    agent: str
    level: int
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class TaskPlan:
    """A complete task decomposition plan."""
    original_task: str
    complexity: TaskComplexity
    subtasks: List[SubTask] = field(default_factory=list)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    
    def get_ready_subtasks(self) -> List[SubTask]:
        """Get subtasks that are ready to execute (all dependencies met)."""
        completed_ids = {st.id for st in self.subtasks if st.status == "completed"}
        return [
            st for st in self.subtasks 
            if st.status == "pending" and all(dep in completed_ids for dep in st.dependencies)
        ]
    
    def is_complete(self) -> bool:
        """Check if all subtasks are completed."""
        return all(st.status == "completed" for st in self.subtasks)
    
    def get_result_summary(self) -> str:
        """Get summary of all subtask results."""
        results = []
        for st in self.subtasks:
            if st.result:
                results.append(f"{st.agent}: {st.result[:100]}")
        return "\n".join(results)


class TaskDecomposer:
    """Decomposes complex tasks into subtasks for multi-agent execution."""
    
    def __init__(self):
        self._decomposition_rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load task decomposition rules."""
        return [
            {
                "pattern": r"(?i)(build|create|implement).*from\s*scratch",
                "complexity": TaskComplexity.ARCHITECT,
                "subtasks": [
                    {"description": "Analyze requirements and create specification", "agent": "prometheus", "level": 4},
                    {"description": "Design system architecture", "agent": "metis", "level": 5},
                    {"description": "Create implementation plan", "agent": "prometheus", "level": 4},
                    {"description": "Implement core functionality", "agent": "hephaestus", "level": 3},
                    {"description": "Review architecture and implementation", "agent": "oracle", "level": 4},
                ]
            },
            {
                "pattern": r"(?i)(refactor|restructure|reorganize)",
                "complexity": TaskComplexity.COMPLEX,
                "subtasks": [
                    {"description": "Analyze current code structure", "agent": "explore", "level": 3},
                    {"description": "Create refactoring plan", "agent": "prometheus", "level": 4},
                    {"description": "Implement refactoring", "agent": "hephaestus", "level": 3},
                    {"description": "Verify refactoring correctness", "agent": "oracle", "level": 3},
                ]
            },
            {
                "pattern": r"(?i)(add|implement).*(feature|functionality|system)",
                "complexity": TaskComplexity.COMPLEX,
                "subtasks": [
                    {"description": "Research existing patterns and implementations", "agent": "explore", "level": 3},
                    {"description": "Design feature architecture", "agent": "prometheus", "level": 4},
                    {"description": "Implement feature", "agent": "hephaestus", "level": 3},
                    {"description": "Write tests for feature", "agent": "hephaestus", "level": 2},
                ]
            },
            {
                "pattern": r"(?i)(fix|debug|resolve).*(bug|issue|error|crash)",
                "complexity": TaskComplexity.MODERATE,
                "subtasks": [
                    {"description": "Investigate root cause", "agent": "explore", "level": 2},
                    {"description": "Implement fix", "agent": "hephaestus", "level": 2},
                    {"description": "Verify fix and test", "agent": "hephaestus", "level": 2},
                ]
            },
            {
                "pattern": r"(?i)(test|write.*tests|add.*coverage)",
                "complexity": TaskComplexity.MODERATE,
                "subtasks": [
                    {"description": "Analyze code to test", "agent": "explore", "level": 2},
                    {"description": "Write test cases", "agent": "hephaestus", "level": 2},
                    {"description": "Run tests and verify coverage", "agent": "hephaestus", "level": 2},
                ]
            },
            {
                "pattern": r"(?i)(review|audit|analyze).*(code|implementation|architecture)",
                "complexity": TaskComplexity.MODERATE,
                "subtasks": [
                    {"description": "Review code quality and patterns", "agent": "oracle", "level": 3},
                    {"description": "Identify potential issues", "agent": "momus", "level": 3},
                    {"description": "Provide recommendations", "agent": "oracle", "level": 3},
                ]
            },
            {
                "pattern": r"(?i)(update|upgrade|migrate).*(version|dependency|library)",
                "complexity": TaskComplexity.SIMPLE,
                "subtasks": [
                    {"description": "Check current version and compatibility", "agent": "explore", "level": 1},
                    {"description": "Update version and dependencies", "agent": "hephaestus", "level": 2},
                    {"description": "Verify compatibility and test", "agent": "hephaestus", "level": 2},
                ]
            },
            {
                "pattern": r"(?i)(document|write.*docs|create.*documentation)",
                "complexity": TaskComplexity.SIMPLE,
                "subtasks": [
                    {"description": "Analyze code to document", "agent": "explore", "level": 1},
                    {"description": "Write documentation", "agent": "sisyphus-junior", "level": 1},
                ]
            },
        ]
    
    def decompose_task(self, task_description: str) -> TaskPlan:
        """Decompose a task into subtasks."""
        # Find matching rule
        matching_rule = None
        for rule in self._decomposition_rules:
            if re.search(rule["pattern"], task_description):
                matching_rule = rule
                break
        
        if not matching_rule:
            # Default: single task
            return TaskPlan(
                original_task=task_description,
                complexity=TaskComplexity.MODERATE,
                subtasks=[
                    SubTask(
                        id="task_0",
                        description=task_description,
                        agent="hephaestus",
                        level=2
                    )
                ]
            )
        
        # Create subtasks with dependencies
        subtasks = []
        for i, st_def in enumerate(matching_rule["subtasks"]):
            # Dependencies: previous subtasks must complete first
            dependencies = [f"task_{j}" for j in range(i)] if i > 0 else []
            
            subtask = SubTask(
                id=f"task_{i}",
                description=st_def["description"],
                agent=st_def["agent"],
                level=st_def["level"],
                dependencies=dependencies
            )
            subtasks.append(subtask)
        
        return TaskPlan(
            original_task=task_description,
            complexity=matching_rule["complexity"],
            subtasks=subtasks
        )
    
    def get_execution_order(self, plan: TaskPlan) -> List[List[SubTask]]:
        """Get execution order respecting dependencies."""
        order = []
        completed = set()
        remaining = list(plan.subtasks)
        
        while remaining:
            # Find subtasks with all dependencies met
            ready = [
                st for st in remaining 
                if all(dep in completed for dep in st.dependencies)
            ]
            
            if not ready:
                # Circular dependency or error
                logger.warning(f"Circular dependency detected in task plan")
                break
            
            order.append(ready)
            for st in ready:
                completed.add(st.id)
                remaining.remove(st)
        
        return order
    
    def get_plan_summary(self, plan: TaskPlan) -> str:
        """Get human-readable summary of task plan."""
        lines = [
            f"Task: {plan.original_task}",
            f"Complexity: {plan.complexity.name}",
            f"Subtasks: {len(plan.subtasks)}",
            ""
        ]
        
        execution_order = self.get_execution_order(plan)
        for i, batch in enumerate(execution_order):
            lines.append(f"Batch {i + 1} (can run in parallel):")
            for st in batch:
                deps = f" (depends on: {', '.join(st.dependencies)})" if st.dependencies else ""
                lines.append(f"  - [{st.id}] {st.description} → {st.agent} (L{st.level}){deps}")
        
        return "\n".join(lines)


# Global decomposer instance
_decomposer = None

def get_task_decomposer() -> TaskDecomposer:
    """Get or create the global task decomposer."""
    global _decomposer
    if _decomposer is None:
        _decomposer = TaskDecomposer()
    return _decomposer
