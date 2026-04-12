"""
Tool Orchestrator - Concurrency-safe tool execution.

Based on leaked Anthropic source code patterns from toolOrchestration.ts.
Provides read-only tool parallelization and write tool serialization.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_MAX_CONCURRENCY = 4


def get_max_tool_use_concurrency() -> int:
    """
    Get max tool use concurrency from environment variable.
    Defaults to 4 per N-Xyme_MIND requirements.
    """
    env_value = os.environ.get("CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY")
    if env_value:
        try:
            parsed = int(env_value, 10)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_MAX_CONCURRENCY


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ToolCall:
    """Represents a single tool call with concurrency metadata."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_id: str
    is_concurrency_safe: bool = False


@dataclass
class ToolBatch:
    """A batch of tool calls that can be executed together."""

    is_concurrency_safe: bool
    blocks: list[ToolCall] = field(default_factory=list)


# ============================================================================
# Tool Classifier
# ============================================================================


class ToolClassifier:
    """
    Classifies tools by their concurrency safety.

    Read-only tools can run in parallel.
    Write/destructive tools must run serially.
    """

    # Read-only tool names (safe for concurrent execution)
    READ_ONLY_TOOLS: set[str] = {
        "grep",
        "read",
        "glob",
        "lsp_goto_definition",
        "lsp_find_references",
        "lsp_symbols",
        "lsp_diagnostics",
        "lsp_prepare_rename",
        "session_read",
        "session_search",
        "session_info",
        "session_list",
        "webfetch",
        "websearch",
        "codesearch",
        "github_get_file_contents",
        "github_list_commits",
        "github_list_issues",
        "github_list_pull_requests",
        "github_get_issue",
        "github_get_pull_request",
        "github_search_code",
        "github_search_issues",
        "github_search_users",
        "github_search_repositories",
        "github_get_pull_request_files",
        "github_get_pull_request_comments",
        "github_get_pull_request_reviews",
        "github_get_pull_request_status",
        "look_at",
        "notion_API-get-block-children",
        "notion_API-retrieve-a-block",
        "notion_API-retrieve-a-page",
        "notion_API-retrieve-a-page-property",
        "notion_API-retrieve-a-database",
        "notion_API-retrieve-a-data-source",
        "notion_API-retrieve-a-comment",
        "notion_API-get-self",
        "notion_API-get-user",
        "notion_API-get-users",
        "notion_API-post-search",
        "notion_API-list-data-source-templates",
        "unified-memory_search_memories",
        "unified-memory_get_memory_stats",
        "unified-memory_recall_session",
        "unified-memory_find_context",
        "unified-memory_memory_search",
        "unified-memory_memory_stats",
        "nx-context_get_active_context",
        "nx-context_get_product_context",
        "nx-context_get_user_context",
        "nx-context_get_constraints",
        "nx-context_get_user_profile",
        "nx-context_get_style_context",
        "nx-context_get_archive_context",
        "nx-context_get_bmad_agents",
        "nx-context_get_bmad_workflows",
        "nx-context_inject_context",
        "nx-context_get_capabilities",
        "nx-context_health_check",
        "nx-mind_get_mind_state",
        "nx-mind_get_session_history",
        "nx-mind_get_active_workflow",
        "nx-mind_get_project_manifest",
        "nx-mind_spine_probe",
        "nx-mind_spine_status",
        "intelligence_route",
        "intelligence_score_complexity",
        "intelligence_available_agents",
        "intelligence_get_routing_history",
        "session-pool_route_task",
        "session-pool_pool_stats",
        "catalyst_list_workflows",
        "catalyst_get_orchestrator_status",
        "trigger-guardian_list_triggers",
        "trigger-guardian_check_trigger",
        "learning-engine_status",
        "learning-engine_learning_stats",
        "learning-engine_get_recommendations",
        "learning-engine_get_outcomes",
        "unified-memory_get_memory_stats",
    }

    # Write/destructive tool names (must run serially)
    WRITE_TOOLS: set[str] = {
        "edit",
        "write",
        "bash",
        "github_create_or_update_file",
        "github_push_files",
        "github_create_repository",
        "github_create_org_repository",
        "github_create_issue",
        "github_create_pull_request",
        "github_update_issue",
        "github_add_issue_comment",
        "github_create_branch",
        "github_fork_repository",
        "github_merge_pull_request",
        "github_update_pull_request_branch",
        "github_create_pull_request_review",
        "notion_API-post-page",
        "notion_API-patch-page",
        "notion_API-update-a-block",
        "notion_API-delete-a-block",
        "notion_API-patch-block-children",
        "notion_API-move-page",
        "notion_API-create-a-comment",
        "notion_API-create-a-data-source",
        "notion_API-update-a-data-source",
        "unified-memory_memory_write",
        "nx-mind_update_mind_state",
        "nx-mind_set_context",
        "nx-mind_log_task_completion",
        "nx-mind_sync_to_memory",
        "nx-mind_spine_run",
        "trigger-guardian_register_trigger",
        "trigger-guardian_log_trigger_event",
        "trigger-guardian_clear_triggers",
        "learning-engine_record_outcome",
        "learning-engine_log_outcome",
        "learning-engine_retrain",
        "orchestration_spawn",
    }

    @classmethod
    def is_read_only(cls, tool_name: str, tool_input: Optional[dict] = None) -> bool:
        """
        Check if a tool is read-only.

        Args:
            tool_name: Name of the tool
            tool_input: Optional tool input for deeper inspection

        Returns:
            True if tool is read-only, False otherwise
        """
        # Direct name match in read-only set
        if tool_name in cls.READ_ONLY_TOOLS:
            return True

        # Check if it's a write tool (explicitly not read-only)
        if tool_name in cls.WRITE_TOOLS:
            return False

        # Check for read-like patterns in name
        read_patterns = ("get_", "list_", "search_", "query_", "fetch", "read")
        if any(tool_name.startswith(p) for p in read_patterns):
            return True

        # Check for write-like patterns in name
        write_patterns = ("create_", "update_", "delete_", "write_", "push_", "merge_")
        if any(tool_name.startswith(p) for p in write_patterns):
            return False

        # Default: assume non-concurrency-safe
        return False

    @classmethod
    def is_destructive(cls, tool_name: str, tool_input: Optional[dict] = None) -> bool:
        """
        Check if a tool is destructive (modifies state).

        Args:
            tool_name: Name of the tool
            tool_input: Optional tool input for deeper inspection

        Returns:
            True if tool is destructive, False otherwise
        """
        # Explicit destructive tools
        if tool_name in cls.WRITE_TOOLS:
            return True

        # Check for destructive patterns
        destructive_patterns = (
            "delete",
            "remove",
            "destroy",
            "drop",
            "truncate",
            "create_issue",
            "create_pull_request",
            "merge_",
            "update_issue",
            "update_pull_request",
        )
        if any(p in tool_name.lower() for p in destructive_patterns):
            return True

        # Check input for destructive operations
        if tool_input:
            # File operations that are destructive
            if "command" in tool_input:
                cmd = str(tool_input["command"]).lower()
                if any(c in cmd for c in ["rm -", "rmdir", "del ", "drop "]):
                    return True

            if "operation" in tool_input:
                op = str(tool_input["operation"]).lower()
                if op in ["delete", "remove", "destroy"]:
                    return True

        return False

    @classmethod
    def is_concurrency_safe(
        cls,
        tool_name: str,
        tool_input: Optional[dict] = None,
    ) -> bool:
        """
        Determine if a tool can run concurrently with others.

        Args:
            tool_name: Name of the tool
            tool_input: Optional tool input for deeper inspection

        Returns:
            True if tool is concurrency-safe, False otherwise
        """
        try:
            # If it's read-only, it's likely concurrency-safe
            if cls.is_read_only(tool_name, tool_input):
                # But check for edge cases in input
                if tool_input:
                    # Some read operations can have destructive side effects
                    # e.g., session operations that modify state
                    if tool_name.startswith("session_"):
                        # Session operations might modify session state
                        if "write" in tool_name.lower():
                            return False
                    # Github operations that might trigger webhooks
                    if tool_name.startswith("github_"):
                        # Check for read-only github operations
                        write_github = {
                            "create",
                            "update",
                            "delete",
                            "push",
                            "merge",
                            "add",
                            "fork",
                            "close",
                        }
                        if any(w in tool_name.lower() for w in write_github):
                            return False
                return True

            # All write operations are non-concurrency-safe
            return False

        except Exception:
            # If classification fails, be conservative - treat as non-concurrency-safe
            return False


# ============================================================================
# Batch Partitioning
# ============================================================================


def partition_tool_calls(tools: list[ToolCall]) -> list[tuple[bool, list[ToolCall]]]:
    """
    Partition tool calls into batches where each batch is either:
    1. Multiple consecutive read-only (concurrency-safe) tools, or
    2. A single non-read-only tool (run serially)

    Args:
        tools: List of tool calls to partition

    Returns:
        List of tuples (is_concurrency_safe, tools_in_batch)
    """
    batches: list[tuple[bool, list[ToolCall]]] = []

    for tool in tools:
        is_safe = tool.is_concurrency_safe

        # If current batch is concurrency-safe and this tool is also safe,
        # append to the current batch
        if batches and batches[-1][0] and is_safe:
            batches[-1][1].append(tool)
        else:
            # Start a new batch
            batches.append((is_safe, [tool]))

    return batches


# ============================================================================
# Concurrent Runner
# ============================================================================


class ConcurrentRunner:
    """
    Runs read-only tools concurrently with configurable max parallelism.
    """

    def __init__(self, max_concurrency: Optional[int] = None):
        """
        Initialize concurrent runner.

        Args:
            max_concurrency: Maximum concurrent executions (default from env or 4)
        """
        self.max_concurrency = max_concurrency or get_max_tool_use_concurrency()
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazily create semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    async def run_tools_concurrently(
        self,
        tools: list[ToolCall],
        executor: Callable[[ToolCall], Coroutine[Any, Any, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Run tools concurrently with max concurrency limit.

        Args:
            tools: List of tool calls to execute
            executor: Async function that executes a single tool call

        Returns:
            List of results in same order as input tools
        """
        if not tools:
            return []

        async def run_with_semaphore(tool: ToolCall) -> dict[str, Any]:
            async with self.semaphore:
                try:
                    return await executor(tool)
                except Exception as e:
                    return {
                        "tool_id": tool.tool_id,
                        "tool_name": tool.tool_name,
                        "error": str(e),
                        "success": False,
                    }

        # Run all tools concurrently with semaphore limiting
        tasks = [run_with_semaphore(tool) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "tool_id": tools[i].tool_id,
                        "tool_name": tools[i].tool_name,
                        "error": str(result),
                        "success": False,
                    }
                )
            else:
                processed_results.append(result)

        return processed_results


# ============================================================================
# Serial Runner
# ============================================================================


class SerialRunner:
    """
    Runs tools serially (one at a time).
    Used for write operations that cannot run concurrently.
    """

    async def run_tools_serially(
        self,
        tools: list[ToolCall],
        executor: Callable[[ToolCall], Coroutine[Any, Any, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Run tools one at a time in order.

        Args:
            tools: List of tool calls to execute
            executor: Async function that executes a single tool call

        Returns:
            List of results in same order as input tools
        """
        results = []

        for tool in tools:
            try:
                result = await executor(tool)
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "tool_id": tool.tool_id,
                        "tool_name": tool.tool_name,
                        "error": str(e),
                        "success": False,
                    }
                )

        return results


# ============================================================================
# Orchestrator
# ============================================================================


class Orchestrator:
    """
    Main orchestrator for concurrency-safe tool execution.

    Partitions tools into batches and executes them appropriately:
    - Read-only batches run concurrently
    - Write batches run serially
    """

    def __init__(self, max_concurrency: Optional[int] = None):
        """
        Initialize orchestrator.

        Args:
            max_concurrency: Maximum concurrent executions for read-only batches
        """
        self.concurrent_runner = ConcurrentRunner(max_concurrency)
        self.serial_runner = SerialRunner()
        self.max_concurrency = max_concurrency or get_max_tool_use_concurrency()

    def create_tool_calls(
        self,
        tool_specs: list[dict[str, Any]],
    ) -> list[ToolCall]:
        """
        Create ToolCall objects from tool specifications.

        Args:
            tool_specs: List of dicts with keys: tool_name, tool_input, tool_id

        Returns:
            List of ToolCall objects with concurrency safety determined
        """
        tool_calls = []

        for spec in tool_specs:
            tool_name = spec.get("tool_name", "")
            tool_input = spec.get("tool_input", {})
            tool_id = spec.get("tool_id", "")

            # Determine concurrency safety
            is_safe = ToolClassifier.is_concurrency_safe(tool_name, tool_input)

            tool_calls.append(
                ToolCall(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_id=tool_id,
                    is_concurrency_safe=is_safe,
                )
            )

        return tool_calls

    async def execute(
        self,
        tool_specs: list[dict[str, Any]],
        executor: Callable[[ToolCall], Coroutine[Any, Any, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Execute tools with proper concurrency handling.

        Args:
            tool_specs: List of tool specifications
            executor: Async function to execute a single tool

        Returns:
            List of results in original order
        """
        # Create tool calls with concurrency metadata
        tool_calls = self.create_tool_calls(tool_specs)

        # Partition into batches
        batches = partition_tool_calls(tool_calls)

        # Execute each batch
        all_results = []

        for is_safe, batch_tools in batches:
            if is_safe:
                # Run concurrent batch
                batch_results = await self.concurrent_runner.run_tools_concurrently(
                    batch_tools, executor
                )
            else:
                # Run serial batch
                batch_results = await self.serial_runner.run_tools_serially(
                    batch_tools, executor
                )

            all_results.extend(batch_results)

        return all_results

    def get_partition_info(
        self, tool_specs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Get partition information without executing.

        Args:
            tool_specs: List of tool specifications

        Returns:
            List of dicts with batch information
        """
        tool_calls = self.create_tool_calls(tool_specs)
        batches = partition_tool_calls(tool_calls)

        info = []
        for is_safe, batch_tools in batches:
            info.append(
                {
                    "is_concurrency_safe": is_safe,
                    "tool_count": len(batch_tools),
                    "tools": [
                        {"name": t.tool_name, "id": t.tool_id} for t in batch_tools
                    ],
                }
            )

        return info


# ============================================================================
# Convenience Functions
# ============================================================================


def create_orchestrator(max_concurrency: Optional[int] = None) -> Orchestrator:
    """Create an Orchestrator instance with optional custom max concurrency."""
    return Orchestrator(max_concurrency)


def is_tool_concurrency_safe(tool_name: str, tool_input: Optional[dict] = None) -> bool:
    """Quick function to check if a tool is concurrency-safe."""
    return ToolClassifier.is_concurrency_safe(tool_name, tool_input)
