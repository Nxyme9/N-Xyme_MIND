"""
Streaming Tool Execution — Async streaming with concurrency control.

Ported from: services/tools/StreamingToolExecutor.ts (Claude Code)
"""

from __future__ import annotations

import asyncio
import logging
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    YIELDED = "yielded"


@dataclass
class TrackedTool:
    """Tool being tracked for execution."""
    id: str
    block: dict
    assistant_message: dict
    status: ToolStatus = ToolStatus.QUEUED
    is_concurrency_safe: bool = False
    promise: Optional[asyncio.Task] = None
    results: list[dict] = field(default_factory=list)
    pending_progress: list[dict] = field(default_factory=list)
    context_modifiers: list[Callable] = field(default_factory=list)


@dataclass
class MessageUpdate:
    """Update from tool execution."""
    message: Optional[dict] = None
    new_context: Optional[dict] = None


class StreamingToolExecutor:
    """Executes tools as they stream with concurrency control."""

    def __init__(
        self,
        tool_definitions: list[dict],
        can_use_tool: Callable[[str], bool],
        tool_use_context: dict,
    ):
        self.tool_definitions = tool_definitions
        self.can_use_tool = can_use_tool
        self.tool_use_context = tool_use_context
        self.tools: list[TrackedTool] = []
        self.has_errored = False
        self.errored_tool_description = ""
        self.discarded = False
        self.progress_available: Optional[asyncio.Event] = None
        self._abort_controller: Optional[asyncio.Event] = None

    def discard(self) -> None:
        """Discard all pending tools when streaming fallback occurs."""
        self.discarded = True

    def add_tool(self, block: dict, assistant_message: dict) -> None:
        """Add a tool to the execution queue."""
        tool_definition = self._find_tool_by_name(block.get("name"))
        if not tool_definition:
            error_tool = TrackedTool(
                id=block.get("id", ""),
                block=block,
                assistant_message=assistant_message,
                status=ToolStatus.COMPLETED,
                is_concurrency_safe=True,
                results=[self._create_error_message(
                    f"No such tool available: {block.get('name')}",
                    block.get("id", ""),
                    assistant_message,
                )],
            )
            self.tools.append(error_tool)
            return

        parsed = self._safe_parse(tool_definition, block.get("input", {}))
        is_concurrency_safe = False
        if parsed:
            try:
                is_concurrency_safe = bool(tool_definition.get("isConcurrencySafe", lambda: False)(parsed))
            except Exception:
                pass

        tracked = TrackedTool(
            id=block.get("id", ""),
            block=block,
            assistant_message=assistant_message,
            status=ToolStatus.QUEUED,
            is_concurrency_safe=is_concurrency_safe,
        )
        self.tools.append(tracked)
        asyncio.create_task(self._process_queue())

    def _find_tool_by_name(self, name: str) -> Optional[dict]:
        """Find tool definition by name."""
        for tool in self.tool_definitions:
            if tool.get("name") == name:
                return tool
        return None

    def _safe_parse(self, definition: dict, data: dict) -> Optional[dict]:
        """Safely parse tool input."""
        if "inputSchema" in definition:
            schema = definition["inputSchema"]
            if hasattr(schema, "safeParse"):
                result = schema.safeParse(data)
                if result.success:
                    return result.data
        return data

    def _can_execute_tool(self, is_concurrency_safe: bool) -> bool:
        """Check if tool can execute based on concurrency state."""
        executing = [t for t in self.tools if t.status == ToolStatus.EXECUTING]
        if not executing:
            return True
        return is_concurrency_safe and all(t.is_concurrency_safe for t in executing)

    async def _process_queue(self) -> None:
        """Process queue starting tools when concurrency allows."""
        for tool in self.tools:
            if tool.status != ToolStatus.QUEUED:
                continue

            if self._can_execute_tool(tool.is_concurrency_safe):
                await self._execute_tool(tool)
            elif not tool.is_concurrency_safe:
                break

    def _get_abort_reason(
        self,
        tool: TrackedTool,
    ) -> Optional[str]:
        """Determine why tool should be cancelled."""
        if self.discarded:
            return "streaming_fallback"
        if self.has_errored:
            return "sibling_error"
        if self._abort_controller and self._abort_controller.is_set():
            return "user_interrupted"
        return None

    def _get_tool_description(self, tool: TrackedTool) -> str:
        """Get tool description for error messages."""
        block = tool.block
        inp = block.get("input", {})
        summary = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
        truncated = (summary[:40] + "…") if len(summary) > 40 else summary
        return f"{block.get('name')}({truncated})"

    async def _execute_tool(self, tool: TrackedTool) -> None:
        """Execute a tool and collect results."""
        tool.status = ToolStatus.EXECUTING

        messages: list[dict] = []
        context_modifiers: list[Callable] = []

        abort_reason = self._get_abort_reason(tool)
        if abort_reason:
            messages.append(self._create_synthetic_error(
                tool.id,
                abort_reason,
                tool.assistant_message,
            ))
            tool.results = messages
            tool.status = ToolStatus.COMPLETED
            return

        try:
            result = await self._run_tool_use(
                tool.block,
                tool.assistant_message,
                self.tool_use_context,
            )

            async for update in result:
                abort_reason = self._get_abort_reason(tool)
                if abort_reason:
                    messages.append(self._create_synthetic_error(
                        tool.id,
                        abort_reason,
                        tool.assistant_message,
                    ))
                    break

                if update.message:
                    messages.append(update.message)

                if update.new_context:
                    context_modifiers.append(lambda ctx: update.new_context)

        except Exception as e:
            self.has_errored = True
            self.errored_tool_description = self._get_tool_description(tool)
            messages.append(self._create_synthetic_error(
                tool.id,
                "sibling_error",
                tool.assistant_message,
            ))
            logger.error(f"Tool execution error: {e}")

        tool.results = messages
        tool.context_modifiers = context_modifiers
        tool.status = ToolStatus.COMPLETED

    async def _run_tool_use(
        self,
        block: dict,
        assistant_message: dict,
        context: dict,
    ) -> AsyncGenerator[MessageUpdate, None]:
        """Run tool and yield updates."""
        tool_name = block.get("name")
        tool_input = block.get("input", {})

        if not self.can_use_tool(tool_name):
            yield MessageUpdate(
                message=self._create_error_message(
                    f"Tool {tool_name} not available",
                    block.get("id", ""),
                    assistant_message,
                )
            )
            return

        try:
            executor = context.get("executor")
            if executor and hasattr(executor, "execute"):
                result = await executor.execute(tool_name, tool_input, context)
                yield MessageUpdate(message=result)
        except Exception as e:
            yield MessageUpdate(
                message=self._create_error_message(
                    str(e),
                    block.get("id", ""),
                    assistant_message,
                )
            )

    def _create_error_message(
        self,
        content: str,
        tool_use_id: str,
        assistant_message: dict,
    ) -> dict:
        """Create error message."""
        return {
            "type": "user",
            "message": {
                "type": "message",
                "content": [
                    {
                        "type": "tool_result",
                        "content": f"<tool_use_error>{content}</tool_use_error>",
                        "is_error": True,
                        "tool_use_id": tool_use_id,
                    }
                ],
            },
            "tool_use_result": content,
            "source_tool_assistant_uuid": assistant_message.get("uuid"),
        }

    def _create_synthetic_error_message(
        self,
        tool_use_id: str,
        reason: str,
        assistant_message: dict,
    ) -> dict:
        """Create synthetic error for abort cases."""
        reason_messages = {
            "sibling_error": "Cancelled: parallel tool call errored",
            "user_interrupted": "User rejected tool use",
            "streaming_fallback": "Streaming fallback - tool execution discarded",
        }
        content = reason_messages.get(reason, "Tool execution cancelled")
        return self._create_error_message(content, tool_use_id, assistant_message)


async def create_streaming_executor(
    tool_definitions: list[dict],
    can_use_tool: Callable[[str], bool],
    tool_use_context: dict,
) -> StreamingToolExecutor:
    """Create streaming executor (CLI entry point)."""
    return StreamingToolExecutor(tool_definitions, can_use_tool, tool_use_context)


__all__ = [
    "ToolStatus",
    "TrackedTool",
    "MessageUpdate",
    "StreamingToolExecutor",
    "create_streaming_executor",
]