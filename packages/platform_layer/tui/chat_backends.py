#!/usr/bin/env python3
"""Chat Backend - Bridge between AI Chat and all N-Xyme MIND backend systems."""

# pyright: reportMissingImports=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportArgumentType=false

import asyncio
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Optional

# Memory Core imports
try:
    from packages.memory_core import search as memory_search, stats as memory_stats
    from packages.memory_core import recall_session, store as memory_store
    from packages.memory_core.retrievers import TEMPRRetriever

    MEMORY_CORE_AVAILABLE = True
except ImportError:
    MEMORY_CORE_AVAILABLE = False

# Learning Engine imports
try:
    from packages.learning_engine import status as learning_status, route_task
    from packages.learning_engine.outcome_logger import OutcomeLogger

    LEARNING_ENGINE_AVAILABLE = True
except ImportError:
    # Fallback: try with hyphen naming (learning-engine)
    try:
        from packages.learning_engine import status as learning_status, route_task
        from packages.learning_engine.outcome_logger import OutcomeLogger

        LEARNING_ENGINE_AVAILABLE = True
    except ImportError:
        LEARNING_ENGINE_AVAILABLE = False

# Local LLM import
try:
    from packages.local_llm import LocalLLM

    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False


# ─── Intent Patterns ────────────────────────────────────────────────────────────

INTENTS = {
    "memory": [
        "search memory",
        "find in memory",
        "what do you remember",
        "semantic",
        "recall",
        "what did i work on",
        "context",
    ],
    "stats": [
        "stats",
        "statistics",
        "show metrics",
        "performance",
        "how is",
        "health check",
        "system status",
    ],
    "routing": [
        "routing",
        "agent performance",
        "delegation",
        "outcomes",
        "which agent",
        "best agent",
        "success rate",
    ],
    "health": [
        "health",
        "status",
        "check",
        "broken",
        "running",
        "is working",
        "what's wrong",
        "diagnose",
    ],
    "command": [
        "start",
        "stop",
        "restart",
        "run",
        "execute",
        "launch",
        "kill",
        "reload",
    ],
    "logs": [
        "logs",
        "journal",
        "recent activity",
        "what happened",
        "errors",
        "trace",
    ],
    "session": [
        "session",
        "conversation",
        "previous",
        "recent",
        "what were we",
        "last time",
    ],
    "git": [
        "git status",
        "git log",
        "git diff",
        "git branch",
        "show changes",
        "show commits",
        "what changed",
        "recent commits",
        "untracked files",
        "stashed",
        "status of my repo",
        "commit history",
    ],
    "health": [
        "health check",
        "system status",
        "is working",
        "what's wrong",
        "diagnose",
        "run a health",
    ],
    "file": [
        "read",
        "show",
        "cat",
        "list directory",
        "ls ",
        "dir ",
        "browse",
        "open",
        "display",
        "contents of",
    ],
    "alias": [
        "do status",
        "do log",
        "do health",
        "do memory",
        "do routing",
    ],
}


# ─── ChatBackend Class ─────────────────────────────────────────────────────────


class ChatBackend:
    """Bridge between chat and all N-Xyme MIND backend systems."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 30  # seconds
        self._retriever = TEMPRRetriever() if MEMORY_CORE_AVAILABLE else None
        self._command_history: list[dict] = []  # Store recent commands
        self._max_history = 20

    # ─── Intent Detection ─────────────────────────────────────────────────

    def detect_intent(self, query: str) -> list[str]:
        """Detect what the user is asking for."""
        query_lower = query.lower()
        detected = []
        for intent, patterns in INTENTS.items():
            if any(p in query_lower for p in patterns):
                detected.append(intent)
        return detected if detected else ["general"]

    # ─── Memory Search ────────────────────────────────────────────────────

    async def get_memory_results(self, query: str, limit: int = 5) -> dict:
        """Query Athena memory."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            # Use TEMPRRetriever for semantic search
            if self._retriever:
                results = self._retriever.search(query, top_k=limit)
                if results:
                    return {
                        "status": "ok",
                        "results": [
                            {
                                "content": r.get("content", "")[:200],
                                "score": r.get("score", 0),
                                "source": r.get("source", "unknown"),
                            }
                            for r in results[:limit]
                        ],
                        "count": len(results),
                    }

            # Fallback to simple search
            results = memory_search(query, limit=limit)
            return {
                "status": "ok",
                "results": results,
                "count": len(results) if results else 0,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_memory_stats(self) -> dict:
        """Get memory system statistics."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            stats = memory_stats()
            return {"status": "ok", "stats": stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def recall_session(self, session_id: str = None, limit: int = 10) -> dict:
        """Recall session context."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            result = recall_session(session_id=session_id, limit=limit)
            return {"status": "ok", "session": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def write_memory(
        self, content: str, kind: str = "episodic", scope: str = "global"
    ) -> dict:
        """Write a memory to the memory system."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            result = memory_store(content, kind=kind, scope=scope)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Routing Stats ─────────────────────────────────────────────────────

    async def get_routing_stats(self) -> dict:
        """Get learning engine stats from SQLite."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            status_info = learning_status()
            return {"status": "ok", "stats": status_info}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def sqlite_query(self, query: str, limit: int = 20) -> dict:
        """Query routing/outcomes SQLite database."""
        import os

        db_path = ".sisyphus/outcomes.db"

        if not os.path.exists(db_path):
            return {"status": "error", "error": f"Database not found: {db_path}"}

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Safety: only allow SELECT queries
            query_stripped = query.strip().upper()
            if not query_stripped.startswith("SELECT"):
                conn.close()
                return {"status": "error", "error": "Only SELECT queries allowed"}

            cursor.execute(query)
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = []
            for row in rows[:limit]:
                results.append({k: row[k] for k in row.keys()})

            conn.close()
            return {"status": "ok", "results": results, "count": len(results)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_outcomes(self, agent: str = None, limit: int = 20) -> dict:
        """Get delegation outcomes."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            logger = OutcomeLogger()
            outcomes = logger.get_outcomes(agent=agent, limit=limit)
            return {
                "status": "ok",
                "outcomes": [
                    {
                        "agent": o.agent,
                        "task": o.task_description[:50],
                        "success": o.success,
                        "latency_ms": o.latency_ms,
                        "timestamp": o.timestamp,
                    }
                    for o in outcomes
                ],
                "count": len(outcomes),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_agent_performance(self) -> dict:
        """Get agent performance summary."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            logger = OutcomeLogger()
            all_stats = logger.get_all_agent_stats()
            return {"status": "ok", "performance": all_stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Health Checks ────────────────────────────────────────────────────

    async def get_health_summary(self, level: str = "l0") -> dict:
        """Run health checks and summarize."""
        script_map = {
            "l0": "bin/health-l0-blink.sh",
            "l1": "bin/health-l1-pulse.sh",
            "l2": "bin/health-l2-vitals.sh",
        }

        script = script_map.get(level, "bin/health-l0-blink.sh")
        script_path = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND") / script

        if not script_path.exists():
            return {"status": "error", "error": f"Health script not found: {script}"}

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
            )

            output = result.stdout[:1000] if result.stdout else ""
            error = result.stderr[:500] if result.stderr else ""

            return {
                "status": "ok" if result.returncode == 0 else "degraded",
                "returncode": result.returncode,
                "output": output,
                "error": error if error else None,
                "level": level,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Health check timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def athena_search(self, query: str, limit: int = 5) -> dict:
        """Search Athena knowledge base via memory search."""
        # Use the existing memory search instead
        return await self.get_memory_results(query, limit)

    async def get_active_context(self) -> dict:
        """Get current active context."""
        try:
            # Read directly from memory bank
            ctx_path = Path(
                "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.context/memory_bank/activeContext.md"
            )
            if ctx_path.exists():
                content = ctx_path.read_text()[:2000]
                return {"status": "ok", "context": content}
            return {"status": "not_found", "error": "activeContext.md not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_user_context(self) -> dict:
        """Get user context/preferences."""
        try:
            user_path = Path(
                "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.context/memory_bank/userContext.md"
            )
            if user_path.exists():
                content = user_path.read_text()[:2000]
                return {"status": "ok", "user": content}
            return {"status": "not_found", "error": "userContext.md not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_service(self, service: str) -> dict:
        """Check if a specific service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            is_active = result.returncode == 0
            return {
                "status": "ok",
                "service": service,
                "running": is_active,
                "state": result.stdout.strip(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Command Execution ─────────────────────────────────────────────────

    async def execute_command(self, command: str) -> dict:
        """Execute a system command."""
        import subprocess

        # Whitelist of allowed commands
        allowed_prefixes = [
            "start ",
            "stop ",
            "restart ",
            "systemctl --user start",
            "systemctl --user stop",
            "systemctl --user restart",
            "bash ",
            "python3 ",
            "pip ",
        ]

        command_lower = command.lower().strip()

        # Check if command is in whitelist
        is_allowed = any(
            command_lower.startswith(prefix.lower()) for prefix in allowed_prefixes
        )

        if not is_allowed:
            return {"status": "error", "error": f"Command not allowed: {command[:50]}"}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
            )

            return {
                "status": "ok" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "output": result.stdout[:2000],
                "error": result.stderr[:500] if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def start_service(self, service: str) -> dict:
        """Start a user service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", service],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "service": service,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def stop_service(self, service: str) -> dict:
        """Stop a user service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "stop", service],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "service": service,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── LLM Integration ──────────────────────────────────────────────────

    async def get_llm_response(
        self,
        messages: list[dict],
        model: str = "qwen2.5-coder:7b",
        system_prompt: str = "",
    ) -> dict:
        """Get response from LocalLLM."""
        if not LOCAL_LLM_AVAILABLE:
            return {"status": "unavailable", "error": "Local LLM not available"}

        try:
            llm = LocalLLM(model=model)

            # Add system prompt if provided
            if system_prompt:
                full_messages = [
                    {"role": "system", "content": system_prompt}
                ] + messages
            else:
                full_messages = messages

            response = llm.chat(full_messages)

            if isinstance(response, dict) and "content" in response:
                return {"status": "ok", "content": response["content"]}
            elif isinstance(response, dict) and "Error" in str(
                response.get("content", "")
            ):
                return {
                    "status": "error",
                    "error": response.get("content", "Unknown error"),
                }
            else:
                return {"status": "ok", "content": str(response)}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── LLM Integration with Tools ─────────────────────────────────────────────

    async def get_llm_response_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        model: str = "qwen2.5-coder:7b",
        temperature: float = 0.3,
    ) -> dict:
        """Get response from LLM with tool calling support.

        Args:
            messages: Chat history including previous tool results
            tools: Tool definitions in OpenAI function format
            model: Model to use
            temperature: Lower temp = more deterministic tool selection

        Returns:
            dict with "content" and/or "tool_calls" keys
        """
        if not LOCAL_LLM_AVAILABLE:
            return {"status": "unavailable", "error": "Local LLM not available"}

        try:
            llm = LocalLLM(model=model)

            # Use the chat_with_tools method which handles tool calling API
            response = llm.chat_with_tools(
                messages=messages,
                tools=tools or [],
                temperature=temperature,
            )

            # Parse response based on type
            if response.type == "tool_calls":
                tool_calls = []
                for tc in response.tool_calls:
                    tool_calls.append(
                        {
                            "id": getattr(tc, "id", f"call_{tc.name}"),
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    )
                return {
                    "status": "ok",
                    "tool_calls": tool_calls,
                }
            elif response.type == "text":
                return {
                    "status": "ok",
                    "content": response.content or "",
                }
            else:
                return {
                    "status": "ok",
                    "content": str(response),
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def execute_with_tools(
        self,
        query: str,
        max_iterations: int = 3,
        model: str = "llama3.2:3b",
    ) -> dict:
        """Execute query using tool calling with the LLM.

        This method implements a tool loop where:
        1. Send query + tools to LLM
        2. LLM may call tools (git, read_file, etc.)
        3. Execute tool calls and send results back
        4. Repeat until LLM returns final answer

        Args:
            query: User query
            max_iterations: Max tool call iterations (prevents infinite loops)
            model: Model to use

        Returns:
            dict with final response or error
        """
        # Import MCPToolLoader to get tool definitions
        try:
            from packages.local_llm.mcp_tool_loader import MCPToolLoader
        except ImportError:
            return {"status": "error", "error": "MCPToolLoader not available"}

        # Get tools in OpenAI format
        loader = MCPToolLoader()
        tools = loader.get_tools_openai_format()

        if not tools:
            # Fall back to no-tool mode if no tools available
            return await self.get_llm_response(
                [{"role": "user", "content": query}],
                model=model,
            )

        # Map OpenAI tool names to ChatBackend methods
        # These are the tools the LLM can actually call
        # Default values for tools when LLM doesn't provide them
        repo_path_default = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

        def resolve_path(path: str) -> str:
            """Resolve path relative to workspace, with fallbacks."""
            # Reject obviously invalid paths - more comprehensive
            path_str = str(path) if path else ""
            invalid_patterns = (
                "{",
                "}",
                "/path",
                "none",
                "null",
                "your",
                "type",
                "object",
                "array",
                "[]",
                "<",
            )
            if not path or any(p in path_str.lower() for p in invalid_patterns):
                return repo_path_default

            # Use the path if it's a valid absolute path starting with /home
            if path_str.startswith("/"):
                if path_str.startswith("/home"):
                    return path_str
                return repo_path_default + path_str
            # Relative path - prepend workspace
            return f"{repo_path_default}/{path_str}"

        # Stronger system prompt for tool calling
        system_msg = (
            "You are N-Xyme MIND AI assistant. "
            "IMPORTANT: When calling tools, use the DEFAULT values if the user doesn't specify. "
            "For repo_path, use: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND "
            "For path, use relative paths like 'README.md' or 'docs/' "
            "Do NOT use placeholder values like /path/to/repo or JSON schema types. "
            "After getting tool results, respond with plain text only, NO more tools."
        )

        TOOL_HANDLERS = {
            "git_status": lambda **kwargs: self.git_operation("status"),
            "git_log": lambda **kwargs: self.git_operation(
                "log", kwargs.get("max_count", 10)
            ),
            "git_diff": lambda **kwargs: self.git_operation("diff"),
            "git_branch": lambda **kwargs: self.git_operation("branch"),
            "read_file": lambda **kwargs: self.read_file(
                resolve_path(kwargs.get("path", "")), kwargs.get("lines", 50)
            ),
            "list_directory": lambda **kwargs: self.list_directory(
                resolve_path(kwargs.get("path", "."))
            ),
            "memory_search": lambda **kwargs: self.get_memory_results(
                kwargs.get("query", ""), kwargs.get("limit", 5)
            ),
            "memory_write": lambda **kwargs: self.write_memory(
                kwargs.get("content", ""),
                kwargs.get("kind", "episodic"),
                kwargs.get("scope", "global"),
            ),
            "route_task": lambda **kwargs: self.get_routing_stats(),
            "get_health": lambda **kwargs: self.get_health_summary(
                kwargs.get("level", "l0")
            ),
            "athena_smart_search": lambda **kwargs: self.athena_search(
                kwargs.get("query", ""), kwargs.get("limit", 5)
            ),
            "get_active_context": lambda **kwargs: self.get_active_context(),
            "get_user_context": lambda **kwargs: self.get_user_context(),
            "sqlite_query": lambda **kwargs: self.sqlite_query(
                kwargs.get("query", "SELECT * FROM outcomes LIMIT 5"),
                kwargs.get("limit", 20),
            ),
            "get_outcomes": lambda **kwargs: self.get_outcomes(
                kwargs.get("agent"), kwargs.get("limit", 20)
            ),
        }

        # Initialize conversation with user query
        messages = [
            {
                "role": "system",
                "content": system_msg,
            },
            {"role": "user", "content": query},
        ]

        for iteration in range(max_iterations):
            # Get LLM response with current messages
            response = await self.get_llm_response_with_tools(
                messages=messages,
                tools=tools,
                model=model,
            )

            if response.get("status") != "ok":
                return response

            # Check if LLM wants to call tools
            tool_calls = response.get("tool_calls")
            if not tool_calls:
                # No tools called - this is the final response
                return {
                    "status": "ok",
                    "content": response.get("content", "No response"),
                    "iterations": iteration + 1,
                }

            # Execute each tool call and add results to messages
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                args = tc.get("arguments", {})

                # Execute the tool
                if tool_name in TOOL_HANDLERS:
                    try:
                        result = await TOOL_HANDLERS[tool_name](**args)
                    except Exception as e:
                        result = {"status": "error", "error": str(e)}
                else:
                    result = {"status": "error", "error": f"Unknown tool: {tool_name}"}

                # Add assistant message with tool call first (required for tool result)
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc.get("id", f"call_{tool_name}"),
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(args),
                                },
                            }
                        ],
                    }
                )

                # Then add tool result message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call_{tool_name}"),
                        "content": json.dumps(result),
                    }
                )

        # Max iterations reached
        return {
            "status": "max_iterations",
            "content": f"Maximum {max_iterations} tool call iterations reached. Add more context if needed.",
        }

    # ─── Context Building ─────────────────────────────────────────────────

    async def build_context(self, query: str, intents: list[str]) -> dict:
        """Build context from all relevant backends based on intents."""
        context_parts = []

        # Memory search (if relevant)
        if "memory" in intents or "session" in intents:
            mem_results = await self.get_memory_results(query)
            if mem_results.get("status") == "ok" and mem_results.get("results"):
                context_parts.append("## Memory Results")
                for r in mem_results["results"][:3]:
                    context_parts.append(f"- {r.get('content', '')[:150]}...")

        # Routing stats (if relevant)
        if "routing" in intents or "stats" in intents:
            routing = await self.get_routing_stats()
            if routing.get("status") == "ok":
                stats = routing.get("stats", {})
                weights = stats.get("routing_weights", {})
                if weights:
                    context_parts.append("## Agent Performance")
                    for agent, data in list(weights.items())[:5]:
                        success_rate = data.get("success_rate", 0)
                        context_parts.append(
                            f"- {agent}: {success_rate:.1%} success rate"
                        )

        # Health check (if relevant)
        if "health" in intents or "stats" in intents:
            health = await self.get_health_summary("l0")
            if health.get("status") == "ok":
                context_parts.append(f"## System Health (L0)")
                context_parts.append(
                    f"- Status: {health.get('output', 'Unknown')[:200]}"
                )

        # Command execution (if relevant)
        if "command" in intents:
            cmd_result = await self.execute_command(query)
            if cmd_result.get("status") == "ok":
                context_parts.append(f"## Command Output")
                context_parts.append(cmd_result.get("output", "Success")[:500])
            else:
                context_parts.append(f"## Command Error")
                context_parts.append(cmd_result.get("error", "Unknown error"))

        # Log retrieval (if relevant)
        if "logs" in intents:
            logs_result = await self.get_logs(lines=30)
            if logs_result.get("status") == "ok":
                context_parts.append(
                    f"## Recent Logs ({logs_result.get('source', 'unknown')})"
                )
                context_parts.append(logs_result.get("logs", "No logs")[:1000])
            else:
                context_parts.append(f"## Logs Error")
                context_parts.append(logs_result.get("error", "Unknown error"))

        # Git operations (if relevant)
        if "git" in intents:
            query_lower = query.lower()
            if "status" in query_lower or "changes" in query_lower:
                git_result = await self.git_operation("status")
                context_parts.append("## Git Status")
                context_parts.append(git_result.get("output", "No changes")[:500])
            elif "log" in query_lower or "commits" in query_lower:
                git_result = await self.git_operation("log")
                context_parts.append("## Git Log (Recent Commits)")
                context_parts.append(git_result.get("output", "No commits")[:500])
            elif "diff" in query_lower:
                git_result = await self.git_operation("diff")
                context_parts.append("## Git Diff")
                context_parts.append(git_result.get("output", "No changes")[:500])
            elif "branch" in query_lower:
                git_result = await self.git_operation("branch")
                context_parts.append("## Git Branches")
                context_parts.append(git_result.get("output", "No branches")[:500])
            else:
                # Default: show status
                git_result = await self.git_operation("status")
                context_parts.append("## Git Status")
                context_parts.append(git_result.get("output", "Error")[:500])

        # File operations (if relevant)
        if "file" in intents:
            query_lower = query.lower()
            # Extract potential path from query
            import re

            path_match = re.search(
                r"(?:read|show|cat|list)\s+(?:file\s+)?([^\s]+)", query_lower
            )
            if path_match:
                file_path = path_match.group(1)
                file_result = await self.read_file(file_path)
                if file_result.get("status") == "ok":
                    context_parts.append(
                        f"## File: {file_result.get('path', file_path)}"
                    )
                    context_parts.append(f"```\n{file_result.get('content', '')}\n```")
                else:
                    context_parts.append("## File Error")
                    context_parts.append(file_result.get("error", "Unknown"))
            elif "list" in query_lower or "dir" in query_lower or "ls" in query_lower:
                # List current directory
                dir_result = await self.list_directory(".")
                if dir_result.get("status") == "ok":
                    context_parts.append("## Directory Listing")
                    context_parts.append("\n".join(dir_result.get("items", [])))

        # Alias execution (if relevant)
        if "alias" in intents:
            query_lower = query.lower()
            # Check for known aliases
            for alias_name in self._init_aliases().keys():
                if f"do {alias_name}" in query_lower:
                    alias_result = await self.execute_alias(alias_name)
                    if alias_result.get("status") == "ok":
                        context_parts.append(f"## Alias: {alias_name}")
                        context_parts.append(
                            alias_result.get("output", "Success")[:500]
                        )
                    else:
                        context_parts.append(f"## Alias Error")
                        context_parts.append(alias_result.get("error", "Unknown"))
                    break

        return {
            "context": "\n\n".join(context_parts) if context_parts else "",
            "intents": intents,
        }

    # ─── Log Retrieval ────────────────────────────────────────────────────────

    async def get_logs(self, service: str = None, lines: int = 50) -> dict:
        """Get recent logs from journalctl or files."""
        try:
            # Try journalctl first for user services
            if service:
                cmd = [
                    "journalctl",
                    "--user",
                    "-u",
                    service,
                    "-n",
                    str(lines),
                    "--no-pager",
                ]
            else:
                cmd = ["journalctl", "--user", "-n", str(lines), "--no-pager"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout:
                return {
                    "status": "ok",
                    "source": "journalctl",
                    "logs": result.stdout[-3000:],  # Last 3000 chars
                    "service": service,
                }
        except Exception:
            pass

        # Fallback: try reading from log files
        log_paths = [
            Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND") / ".sisyphus" / "session.log",
            Path.home() / ".local" / "share" / "opencode" / "logs" / "agent.log",
        ]

        for log_path in log_paths:
            if log_path.exists():
                try:
                    content = log_path.read_text()
                    lines_list = content.split("\n")
                    return {
                        "status": "ok",
                        "source": str(log_path.name),
                        "logs": "\n".join(lines_list[-lines:]),
                    }
                except Exception:
                    continue

        return {"status": "error", "error": "No logs found"}

    # ─── Command History ──────────────────────────────────────────────────────

    def add_to_history(self, query: str, response: str, intents: list[str]) -> None:
        """Add a query/response pair to command history."""
        import time as time_module

        self._command_history.append(
            {
                "query": query,
                "response": response[:200] if response else "",
                "intents": intents,
                "timestamp": time_module.time(),
            }
        )
        # Keep only max_history items
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history :]

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent command history."""
        return self._command_history[-limit:]

    # ─── MCP Tool Execution ────────────────────────────────────────────────────

    async def execute_mcp_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """Execute an MCP tool by name with arguments."""
        # Available MCP tools we can call from chat
        MCP_TOOL_MAP = {
            "search_memory": {
                "module": "packages.memory_core.mcp_server",
                "function": "search_memories",
                "params": {"query": str, "limit": int},
            },
            "get_routing_stats": {
                "module": "packages.learning_engine",
                "function": "status",
                "params": {},
            },
            "route_task": {
                "module": "packages.learning_engine",
                "function": "route_task",
                "params": {"task_description": str, "level": int},
            },
            "list_sessions": {
                "module": "packages.memory_core.mcp_server",
                "function": "list_sessions",
                "params": {"limit": int},
            },
            "get_health": {
                "module": "packages.learning_engine.mcp_server",
                "function": "get_health",
                "params": {},
            },
        }

        if tool_name not in MCP_TOOL_MAP:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

        tool_info = MCP_TOOL_MAP[tool_name]
        arguments = arguments or {}

        try:
            # Dynamic import
            import importlib

            module = importlib.import_module(tool_info["module"])
            func = getattr(module, tool_info["function"])

            # Execute
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            return {"status": "ok", "result": result, "tool": tool_name}
        except Exception as e:
            return {"status": "error", "error": str(e), "tool": tool_name}

    async def list_available_tools(self) -> dict:
        """List available MCP tools for chat."""
        tools = [
            {"name": "search_memory", "description": "Search Athena memory"},
            {"name": "get_routing_stats", "description": "Get routing/learning stats"},
            {"name": "route_task", "description": "Route a task to optimal agent"},
            {"name": "list_sessions", "description": "List recent sessions"},
            {"name": "get_health", "description": "Get learning engine health"},
        ]
        return {"status": "ok", "tools": tools}

    # ─── Suggestions ───────────────────────────────────────────────────────────

    def get_suggestions(self, query: str = "") -> list[str]:
        """Get quick-reply suggestions based on query context."""
        query_lower = query.lower()

        # Base suggestions (always shown)
        base = [
            "What's broken?",
            "Show memory stats",
            "Show routing performance",
            "Run health check",
        ]

        # Context-aware suggestions
        if any(w in query_lower for w in ["memory", "search", "remember"]):
            return [
                "Search memory for recent work",
                "What did we do last session?",
                "Show all memories",
            ] + base
        elif any(w in query_lower for w in ["routing", "agent", "delegate"]):
            return [
                "Show agent success rates",
                "What routes are working?",
                "Show routing weights",
            ] + base
        elif any(w in query_lower for w in ["health", "status", "broken"]):
            return [
                "Run full health check",
                "Check all services",
                "Show system status",
            ] + base
        elif any(w in query_lower for w in ["log", "error", "trace"]):
            return [
                "Show recent errors",
                "Check journalctl",
                "Tail session log",
            ] + base

        return base

    # ─── Multi-turn Conversation Memory ────────────────────────────────────────

    def add_conversation_turn(self, role: str, content: str) -> None:
        """Add a turn to the in-memory conversation."""
        if not hasattr(self, "_conversation"):
            self._conversation: list[dict] = []

        self._conversation.append(
            {
                "role": role,
                "content": content,
            }
        )

        # Keep last 10 turns
        if len(self._conversation) > 10:
            self._conversation = self._conversation[-10:]

    def get_conversation_context(self) -> str:
        """Get formatted conversation history for LLM context."""
        if not hasattr(self, "_conversation") or not self._conversation:
            return ""

        formatted = []
        for turn in self._conversation[-5:]:  # Last 5 turns
            formatted.append(f"{turn['role']}: {turn['content'][:100]}")
        return "\n".join(formatted)

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        if hasattr(self, "_conversation"):
            self._conversation = []

    # ─── Git Operations ─────────────────────────────────────────────────────────

    async def git_operation(self, operation: str, *args) -> dict:
        """Execute git operations via chat."""
        git_path = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

        git_commands = {
            "status": ["git", "status", "--short"],
            "log": ["git", "log", "-n", "10", "--oneline", "--format=%h %s %ad"],
            "diff": ["git", "diff", "--stat"],
            "branch": ["git", "branch", "-v"],
            "stash": ["git", "stash", "list"],
            "untracked": ["git", "status", "--porcelain", "-uall"],
        }

        cmd = git_commands.get(operation.lower())
        if not cmd:
            return {"status": "error", "error": f"Unknown git operation: {operation}"}

        # Add any extra args
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=git_path,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "operation": operation,
                "output": result.stdout[:3000] if result.stdout else "",
                "error": result.stderr[:500] if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Git command timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── File Operations ────────────────────────────────────────────────────────

    async def read_file(self, path: str, lines: int = 50) -> dict:
        """Read a file via chat."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"status": "error", "error": f"File not found: {path}"}

            # Security: only allow reading within project
            project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(project_root)):
                return {"status": "error", "error": "Access denied: outside project"}

            content = resolved.read_text()
            lines_list = content.split("\n")

            return {
                "status": "ok",
                "path": str(resolved),
                "lines": len(lines_list),
                "content": "\n".join(lines_list[-lines:]),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def list_directory(self, path: str = ".") -> dict:
        """List directory contents."""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return {"status": "error", "error": f"Directory not found: {path}"}

            project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
            resolved = dir_path.resolve()
            if not str(resolved).startswith(str(project_root)):
                return {"status": "error", "error": "Access denied: outside project"}

            items = []
            for item in sorted(resolved.iterdir())[:50]:  # Limit to 50
                items.append(f"{item.name}/" if item.is_dir() else item.name)

            return {
                "status": "ok",
                "path": str(resolved),
                "items": items,
                "count": len(items),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Custom Command Aliases ────────────────────────────────────────────────

    def _init_aliases(self) -> dict:
        """Initialize default command aliases."""
        return {
            "status": "git status",
            "log": "git log",
            "health": "bash bin/health-l0-blink.sh",
            "memory": "show memory stats",
            "routing": "show routing performance",
            "untracked": "git untracked",
            "branches": "git branch",
        }

    async def execute_alias(self, alias: str) -> dict:
        """Execute a command alias."""
        aliases = self._init_aliases()

        command = aliases.get(alias.lower())
        if not command:
            return {"status": "error", "error": f"Unknown alias: {alias}"}

        # Check if it's a git command
        if command.startswith("git "):
            op = command[4:].strip()
            return await self.git_operation(op)

        # Otherwise execute as command
        return await self.execute_command(command)


# ─── Convenience Functions ─────────────────────────────────────────────────


def create_backend() -> ChatBackend:
    """Create a ChatBackend instance."""
    return ChatBackend()


async def quick_search_memory(query: str, limit: int = 5) -> list[dict]:
    """Quick memory search helper."""
    backend = ChatBackend()
    result = await backend.get_memory_results(query, limit=limit)
    return result.get("results", [])


async def quick_health_check() -> dict:
    """Quick health check helper."""
    backend = ChatBackend()
    return await backend.get_health_summary("l0")


async def quick_routing_stats() -> dict:
    """Quick routing stats helper."""
    backend = ChatBackend()
    return await backend.get_routing_stats()
