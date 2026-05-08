"""
packages.intelligence.schemas
=============================
Pydantic validation models for intelligence MCP tool parameters.

Provides input validation for:
- route
- score_complexity
- available_agents
- get_routing_history
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Routing Input Models
# =============================================================================


class RouteInput(BaseModel):
    """Input validation for route tool."""

    task_description: str = Field(
        description="The task to route",
        min_length=1,
        max_length=1000,
    )
    context: Optional[dict] = Field(
        description="Optional context dictionary",
        default=None,
    )

    @field_validator("task_description")
    @classmethod
    def task_description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task description cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Complexity Scoring Input Models
# =============================================================================


class ScoreComplexityInput(BaseModel):
    """Input validation for score_complexity tool."""

    task_description: str = Field(
        description="The task to score",
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
# History Input Models
# =============================================================================


class GetRoutingHistoryInput(BaseModel):
    """Input validation for get_routing_history tool."""

    limit: int = Field(
        description="Maximum number of entries to return",
        default=10,
        ge=0,
        le=100,
    )


# =============================================================================
# Agent Listing Input Models (empty - no params)
# =============================================================================


class AvailableAgentsInput(BaseModel):
    """Input validation for available_agents tool (no params)."""

    pass
