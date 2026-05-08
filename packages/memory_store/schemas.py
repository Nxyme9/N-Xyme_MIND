"""
packages.memory_store.schemas
=============================
Pydantic validation models for memory_store MCP tool parameters.

Provides input validation for:
- search_memories
- memory_write
- recall_session
- find_context
- memory_search
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Search Input Models
# =============================================================================


class SearchMemoriesInput(BaseModel):
    """Input validation for search_memories tool."""

    query: str = Field(
        description="The search query string",
        min_length=1,
        max_length=1000,
    )
    limit: int = Field(
        description="Maximum number of results to return",
        default=10,
        ge=1,
        le=100,
    )
    strict: bool = Field(
        description="If True, filter out low-confidence results",
        default=False,
    )
    rerank: bool = Field(
        description="If True, apply LLM-based reranking to top candidates",
        default=False,
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()


class MemorySearchInput(BaseModel):
    """Input validation for memory_search tool."""

    query: str = Field(
        description="The search query string",
        min_length=1,
        max_length=1000,
    )
    top_k: int = Field(
        description="Maximum number of results to return",
        default=10,
        ge=1,
        le=100,
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Write Input Models
# =============================================================================


class MemoryWriteInput(BaseModel):
    """Input validation for memory_write tool."""

    content: str = Field(
        description="The memory content to store",
        min_length=1,
        max_length=50000,
    )
    kind: Literal["episodic", "semantic", "procedural", "declarative"] = Field(
        description="Type of memory",
        default="episodic",
    )
    scope: Literal["global", "session", "project"] = Field(
        description="Scope of memory",
        default="global",
    )
    tags: Optional[list[str]] = Field(
        description="Optional tags for the memory",
        default=None,
    )

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Session Input Models
# =============================================================================


class RecallSessionInput(BaseModel):
    """Input validation for recall_session tool."""

    session_id: Optional[str] = Field(
        description="Session ID to recall (None for current)",
        default=None,
        max_length=100,
    )
    limit: int = Field(
        description="Maximum number of lines to return",
        default=50,
        ge=1,
        le=500,
    )


# =============================================================================
# Context Input Models
# =============================================================================


class FindContextInput(BaseModel):
    """Input validation for find_context tool."""

    task: str = Field(
        description="The task to find relevant context for",
        min_length=1,
        max_length=1000,
    )
    context_type: Literal["all", "episodic", "semantic", "procedural"] = Field(
        description="Type of context to search",
        default="all",
    )

    @field_validator("task")
    @classmethod
    def task_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Stats Input Models (empty - no params)
# =============================================================================


class GetMemoryStatsInput(BaseModel):
    """Input validation for get_memory_stats tool (no params)."""

    pass


class MemoryStatsInput(BaseModel):
    """Input validation for memory_stats tool (no params)."""

    pass
