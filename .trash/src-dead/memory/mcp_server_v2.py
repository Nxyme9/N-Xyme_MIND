"""src.memory.mcp_server_v2

MCP Tool Server v2 — Uses factory-pattern tool registry.

Wires 14 factory-pattern tools into MCP while maintaining
backward compatibility with the existing mcp_server.py.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional, List, Dict

from fastmcp import FastMCP

# Ensure src is in path
project_root = Path(__file__).parent.parent.parent.resolve()
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import tool registry
from src.orchestration.tool_registry import registry
from src.orchestration.tool_factory import ToolContext

# Import tool CLASSES (not modules)
from src.tools.search_memories import SearchMemoriesTool
from src.tools.create_memory import CreateMemoryTool
from src.tools.get_memory_stats import GetMemoryStatsTool
from src.tools.recall_session import RecallSessionTool
from src.tools.find_context import FindContextTool
from src.tools.semantic_search import SemanticSearchTool
from src.tools.tempr_search import TemprSearchTool
from src.tools.update_memory import UpdateMemoryTool
from src.tools.delete_memory import DeleteMemoryTool
from src.tools.get_learning_stats import GetLearningStatsTool
from src.tools.get_skill_status import GetSkillStatusTool
from src.tools.record_skill_outcome import RecordSkillOutcomeTool
from src.tools.get_learning_patterns import GetLearningPatternsTool
from src.tools.evolve_prompt import EvolvePromptTool

logger = logging.getLogger("mcp-server-v2")

# If registry is empty, fall back to original server
_registry_empty = len(registry) == 0

if _registry_empty:
    logger.warning("Tool registry empty, falling back to mcp_server.py")
    from src.memory.mcp_server import mcp as _fallback_mcp

    mcp = _fallback_mcp
else:
    mcp = FastMCP(
        name="unified-memory-v2",
        version="2.0.0",
        instructions=(
            "Unified Memory MCP Server v2 — Uses factory-pattern tool registry.\n\n"
            "Tools (14 total):\n"
            "- search_memories: Search across all memory sources\n"
            "- create_memory: Create a new memory entry\n"
            "- update_memory: Update an existing memory entry\n"
            "- delete_memory: Delete or archive a memory entry\n"
            "- get_memory_stats: Get statistics about memory sources\n"
            "- recall_session: Recall session context\n"
            "- find_context: Find relevant context for a task\n"
            "- semantic_search: Semantic search using embeddings\n"
            "- tempr_search: TEMPR multi-strategy retrieval\n"
            "- get_learning_stats: Get learning statistics\n"
            "- get_skill_status: Get skill lifecycle status\n"
            "- record_skill_outcome: Record skill execution outcome\n"
            "- get_learning_patterns: Get learned patterns\n"
            "- evolve_prompt: Evolve a prompt using PromptWizard\n"
        ),
    )

    # Instantiate tool classes
    _search_memories = SearchMemoriesTool()
    _create_memory = CreateMemoryTool()
    _get_memory_stats = GetMemoryStatsTool()
    _recall_session = RecallSessionTool()
    _find_context = FindContextTool()
    _semantic_search = SemanticSearchTool()
    _tempr_search = TemprSearchTool()
    _update_memory = UpdateMemoryTool()
    _delete_memory = DeleteMemoryTool()
    _get_learning_stats = GetLearningStatsTool()
    _get_skill_status = GetSkillStatusTool()
    _record_skill_outcome = RecordSkillOutcomeTool()
    _get_learning_patterns = GetLearningPatternsTool()
    _evolve_prompt = EvolvePromptTool()

    # Add delegation interceptor middleware
    from src.middleware.delegation_interceptor import DelegationInterceptor

    mcp.add_middleware(DelegationInterceptor())

    # Register factory tools with explicit signatures
    @mcp.tool(tags={"memory", "read"})
    async def search_memories(
        query: Optional[str] = None,
        limit: Optional[int] = None,
        sources: Optional[List] = None,
    ):
        input_dict = {
            k: v
            for k, v in {"query": query, "limit": limit, "sources": sources}.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _search_memories.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "write"})
    async def create_memory(
        content: Optional[str] = None,
        kind: Optional[str] = None,
        scope: Optional[str] = None,
        tags: Optional[List] = None,
        metadata: Optional[Dict] = None,
    ):
        input_dict = {
            k: v
            for k, v in {
                "content": content,
                "kind": kind,
                "scope": scope,
                "tags": tags,
                "metadata": metadata,
            }.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _create_memory.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def get_memory_stats():
        ctx = ToolContext(working_directory=".")
        return await _get_memory_stats.execute({}, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def recall_session(
        session_id: Optional[str] = None, lines: Optional[int] = None
    ):
        input_dict = {
            k: v
            for k, v in {"session_id": session_id, "lines": lines}.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _recall_session.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def find_context(
        task: Optional[str] = None, context_type: Optional[str] = None
    ):
        input_dict = {
            k: v
            for k, v in {"task": task, "context_type": context_type}.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _find_context.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def semantic_search(query: Optional[str] = None, top_k: Optional[int] = None):
        input_dict = {
            k: v for k, v in {"query": query, "top_k": top_k}.items() if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _semantic_search.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def tempr_search(
        query: Optional[str] = None,
        top_k: Optional[int] = None,
        tier: Optional[str] = None,
        strategies: Optional[List] = None,
    ):
        input_dict = {
            k: v
            for k, v in {
                "query": query,
                "top_k": top_k,
                "tier": tier,
                "strategies": strategies,
            }.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _tempr_search.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "write"})
    async def update_memory(
        memory_id: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List] = None,
        metadata: Optional[Dict] = None,
    ):
        input_dict = {
            k: v
            for k, v in {
                "memory_id": memory_id,
                "content": content,
                "tags": tags,
                "metadata": metadata,
            }.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _update_memory.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "write"})
    async def delete_memory(
        memory_id: Optional[str] = None, hard_delete: Optional[bool] = None
    ):
        input_dict = {
            k: v
            for k, v in {"memory_id": memory_id, "hard_delete": hard_delete}.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _delete_memory.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def get_learning_stats():
        ctx = ToolContext(working_directory=".")
        return await _get_learning_stats.execute({}, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def get_skill_status(skill_name: Optional[str] = None):
        input_dict = {
            k: v for k, v in {"skill_name": skill_name}.items() if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _get_skill_status.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "write"})
    async def record_skill_outcome(
        skill_name: Optional[str] = None,
        success: Optional[bool] = None,
        latency_ms: Optional[float] = None,
        feedback: Optional[str] = None,
    ):
        input_dict = {
            k: v
            for k, v in {
                "skill_name": skill_name,
                "success": success,
                "latency_ms": latency_ms,
                "feedback": feedback,
            }.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _record_skill_outcome.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def get_learning_patterns(
        query: Optional[str] = None, limit: Optional[int] = None
    ):
        input_dict = {
            k: v for k, v in {"query": query, "limit": limit}.items() if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _get_learning_patterns.execute(input_dict, ctx)

    @mcp.tool(tags={"memory", "read"})
    async def evolve_prompt(
        original_prompt: Optional[str] = None,
        task_context: Optional[str] = None,
        iterations: Optional[int] = None,
    ):
        input_dict = {
            k: v
            for k, v in {
                "original_prompt": original_prompt,
                "task_context": task_context,
                "iterations": iterations,
            }.items()
            if v is not None
        }
        ctx = ToolContext(working_directory=".")
        return await _evolve_prompt.execute(input_dict, ctx)

    # Intelligence Tools
    @mcp.tool(tags={"routing", "intelligence"})
    async def route_task(task_description: str) -> dict:
        """Route a task using the unified delegation router with 5-layer fallback chain."""
        try:
            from src.intelligence.unified_router import get_unified_router

            router = get_unified_router()
            result = await router.route_task(task_description)
            return {
                "level": result.level,
                "agent": result.agent,
                "confidence": result.confidence,
                "strategy": result.strategy_used,
                "reason": result.reason,
                "alternatives": result.alternatives,
            }
        except Exception as e:
            logger.error(f"route_task failed: {e}")
            return {
                "error": str(e),
                "level": 2,
                "agent": "hephaestus",
                "strategy": "fallback",
            }

    @mcp.tool(tags={"routing", "learning"})
    async def record_delegation_outcome(
        task_id: str,
        task_description: str,
        level: int,
        agent: str,
        success: bool,
        latency_ms: float = 0,
        tokens_used: int = 0,
    ) -> dict:
        """Record a delegation outcome for learning and routing optimization."""
        try:
            from src.intelligence.unified_router import get_unified_router

            router = get_unified_router()
            await router.record_outcome(
                task_id=task_id,
                task_description=task_description,
                level=level,
                agent=agent,
                success=success,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
            )
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"record_delegation_outcome failed: {e}")
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import argparse
    import logging

    logging.getLogger("fastmcp").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Unified Memory MCP Server v2")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8769, help="SSE port")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="sse", port=args.port, show_banner=False)
    else:
        mcp.run(transport="stdio", show_banner=False)
