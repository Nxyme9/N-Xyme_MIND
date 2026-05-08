"""
packages.learning_engine.schemas
================================
Pydantic validation models for learning_engine MCP tool parameters.

Provides input validation for:
- record_outcome
- route_task
- log_outcome
- get_outcomes
- get_recommendations
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Task Types and Levels
# =============================================================================

VALID_TASK_TYPES = [
    "implementation",
    "research",
    "review",
    "fix",
    "exploration",
    "delegation",
    "planning",
    "evaluation",
]

VALID_AGENTS = [
    "hephaestus",
    "explore",
    "librarian",
    "oracle",
    "metis",
    "momus",
    "plan",
    "atlas",
    "sisyphus-junior",
    "prometheus",
    "sisyphus",
    "multimodal-looker",
]


# =============================================================================
# Outcome Input Models
# =============================================================================


class RecordOutcomeInput(BaseModel):
    """Input validation for record_outcome tool."""

    task: str = Field(
        description="Task description",
        min_length=1,
        max_length=1000,
    )
    agent: str = Field(
        description="The agent that handled the task",
        min_length=1,
        max_length=100,
    )
    success: bool = Field(
        description="Whether the task succeeded",
    )
    latency_ms: float = Field(
        description="Execution latency in milliseconds",
        default=0,
        ge=0,
    )
    tokens_used: int = Field(
        description="Number of tokens used",
        default=0,
        ge=0,
    )

    @field_validator("task")
    @classmethod
    def task_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task cannot be empty or whitespace")
        return v.strip()

    @field_validator("agent")
    @classmethod
    def validate_agent(cls, v: str) -> str:
        # Allow any agent but warn if not in known list
        if v.strip() not in VALID_AGENTS and v.strip():
            # Just validate not empty, allow custom agents
            pass
        return v.strip()


class LogOutcomeInput(BaseModel):
    """Input validation for log_outcome tool."""

    task_id: str = Field(
        description="Unique identifier for the task",
        min_length=1,
        max_length=100,
    )
    task_description: str = Field(
        description="Description of the task",
        min_length=1,
        max_length=1000,
    )
    task_type: str = Field(
        description="Type of task (implementation, research, review, fix)",
        min_length=1,
        max_length=50,
    )
    agent: str = Field(
        description="Agent that handled the task",
        min_length=1,
        max_length=100,
    )
    level: int = Field(
        description="Complexity level (L1-L5)",
        ge=1,
        le=5,
    )
    success: bool = Field(
        description="Whether the task succeeded",
    )
    latency_ms: float = Field(
        description="Execution latency in milliseconds",
        ge=0,
    )
    tokens_used: int = Field(
        description="Number of tokens used",
        default=0,
        ge=0,
    )

    @field_validator("task_description")
    @classmethod
    def task_description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task description cannot be empty or whitespace")
        return v.strip()

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        if v.lower() not in VALID_TASK_TYPES:
            raise ValueError(f"task_type must be one of: {', '.join(VALID_TASK_TYPES)}")
        return v.lower()

    @field_validator("task_id")
    @classmethod
    def task_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task ID cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Routing Input Models
# =============================================================================


class RouteTaskInput(BaseModel):
    """Input validation for route_task tool."""

    task_description: str = Field(
        description="The task to route",
        min_length=1,
        max_length=1000,
    )

    @field_validator("task_description")
    @classmethod
    def task_description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task description cannot be empty or whitespace")
        return v.strip()


class GetRecommendationsInput(BaseModel):
    """Input validation for get_recommendations tool."""

    task_description: str = Field(
        description="The task to get recommendations for",
        min_length=1,
        max_length=1000,
    )

    @field_validator("task_description")
    @classmethod
    def task_description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task description cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Outcomes Input Models
# =============================================================================


class GetOutcomesInput(BaseModel):
    """Input validation for get_outcomes tool."""

    agent: Optional[str] = Field(
        description="Filter by agent name",
        default=None,
        max_length=100,
    )
    task_type: Optional[str] = Field(
        description="Filter by task type",
        default=None,
        max_length=50,
    )
    limit: int = Field(
        description="Maximum number of outcomes to return",
        default=100,
        ge=1,
        le=1000,
    )

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if v.lower() not in VALID_TASK_TYPES:
                raise ValueError(
                    f"task_type must be one of: {', '.join(VALID_TASK_TYPES)}"
                )
            return v.lower()
        return v


# =============================================================================
# Status Input Models (empty - no params)
# =============================================================================


class StatusInput(BaseModel):
    """Input validation for status tool (no params)."""

    pass


class RetrainInput(BaseModel):
    """Input validation for retrain tool (no params)."""

    pass


class LearningStatsInput(BaseModel):
    """Input validation for learning_stats tool (no params)."""

    pass


class GetLearningProgressInput(BaseModel):
    """Input validation for get_learning_progress tool (no params)."""

    pass
