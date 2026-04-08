#!/usr/bin/env python3
"""Local LLM Integration - Wires local_llm to intelligent_router.

This module integrates:
- packages.local_llm (Ollama tool calling)
- packages.intelligent_router_mcp (model selection)
- packages.local_llm.mcp_tool_loader (MCP tools)

Provides a unified interface for local LLM with tool calling.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from packages.local_llm.ollama_client import LocalLLM
from packages.local_llm.wrapper import LocalLLMWrapper, MCPToolExecutor
from packages.local_llm.mcp_tool_loader import MCPToolLoader, get_tool_loader

logger = logging.getLogger("local_llm_integration")

# Try to import intelligent_router
try:
    from packages.intelligent_router_mcp import Router

    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    logger.warning("intelligent_router not available, using default model")


class LocalLLMIntegration:
    """Full integration: local LLM + intelligent routing + MCP tools.

    Provides:
    - Automatic model selection via intelligent_router
    - MCP tool loading and execution
    - Full 2-pass pipeline: model → tools → results
    """

    DEFAULT_MODEL = "qwen2.5-coder:7b"
    FALLBACK_MODELS = ["qwen2.5-coder:7b", "llama3.2:3b"]

    def __init__(
        self,
        config_path: str = "opencode.json",
        auto_select_model: bool = True,
        default_model: Optional[str] = None,
    ):
        self.config_path = config_path
        self.auto_select_model = auto_select_model

        # Model selection
        self.router = None
        if ROUTER_AVAILABLE and auto_select_model:
            try:
                self.router = Router()
                logger.info("Intelligent router initialized")
            except Exception as e:
                logger.warning(f"Failed to init router: {e}, using default")

        # Default model
        self.current_model = default_model or self.DEFAULT_MODEL

        # MCP tool loader
        self.tool_loader = get_tool_loader(config_path)

        # Local LLM wrapper with tool execution
        self.wrapper = LocalLLMWrapper(
            model=self.current_model,
            execute_mcp=True,
        )

        # Register MCP tool handlers
        self._register_handlers()

        logger.info(
            f"LocalLLMIntegration initialized: model={self.current_model}, "
            f"tools={len(self.tool_loader.list_tools())}"
        )

    def _register_handlers(self) -> None:
        """Register MCP tool handlers with the executor."""
        # Register memory tools
        self.wrapper.executor.register_handler(
            "memory_search", self._handle_memory_search
        )
        self.wrapper.executor.register_handler(
            "memory_write", self._handle_memory_write
        )
        self.wrapper.executor.register_handler(
            "athena_smart_search", self._handle_athena_search
        )

        # Register filesystem tools
        self.wrapper.executor.register_handler("read_file", self._handle_read_file)
        self.wrapper.executor.register_handler("write_file", self._handle_write_file)
        self.wrapper.executor.register_handler(
            "list_directory", self._handle_list_directory
        )

        # Register git tools
        self.wrapper.executor.register_handler("git_status", self._handle_git_status)
        self.wrapper.executor.register_handler("git_log", self._handle_git_log)
        self.wrapper.executor.register_handler("git_diff", self._handle_git_diff)

        # Register GitHub tools
        self.wrapper.executor.register_handler(
            "github_search_repositories", self._handle_github_search_repos
        )
        self.wrapper.executor.register_handler(
            "github_list_issues", self._handle_github_list_issues
        )

        # Register fetch tools
        self.wrapper.executor.register_handler("fetch_url", self._handle_fetch_url)

        # Register context7 tools
        self.wrapper.executor.register_handler(
            "context7_query_docs", self._handle_context7_docs
        )

        # Register sequential thinking
        self.wrapper.executor.register_handler(
            "sequential_thinking", self._handle_sequential_thinking
        )

        # Register athena context tools
        self.wrapper.executor.register_handler(
            "get_active_context", self._handle_get_active_context
        )
        self.wrapper.executor.register_handler(
            "get_user_context", self._handle_get_user_context
        )

        # Register learning engine tools
        self.wrapper.executor.register_handler("route_task", self._handle_route_task)
        self.wrapper.executor.register_handler(
            "record_outcome", self._handle_record_outcome
        )

        # Register quality gates
        self.wrapper.executor.register_handler(
            "run_typecheck", self._handle_run_typecheck
        )
        self.wrapper.executor.register_handler("run_lint", self._handle_run_lint)

        # Register playwright tools
        self.wrapper.executor.register_handler(
            "browser_navigate", self._handle_browser_navigate
        )
        self.wrapper.executor.register_handler(
            "browser_click", self._handle_browser_click
        )

        # Register sqlite
        self.wrapper.executor.register_handler(
            "sqlite_query", self._handle_sqlite_query
        )

        logger.info("Registered all MCP tool handlers")

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    async def _handle_memory_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_search tool."""
        try:
            from unified_memory import search_memories

            result = search_memories(
                query=args.get("query", ""),
                limit=args.get("limit", 10),
                rerank=args.get("rerank", False),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "unified-memory MCP not connected"}

    async def _handle_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read_file tool."""
        path = args.get("path", "")
        if not path:
            return {"error": "path is required"}

        try:
            with open(path) as f:
                content = f.read()
                # Truncate for display
                if len(content) > 5000:
                    content = content[:5000] + "\n... [truncated]"
                return {"content": content, "path": path}
        except Exception as e:
            return {"error": str(e), "path": path}

    async def _handle_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write_file tool."""
        path = args.get("path", "")
        content = args.get("content", "")

        if not path:
            return {"error": "path is required"}

        try:
            with open(path, "w") as f:
                f.write(content)
            return {"success": True, "path": path, "bytes_written": len(content)}
        except Exception as e:
            return {"error": str(e), "path": path}

    async def _handle_list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_directory tool."""
        import os

        path = args.get("path", ".")

        try:
            entries = os.listdir(path)
            return {"entries": entries, "path": path}
        except Exception as e:
            return {"error": str(e), "path": path}

    async def _handle_git_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle git_status tool."""
        import subprocess

        repo_path = args.get("repo_path", ".")

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            return {
                "status": result.stdout or "clean",
                "repo_path": repo_path,
            }
        except Exception as e:
            return {"error": str(e), "repo_path": repo_path}

    async def _handle_route_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle route_task tool."""
        if not self.router:
            return {"error": "Router not available", "model": self.current_model}

        try:
            task = args.get("task_description", "")
            route = self.router.select_route(task)
            return route
        except Exception as e:
            return {"error": str(e), "model": self.current_model}

    # =========================================================================
    # Additional Tool Handlers (Phase 2.3)
    # =========================================================================

    async def _handle_memory_write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_write tool."""
        try:
            from unified_memory import memory_write

            result = memory_write(
                content=args.get("content", ""),
                kind=args.get("kind", "episodic"),
                scope=args.get("scope", "global"),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "unified-memory MCP not connected"}

    async def _handle_athena_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle athena_smart_search tool - now uses unified-memory."""
        try:
            # Use unified-memory instead of deprecated Athena
            from packages.memory_core.router import MemoryRouter, UnifiedMemoryQuery
            
            router = MemoryRouter()
            query = UnifiedMemoryQuery(
                query=args.get("query", ""),
                max_results_per_source=args.get("limit", 10)
            )
            results = router.search(query)
            
            return {
                "results": [
                    {
                        "source": r.source,
                        "content": r.content[:500] if isinstance(r.content, str) else str(r.content)[:500],
                        "score": r.relevance_score
                    }
                    for r in results.results
                ],
                "total": results.total_results,
                "sources": results.sources_queried
            }
        except Exception as e:
            return {"error": str(e), "note": "unified-memory search failed"}

    async def _handle_git_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle git_log tool."""
        import subprocess

        repo_path = args.get("repo_path", ".")
        max_count = args.get("max_count", 10)

        try:
            result = subprocess.run(
                ["git", "log", f"-n{max_count}", "--oneline"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            return {"log": result.stdout, "repo_path": repo_path}
        except Exception as e:
            return {"error": str(e), "repo_path": repo_path}

    async def _handle_git_diff(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle git_diff tool."""
        import subprocess

        repo_path = args.get("repo_path", ".")
        target = args.get("target", "HEAD")

        try:
            result = subprocess.run(
                ["git", "diff", target],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            return {"diff": result.stdout, "repo_path": repo_path, "target": target}
        except Exception as e:
            return {"error": str(e), "repo_path": repo_path}

    async def _handle_github_search_repos(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle github_search_repositories tool."""
        try:
            from github import search_repositories

            result = search_repositories(
                query=args.get("query", ""),
                minimal_output=args.get("minimal_output", True),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "github MCP not connected"}

    async def _handle_github_list_issues(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle github_list_issues tool."""
        try:
            from github import list_issues

            result = list_issues(
                owner=args.get("owner", ""),
                repo=args.get("repo", ""),
                state=args.get("state", "OPEN"),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "github MCP not connected"}

    async def _handle_fetch_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fetch_url tool."""
        try:
            from fetch import fetch_markdown

            result = fetch_markdown(
                url=args.get("url", ""),
                max_length=args.get("max_length", 5000),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "fetch MCP not connected"}

    async def _handle_context7_docs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context7_query_docs tool."""
        try:
            from context7 import query_docs

            result = query_docs(
                library_id=args.get("library_id", ""),
                query=args.get("query", ""),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "context7 MCP not connected"}

    async def _handle_sequential_thinking(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sequential_thinking tool."""
        try:
            from sequential_thinking import sequential_thinking

            result = sequential_thinking(
                thought=args.get("thought", ""),
                nextThoughtNeeded=args.get("nextThoughtNeeded", False),
                thoughtNumber=args.get("thoughtNumber", 1),
                totalThoughts=args.get("totalThoughts", 1),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "sequential-thinking MCP not connected"}

    async def _handle_get_active_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_active_context tool."""
        try:
            from athena_context import get_active_context

            result = get_active_context()
            return result
        except Exception as e:
            return {"error": str(e), "note": "athena-context MCP not connected"}

    async def _handle_get_user_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_user_context tool."""
        try:
            from athena_context import get_user_context

            result = get_user_context()
            return result
        except Exception as e:
            return {"error": str(e), "note": "athena-context MCP not connected"}

    async def _handle_record_outcome(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle record_outcome tool."""
        try:
            from learning_engine import record_delegation_outcome

            result = record_delegation_outcome(
                task_description=args.get("task", ""),
                agent=args.get("agent", ""),
                success=args.get("success", False),
                latency_ms=args.get("latency_ms", 0),
                tokens_used=args.get("tokens_used", 0),
                level=args.get("level", 3),
            )
            return result
        except Exception as e:
            return {"error": str(e), "note": "learning-engine MCP not connected"}

    async def _handle_run_typecheck(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_typecheck tool."""
        import subprocess
        import os

        try:
            # Find project root
            project_root = os.getcwd()
            result = subprocess.run(
                ["python3", "-m", "py_compile"]
                + [f for f in os.listdir(project_root) if f.endswith(".py")][:5],
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            return {"success": result.returncode == 0, "output": result.stdout}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_run_lint(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_lint tool."""
        import subprocess
        import os

        try:
            project_root = os.getcwd()
            result = subprocess.run(
                ["python3", "-m", "pyflakes", project_root],
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            return {"success": result.returncode == 0, "output": result.stdout}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_browser_navigate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browser_navigate tool."""
        return {
            "note": "Playwright browser requires MCP connection",
            "url": args.get("url", ""),
            "error": "browser MCP not connected - use playwright skill for browser automation",
        }

    async def _handle_browser_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browser_click tool."""
        return {
            "note": "Playwright browser requires MCP connection",
            "ref": args.get("ref", ""),
            "error": "browser MCP not connected - use playwright skill for browser automation",
        }

    async def _handle_sqlite_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sqlite_query tool."""
        import sqlite3

        sql = args.get("sql", "")
        db_path = args.get("db_path", ":memory:")

        if not sql.strip().upper().startswith("SELECT"):
            return {"error": "Only SELECT queries allowed (read-only)"}

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.close()
            return {
                "results": results,
                "columns": [desc[0] for desc in cursor.description]
                if cursor.description
                else [],
            }
        except Exception as e:
            return {"error": str(e), "sql": sql}

    # =========================================================================
    # Model Selection
    # =========================================================================

    def select_model(self, task: str, agent_type: str = "") -> str:
        """Select best model for task using intelligent_router."""
        if not self.router:
            return self.current_model

        try:
            route = self.router.select_route(task, agent_type=agent_type)
            model = route.get("model")
            if model:
                # Convert to Ollama format if needed
                if "/" in model:
                    model = model.split("/")[-1]
                self.current_model = model
                return model
        except Exception as e:
            logger.warning(f"Model selection failed: {e}")

        return self.current_model

    def set_model(self, model: str) -> None:
        """Set the model to use."""
        self.current_model = model
        self.wrapper.llm.model = model
        logger.info(f"Model set to: {model}")

    # =========================================================================
    # Main Execution
    # =========================================================================

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        auto_route: bool = False,
        agent_type: str = "",
    ) -> Dict[str, Any]:
        """Chat with optional tool calling.

        Args:
            messages: Chat history
            tools: Optional tool definitions (auto-loaded if not provided)
            auto_route: Automatically select model based on task
            agent_type: Agent type for model selection

        Returns:
            Result dict with response and optionally executed tools
        """
        # Auto-route model if enabled
        if auto_route and messages:
            last_message = messages[-1].get("content", "")
            selected = self.select_model(last_message, agent_type)
            if selected != self.wrapper.llm.model:
                self.set_model(selected)

        # Auto-load tools if not provided
        if tools is None:
            tools = self.tool_loader.get_tools_openai_format()

        # Execute with tools
        result = await self.wrapper.execute_with_tools(messages, tools)
        return result

    async def chat_simple(
        self,
        message: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Simple single-message chat.

        Args:
            message: User message
            tools: Optional tool definitions. If None, uses NO tools (not auto-loaded).
                   Pass empty list [] to explicitly request no tools.
        """
        # Fix: Pass empty list instead of None to avoid auto-loading all MCP tools
        effective_tools = [] if tools is None else tools
        return await self.chat(
            [{"role": "user", "content": message}],
            tools=effective_tools,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "model": self.current_model,
            "router_available": self.router is not None,
            "tools_available": len(self.tool_loader.list_tools()),
            "mcp_servers": list(self.tool_loader.mcp_servers.keys()),
        }


# ============================================================================
# Convenience Functions
# ============================================================================


async def chat_with_tools(
    message: str,
    model: Optional[str] = None,
    auto_route: bool = False,
) -> Dict[str, Any]:
    """Convenience function for one-shot tool execution.

    Args:
        message: User message
        model: Optional model to use (auto-selected if auto_route=True)
        auto_route: Use intelligent router for model selection

    Returns:
        Result dict with response
    """
    integration = LocalLLMIntegration(
        auto_select_model=auto_route,
        default_model=model,
    )
    return await integration.chat_simple(message)


# ============================================================================
# Test
# ============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    async def test():
        print("=== Local LLM Integration Test ===\n")

        # Create integration
        integration = LocalLLMIntegration()
        status = integration.get_status()
        print(f"Status: {json.dumps(status, indent=2)}\n")

        # Test 1: Simple chat without tools
        print("=== Test 1: Simple Chat ===")
        result = await integration.chat_simple("Hello, what model are you using?")
        print(f"Response: {result.get('content', '')[:200]}...\n")

        # Test 2: Tool call with memory_search
        print("=== Test 2: Tool Call (memory_search) ===")
        tools = integration.tool_loader.get_tools_openai_format()
        # Filter to just memory_search for test
        memory_tools = [
            t for t in tools if t.get("function", {}).get("name") == "memory_search"
        ]

        result = await integration.chat(
            [{"role": "user", "content": "Search memory for 'test'"}],
            tools=memory_tools if memory_tools else None,
        )
        print(f"Result: {json.dumps(result, indent=2)}\n")

        # Test 3: Auto-route model
        print("=== Test 3: Auto-Route Model ===")
        selected = integration.select_model(
            "Write a function to sort a list", agent_type="hephaestus"
        )
        print(f"Selected model: {selected}")

    asyncio.run(test())
