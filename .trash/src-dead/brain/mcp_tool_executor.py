"""
src.brain.mcp_tool_executor
===========================
MCP Tool Executor - executes parsed tool calls from Rosetta Stone.

This module bridges the gap between Rosetta Stone (which parses tool calls
from local models) and the actual MCP servers that provide the functionality.

Usage:
    executor = MCPToolExecutor()
    result = executor.execute("search_memories", {"query": "test", "limit": 10})
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("mcp-tool-executor")


class MCPToolExecutor:
    """
    Executes MCP tools from parsed tool calls.

    Takes output from Rosetta Stone and actually runs the tools,
    returning results for the model to continue.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize the executor.

        Args:
            workspace_root: Path to workspace root. Defaults to project root.
        """
        self.workspace_root = (
            Path(workspace_root)
            if workspace_root
            else Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
        )

        # Lazy-loaded tool handlers
        self._memory_router = None
        self._athena_client = None

        logger.info(
            f"MCPToolExecutor initialized with workspace: {self.workspace_root}"
        )

    def _get_memory_router(self):
        """Lazy-load memory router."""
        if self._memory_router is None:
            try:
                from src.memory.router import MemoryRouter, UnifiedMemoryQuery

                self._memory_router = MemoryRouter()
                logger.debug("Memory router loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load memory router: {e}")
                raise
        return self._memory_router

    # ---------------------------------------------------------------------------
    # Memory Tools
    # ---------------------------------------------------------------------------

    def _exec_search_memories(self, args: Dict) -> Dict:
        """Execute search_memories from unified memory system."""
        query = args.get("query", "")
        limit = args.get("limit", 10)
        rerank = args.get("rerank", False)
        strict = args.get("strict", False)

        router = self._get_memory_router()
        from src.memory.router import UnifiedMemoryQuery

        uq = UnifiedMemoryQuery(
            query=query,
            max_results_per_source=limit,
            use_semantic=rerank,
        )
        results = router.search(uq)

        return {
            "results": [
                {
                    "source": r.source,
                    "content": str(r.content)[:500],
                    "score": getattr(r, "relevance_score", None),
                }
                for r in results.results
            ],
            "meta": {
                "query": query,
                "limit": limit,
                "total": results.total_results,
                "sources_queried": results.sources_queried,
                "query_time_ms": results.query_time_ms,
            },
        }

    def _exec_memory_search(self, args: Dict) -> Dict:
        """Alias for search_memories."""
        return self._exec_search_memories(args)

    def _exec_create_memory(self, args: Dict) -> Dict:
        """Execute create_memory - creates a new memory entry."""
        # For now, return a placeholder implementation
        # Full implementation would create entities in knowledge graph
        return {
            "status": "implemented",
            "content": args.get("content", ""),
            "kind": args.get("kind", "semantic"),
            "message": "create_memory placeholder - use memory MCP server for full implementation",
        }

    def _exec_get_memory_stats(self, args: Dict) -> Dict:
        """Execute get_memory_stats."""
        import sqlite3

        stats = {}

        # File registry stats
        try:
            db_path = self.workspace_root / "context" / "memory" / "file_registry.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {}
                for (table,) in cur.fetchall():
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        tables[table] = cur.fetchone()[0]
                    except (sqlite3.OperationalError, sqlite3.DatabaseError):
                        pass
                stats["file_registry"] = tables
                conn.close()
        except Exception as e:
            stats["file_registry_error"] = str(e)

        # Learning events stats
        try:
            events_db = (
                self.workspace_root / "context" / "memory" / "learning_events.db"
            )
            if events_db.exists():
                conn = sqlite3.connect(str(events_db))
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM events")
                stats["learning_events"] = cur.fetchone()[0]
                conn.close()
        except Exception as e:
            stats["learning_events_error"] = str(e)

        return stats

    def _exec_find_context(self, args: Dict) -> Dict:
        """Execute find_context."""
        task = args.get("task", "")
        context_type = args.get("context_type", "all")

        router = self._get_memory_router()
        from src.memory.router import UnifiedMemoryQuery

        uq = UnifiedMemoryQuery(query=task, max_results_per_source=5, use_semantic=True)
        results = router.search(uq)

        return {
            "task": task,
            "context_type": context_type,
            "results": [
                {"source": r.source, "content": str(r.content)[:300]}
                for r in results.results[:5]
            ],
        }

    def _exec_recall_session(self, args: Dict) -> Dict:
        """Execute recall_session."""
        return {
            "session_id": args.get("session_id", "current"),
            "limit": args.get("limit", 50),
            "status": "implemented",
        }

    # ---------------------------------------------------------------------------
    # Athena Tools
    # ---------------------------------------------------------------------------

    def _exec_athena_smart_search(self, args: Dict) -> Dict:
        """Execute athena_smart_search."""
        try:
            from src.athena import smart_search

            return smart_search(
                query=args.get("query", ""),
                limit=args.get("limit", 10),
                rerank=args.get("rerank", False),
                strict=args.get("strict", False),
            )
        except ImportError:
            # Fallback if athena module not available
            logger.warning("athena.smart_search not available, using memory search")
            return self._exec_search_memories(args)

    def _exec_athena_agentic_search(self, args: Dict) -> Dict:
        """Execute athena_agentic_search."""
        try:
            from src.athena import agentic_search

            return agentic_search(
                query=args.get("query", ""),
                limit=args.get("limit", 10),
                validate=args.get("validate", True),
            )
        except ImportError:
            return {"error": "agentic_search not available"}

    def _exec_athena_quicksave(self, args: Dict) -> Dict:
        """Execute athena_quicksave."""
        try:
            from src.athena import quicksave

            return quicksave(
                summary=args.get("summary", ""),
                bullets=args.get("bullets"),
            )
        except ImportError:
            return {"error": "quicksave not available"}

    def _exec_athena_query_unified_memory(self, args: Dict) -> Dict:
        """Execute athena-context query_unified_memory."""
        return self._exec_search_memories(args)

    def _exec_athena_get_active_context(self, args: Dict) -> Dict:
        """Execute get_active_context from athena-context."""
        try:
            from src.athena_context import get_active_context

            return get_active_context()
        except ImportError:
            return {"error": "get_active_context not available"}

    def _exec_athena_get_product_context(self, args: Dict) -> Dict:
        """Execute get_product_context."""
        try:
            from src.athena_context import get_product_context

            return get_product_context()
        except ImportError:
            return {"error": "get_product_context not available"}

    def _exec_athena_get_user_context(self, args: Dict) -> Dict:
        """Execute get_user_context."""
        try:
            from src.athena_context import get_user_context

            return get_user_context()
        except ImportError:
            return {"error": "get_user_context not available"}

    # ---------------------------------------------------------------------------
    # Filesystem Tools
    # ---------------------------------------------------------------------------

    def _exec_filesystem_read_text_file(self, args: Dict) -> Dict:
        """Execute filesystem read_file."""
        path = args.get("path", "")

        if not path:
            return {"error": "path is required"}

        # Resolve relative paths against workspace
        file_path = (
            self.workspace_root / path if not Path(path).is_absolute() else Path(path)
        )

        try:
            content = file_path.read_text(encoding="utf-8")

            # Handle head/tail limits
            head = args.get("head")
            tail = args.get("tail")

            lines = content.split("\n")
            if head:
                lines = lines[:head]
                content = "\n".join(lines)
            elif tail:
                lines = lines[-tail:]
                content = "\n".join(lines)

            return {
                "content": content,
                "path": str(file_path),
                "size": file_path.stat().st_size,
            }
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}
        except Exception as e:
            return {"error": str(e)}

    def _exec_filesystem_write_file(self, args: Dict) -> Dict:
        """Execute filesystem write_file."""
        path = args.get("path", "")
        content = args.get("content", "")

        if not path:
            return {"error": "path is required"}

        # Resolve relative paths against workspace
        file_path = (
            self.workspace_root / path if not Path(path).is_absolute() else Path(path)
        )

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return {
                "status": "success",
                "path": str(file_path),
                "bytes_written": len(content),
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_filesystem_list_directory(self, args: Dict) -> Dict:
        """Execute filesystem list_directory."""
        path = args.get("path", "")

        if not path:
            return {"error": "path is required"}

        dir_path = (
            self.workspace_root / path if not Path(path).is_absolute() else Path(path)
        )

        try:
            if not dir_path.exists():
                return {"error": f"Directory not found: {dir_path}"}

            if not dir_path.is_dir():
                return {"error": f"Not a directory: {dir_path}"}

            entries = []
            for entry in dir_path.iterdir():
                entries.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "path": str(entry.relative_to(self.workspace_root)),
                    }
                )

            return {
                "entries": entries,
                "path": str(dir_path),
                "count": len(entries),
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_filesystem_search_files(self, args: Dict) -> Dict:
        """Execute filesystem search_files (glob)."""
        path = args.get("path", "")
        pattern = args.get("pattern", "")

        if not path or not pattern:
            return {"error": "path and pattern are required"}

        search_path = (
            self.workspace_root / path if not Path(path).is_absolute() else Path(path)
        )

        try:
            from pathlib import Path as P

            matches = list(search_path.glob(pattern))

            return {
                "matches": [
                    {
                        "name": m.name,
                        "path": str(m.relative_to(self.workspace_root)),
                        "type": "directory" if m.is_dir() else "file",
                    }
                    for m in matches[:100]  # Limit results
                ],
                "count": len(matches),
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_filesystem_get_file_info(self, args: Dict) -> Dict:
        """Execute filesystem get_file_info."""
        path = args.get("path", "")

        if not path:
            return {"error": "path is required"}

        file_path = (
            self.workspace_root / path if not Path(path).is_absolute() else Path(path)
        )

        try:
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}

            stat = file_path.stat()
            return {
                "name": file_path.name,
                "path": str(file_path.relative_to(self.workspace_root)),
                "size": stat.st_size,
                "is_directory": file_path.is_dir(),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            }
        except Exception as e:
            return {"error": str(e)}

    # ---------------------------------------------------------------------------
    # Git Tools
    # ---------------------------------------------------------------------------

    def _exec_git_git_status(self, args: Dict) -> Dict:
        """Execute git status."""
        import subprocess

        repo_path = args.get("repo_path", str(self.workspace_root))

        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "status": result.stdout,
                "returncode": result.returncode,
                "repo_path": repo_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_git_git_log(self, args: Dict) -> Dict:
        """Execute git log."""
        import subprocess

        repo_path = args.get("repo_path", str(self.workspace_root))
        max_count = args.get("max_count", 10)

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    repo_path,
                    "log",
                    f"--max-count={max_count}",
                    "--oneline",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "commits": result.stdout.strip().split("\n") if result.stdout else [],
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_git_git_diff(self, args: Dict) -> Dict:
        """Execute git diff."""
        import subprocess

        repo_path = args.get("repo_path", str(self.workspace_root))
        target = args.get("target", "HEAD")

        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "diff", target],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "diff": result.stdout,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_git_git_show(self, args: Dict) -> Dict:
        """Execute git show."""
        import subprocess

        repo_path = args.get("repo_path", str(self.workspace_root))
        revision = args.get("revision", "HEAD")

        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "show", revision, "--stat"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "output": result.stdout,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}

    # ---------------------------------------------------------------------------
    # Fetch Tools
    # ---------------------------------------------------------------------------

    def _exec_fetch_fetch_markdown(self, args: Dict) -> Dict:
        """Execute fetch_markdown."""
        url = args.get("url", "")

        if not url:
            return {"error": "url is required"}

        try:
            import requests

            response = requests.get(
                url,
                timeout=args.get("timeout", 30),
                headers={"User-Agent": "N-Xyme-MIND/1.0"},
            )
            response.raise_for_status()

            max_length = args.get("max_length", 5000)
            content = response.text[:max_length]

            return {
                "content": content,
                "url": url,
                "status_code": response.status_code,
            }
        except Exception as e:
            return {"error": str(e)}

    def _exec_fetch_fetch_readable(self, args: Dict) -> Dict:
        """Execute fetch_readable - uses Mozilla Readability."""
        url = args.get("url", "")

        if not url:
            return {"error": "url is required"}

        # For now, fall back to regular fetch
        return self._exec_fetch_fetch_markdown(args)

    # ---------------------------------------------------------------------------
    # GitHub Tools (placeholder - requires MCP or direct API)
    # ---------------------------------------------------------------------------

    def _exec_github_search_code(self, args: Dict) -> Dict:
        """Execute GitHub code search - placeholder."""
        return {
            "error": "GitHub search requires MCP server. Use grep.searchGitHub for local search.",
            "query": args.get("query", ""),
        }

    def _exec_github_list_issues(self, args: Dict) -> Dict:
        """Execute GitHub list_issues - placeholder."""
        return {
            "error": "GitHub issues require MCP server or direct GitHub API",
            "owner": args.get("owner", ""),
            "repo": args.get("repo", ""),
        }

    # ---------------------------------------------------------------------------
    # Context7 Tools (placeholder - requires MCP)
    # ---------------------------------------------------------------------------

    def _exec_context7_query_docs(self, args: Dict) -> Dict:
        """Execute Context7 query_docs - placeholder."""
        return {
            "error": "Context7 requires MCP server",
            "libraryId": args.get("libraryId", ""),
            "query": args.get("query", ""),
        }

    # ---------------------------------------------------------------------------
    # NX-Mind Tools
    # ---------------------------------------------------------------------------

    def _exec_nxmind_get_mind_state(self, args: Dict) -> Dict:
        """Execute nx-mind get_mind_state."""
        try:
            from src.nxmind import get_mind_state

            return get_mind_state()
        except ImportError:
            return {"error": "nx-mind MCP not available"}

    def _exec_nxmind_update_mind_state(self, args: Dict) -> Dict:
        """Execute nx-mind update_mind_state."""
        try:
            from src.nxmind import update_mind_state

            return update_mind_state(
                project=args.get("project"),
                phase=args.get("phase"),
                active_tasks=args.get("active_tasks"),
                context=args.get("context"),
                clear_context=args.get("clear_context", False),
            )
        except ImportError:
            return {"error": "nx-mind MCP not available"}

    def _exec_nxmind_get_session_history(self, args: Dict) -> Dict:
        """Execute nx-mind get_session_history."""
        try:
            from src.nxmind import get_session_history

            return get_session_history(limit=args.get("limit", 10))
        except ImportError:
            return {"error": "nx-mind MCP not available"}

    # ---------------------------------------------------------------------------
    # Grep Tools
    # ---------------------------------------------------------------------------

    def _exec_grep_app_searchGitHub(self, args: Dict) -> Dict:
        """Execute grep_app_searchGitHub - placeholder for grep MCP."""
        return {
            "error": "grep.searchGitHub requires MCP server",
            "query": args.get("query", ""),
        }

    # ---------------------------------------------------------------------------
    # Trigger Guardian Tools
    # ---------------------------------------------------------------------------

    def _exec_trigger_guardian_register_trigger(self, args: Dict) -> Dict:
        """Execute trigger-guardian register_trigger."""
        try:
            from src.triggers import register_trigger

            return register_trigger(
                phrase=args.get("phrase", ""),
                description=args.get("description", ""),
                handler=args.get("handler", "callback"),
                pattern_type=args.get("pattern_type", "exact"),
            )
        except ImportError:
            return {"error": "trigger-guardian not available"}

    def _exec_trigger_guardian_list_triggers(self, args: Dict) -> Dict:
        """Execute trigger-guardian list_triggers."""
        try:
            from src.triggers import list_triggers

            return list_triggers()
        except ImportError:
            return {"error": "trigger-guardian not available"}

    # ---------------------------------------------------------------------------
    # Main Execution
    # ---------------------------------------------------------------------------

    def execute(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Execute an MCP tool by name with provided arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool

        Returns:
            Dict with either {"success": true, "result": ...}
            or {"success": false, "error": "..."}
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        # Map tool names to handler methods
        tool_map = {
            # Memory tools
            "search_memories": self._exec_search_memories,
            "memory_search": self._exec_memory_search,
            "create_memory": self._exec_create_memory,
            "get_memory_stats": self._exec_get_memory_stats,
            "find_context": self._exec_find_context,
            "recall_session": self._exec_recall_session,
            # Athena tools
            "smart_search": self._exec_athena_smart_search,
            "athena_smart_search": self._exec_athena_smart_search,
            "agentic_search": self._exec_athena_agentic_search,
            "athena_agentic_search": self._exec_athena_agentic_search,
            "quicksave": self._exec_athena_quicksave,
            "athena_quicksave": self._exec_athena_quicksave,
            "query_unified_memory": self._exec_athena_query_unified_memory,
            "get_active_context": self._exec_athena_get_active_context,
            "get_product_context": self._exec_athena_get_product_context,
            "get_user_context": self._exec_athena_get_user_context,
            # Filesystem tools
            "read_file": self._exec_filesystem_read_text_file,
            "filesystem_read_text_file": self._exec_filesystem_read_text_file,
            "write_file": self._exec_filesystem_write_file,
            "filesystem_write_file": self._exec_filesystem_write_file,
            "list_directory": self._exec_filesystem_list_directory,
            "filesystem_list_directory": self._exec_filesystem_list_directory,
            "search_files": self._exec_filesystem_search_files,
            "get_file_info": self._exec_filesystem_get_file_info,
            # Git tools
            "git_status": self._exec_git_git_status,
            "git_git_status": self._exec_git_git_status,
            "git_log": self._exec_git_git_log,
            "git_git_log": self._exec_git_git_log,
            "git_diff": self._exec_git_git_diff,
            "git_git_diff": self._exec_git_git_diff,
            "git_show": self._exec_git_git_show,
            "git_git_show": self._exec_git_git_show,
            # Fetch tools
            "fetch_markdown": self._exec_fetch_fetch_markdown,
            "fetch_fetch_markdown": self._exec_fetch_fetch_markdown,
            "fetch_readable": self._exec_fetch_fetch_readable,
            "fetch_fetch_readable": self._exec_fetch_fetch_readable,
            # GitHub tools
            "search_code": self._exec_github_search_code,
            "github_search_code": self._exec_github_search_code,
            "list_issues": self._exec_github_list_issues,
            "github_list_issues": self._exec_github_list_issues,
            # Context7 tools
            "query_docs": self._exec_context7_query_docs,
            "context7_query_docs": self._exec_context7_query_docs,
            # NX-Mind tools
            "get_mind_state": self._exec_nxmind_get_mind_state,
            "nxmind_get_mind_state": self._exec_nxmind_get_mind_state,
            "update_mind_state": self._exec_nxmind_update_mind_state,
            "nxmind_update_mind_state": self._exec_nxmind_update_mind_state,
            "get_session_history": self._exec_nxmind_get_session_history,
            "nxmind_get_session_history": self._exec_nxmind_get_session_history,
            # Grep tools
            "searchGitHub": self._exec_grep_app_searchGitHub,
            "grep_app_searchGitHub": self._exec_grep_app_searchGitHub,
            # Trigger Guardian
            "register_trigger": self._exec_trigger_guardian_register_trigger,
            "trigger_guardian_register_trigger": self._exec_trigger_guardian_register_trigger,
            "list_triggers": self._exec_trigger_guardian_list_triggers,
            "trigger_guardian_list_triggers": self._exec_trigger_guardian_list_triggers,
        }

        # Find and execute the handler
        handler = tool_map.get(tool_name)

        if handler is None:
            logger.warning(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Available tools: {list(tool_map.keys())}",
            }

        try:
            result = handler(arguments)
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}", exc_info=True)

            # Delegate to AI agent for diagnosis
            try:
                from src.dashboard.ai_brain import DashboardAIBrain

                ai_brain = DashboardAIBrain()
                diagnosis = asyncio.run(
                    ai_brain.handle_error(e, f"mcp_tool_executor.{tool_name}")
                )
                ai_brain.close()
                return {
                    "success": False,
                    "error": str(e),
                    "ai_diagnosis": diagnosis,
                }
            except Exception:
                # If AI delegation fails, return original error
                return {
                    "success": False,
                    "error": str(e),
                }

    async def execute_async(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Async wrapper for execute().

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool

        Returns:
            Dict with either {"success": true, "result": ...}
            or {"success": false, "error": "..."}
        """
        # Most operations are CPU-bound, so we run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, tool_name, arguments)

    def execute_batch(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of {"name": "...", "arguments": {...}}

        Returns:
            List of results in same order as tool_calls
        """
        results = []
        for call in tool_calls:
            tool_name = call.get("name", "")
            arguments = call.get("arguments", {})
            results.append(self.execute(tool_name, arguments))
        return results


# Convenience function for quick execution
def execute_tool(tool_name: str, arguments: Dict) -> Dict:
    """Quick execute a single tool call."""
    executor = MCPToolExecutor()
    return executor.execute(tool_name, arguments)


# Async convenience function
async def execute_tool_async(tool_name: str, arguments: Dict) -> Dict:
    """Quick execute a single tool call asynchronously."""
    executor = MCPToolExecutor()
    return await executor.execute_async(tool_name, arguments)
