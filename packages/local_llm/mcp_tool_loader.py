#!/usr/bin/env python3
"""MCP Tool Loader - Discovers and loads tools from MCP servers.

Loads tool definitions from opencode.json MCP configuration and exposes them
in a format compatible with local_llm for tool calling.
"""

import json
import logging
import os
import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("mcp_tool_loader")

# Path to opencode.json
OPENCODE_CONFIG_PATH = os.environ.get("OPENCODE_CONFIG_PATH", "opencode.json")

# Known tool schemas for MCP servers (we discover these dynamically)
# For now, we provide common MCP tools with their schemas


class MCPTool:
    """Represents a tool from an MCP server."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        mcp_server: str,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.mcp_server = mcp_server

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class MCPToolLoader:
    """Discovers and loads tools from MCP servers.

    Reads MCP configuration from opencode.json and provides tool definitions
    in a format compatible with local_llm wrapper.
    """

    # Common MCP tool schemas (enhanced with rich descriptions)
    KNOWN_TOOLS = {
        # Memory tools
        "memory_search": {
            "description": "Search across all memory sources (Athena, session, file content, MCP). "
            + "Use for: finding previously stored information, context from past sessions, "
            + "or knowledge stored in memory. NOT for: general web searches,实时信息, or file content search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "rerank": {
                        "type": "boolean",
                        "description": "Apply LLM-based reranking",
                        "default": False,
                    },
                },
                "required": ["query"],
            },
            "server": "unified-memory",
        },
        "memory_write": {
            "description": "Write memory using MemoryManager. "
            + "Use for: storing important information, session context, or knowledge to retrieve later. "
            + "NOT for: storing temporary data, large files, or real-time logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store",
                    },
                    "kind": {
                        "type": "string",
                        "description": "Type of memory (episodic, semantic, etc.)",
                        "default": "episodic",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Scope of memory (global, session, etc.)",
                        "default": "global",
                    },
                },
                "required": ["content"],
            },
            "server": "unified-memory",
        },
        "athena_smart_search": {
            "description": "Search Athena's knowledge base using hybrid RAG (Canonical + Tags + Vectors + GraphRAG + SQLite + Filenames). "
            + "Use for: finding project-specific knowledge, code patterns, or architectural decisions. "
            + "NOT for:实时信息, general web search, or file system operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                    "rerank": {
                        "type": "boolean",
                        "description": "Apply LLM-based reranking",
                        "default": False,
                    },
                },
                "required": ["query"],
            },
            "server": "athena",
        },
        # Filesystem tools
        "read_file": {
            "description": "Read a file from the local filesystem. "
            + "Use for: examining code, configs, or text files. "
            + "NOT for: reading large binary files (images, videos), running executables, or network operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "head": {
                        "type": "integer",
                        "description": "Return only first N lines",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Return only last N lines",
                    },
                },
                "required": ["path"],
            },
            "server": "filesystem",
        },
        "write_file": {
            "description": "Write content to a file (creates or overwrites). "
            + "Use for: creating new files, updating configs, or writing code. "
            + "NOT for: appending to files (use edit), executing code, or network operations. WARNING: overwrites existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            "server": "filesystem",
        },
        "list_directory": {
            "description": "List files and directories in a path. "
            + "Use for: exploring directory structure, finding files, or checking what exists. "
            + "NOT for: reading file contents (use read_file), executing files, or network operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to list"},
                },
                "required": ["path"],
            },
            "server": "filesystem",
        },
        # Git tools
        "git_status": {
            "description": "Shows the working tree status. "
            + "Use for: checking modified/staged/untracked files before commit. "
            + "NOT for: viewing file contents, network operations, or cloning repositories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to Git repository",
                    },
                },
                "required": ["repo_path"],
            },
            "server": "git",
        },
        "git_log": {
            "description": "Shows the commit logs. "
            + "Use for: viewing commit history, finding when changes were made, or understanding project timeline. "
            + "NOT for: viewing file differences, checking current status, or network operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits",
                        "default": 10,
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Path to Git repository",
                    },
                },
                "required": ["repo_path"],
            },
            "server": "git",
        },
        "git_diff": {
            "description": "Shows differences between branches or commits. "
            + "Use for: comparing code changes, reviewing modifications, or understanding what changed. "
            + "NOT for: viewing commit history, checking status, or creating commits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to Git repository",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target branch or commit",
                    },
                },
                "required": ["repo_path", "target"],
            },
            "server": "git",
        },
        "git_branch": {
            "description": "Shows Git branches. "
            + "Use for: listing branches, seeing current branch, comparing branches. "
            + "NOT for: creating branches, deleting branches, or network operations.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "server": "git",
        },
        # GitHub tools
        "github_search_repositories": {
            "description": "Find GitHub repositories by name, description, or topics. "
            + "Use for: discovering libraries, finding example projects, or researching technologies. "
            + "NOT for: accessing private repos, managing issues, or CI/CD operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Repository search query",
                    },
                    "minimal_output": {
                        "type": "boolean",
                        "description": "Return minimal info",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
            "server": "github",
        },
        "github_list_issues": {
            "description": "List issues in a GitHub repository. "
            + "Use for: viewing open/closed issues, finding bug reports, or checking project status. "
            + "NOT for: creating issues, managing PRs, or cloning repos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {
                        "type": "string",
                        "description": "Filter by state",
                        "enum": ["OPEN", "CLOSED"],
                    },
                },
                "required": ["owner", "repo"],
            },
            "server": "github",
        },
        # Fetch tools
        "fetch_url": {
            "description": "Fetch content from a URL. "
            + "Use for: retrieving web content, APIs, or online documentation. "
            + "NOT for: executing code, database operations, or real-time searches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "format": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["text", "markdown", "html"],
                        "default": "markdown",
                    },
                },
                "required": ["url"],
            },
            "server": "fetch",
        },
        # Context7 (docs lookup)
        "context7_query_docs": {
            "description": "Query documentation for libraries and frameworks via Context7. "
            + "Use for: learning library APIs, finding usage examples, or understanding framework features. "
            + "NOT for: general web search,实时信息, or code execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "library_id": {
                        "type": "string",
                        "description": "Context7 library ID (e.g., /mongodb/docs)",
                    },
                    "query": {
                        "type": "string",
                        "description": "The question about the library",
                    },
                },
                "required": ["library_id", "query"],
            },
            "server": "context7",
        },
        # Sequential thinking
        "sequential_thinking": {
            "description": "Chain-of-thought reasoning for complex problems. "
            + "Use for: multi-step reasoning, complex debugging, or architecture decisions. "
            + "NOT for: simple factual queries, file operations, or real-time data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Current thinking step",
                    },
                    "nextThoughtNeeded": {
                        "type": "boolean",
                        "description": "Whether another thought is needed",
                    },
                    "thoughtNumber": {
                        "type": "integer",
                        "description": "Current thought number",
                    },
                    "totalThoughts": {
                        "type": "integer",
                        "description": "Estimated total thoughts needed",
                    },
                },
                "required": [
                    "thought",
                    "nextThoughtNeeded",
                    "thoughtNumber",
                    "totalThoughts",
                ],
            },
            "server": "sequential-thinking",
        },
        # Athena context
        "get_active_context": {
            "description": "Get current active context from memory bank (activeContext.md). "
            + "Use for: understanding current project state, session goals, or active tasks. "
            + "NOT for: historical data, file operations, or network requests.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "server": "athena-context",
        },
        "get_user_context": {
            "description": "Get user context from memory bank (userContext.md). "
            + "Use for: understanding user preferences, communication style, or project goals. "
            + "NOT for: system configuration, file operations, or real-time data.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "server": "athena-context",
        },
        # Learning engine
        "route_task": {
            "description": "Get routing recommendation for a task using Q-Learning. "
            + "Use for: determining which agent to use, complexity level, or execution strategy. "
            + "NOT for: executing tasks, file operations, or direct code execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Task to route",
                    },
                },
                "required": ["task_description"],
            },
            "server": "learning-engine",
        },
        "record_outcome": {
            "description": "Record a delegation outcome for learning. "
            + "Use for: tracking task success, agent performance, or routing optimization. "
            + "NOT for: executing tasks, querying data, or file operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"},
                    "agent": {
                        "type": "string",
                        "description": "Agent that handled the task",
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether task succeeded",
                    },
                    "latency_ms": {
                        "type": "number",
                        "description": "Execution time in ms",
                    },
                    "tokens_used": {"type": "integer", "description": "Tokens used"},
                },
                "required": ["task", "agent", "success"],
            },
            "server": "learning-engine",
        },
        # Health check tool
        "get_health": {
            "description": "Get health summary of the N-Xyme MIND system. "
            + "Use for: checking system status, diagnosing issues, or verifying services are running. "
            + "NOT for: executing tasks, file operations, or detailed diagnostics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "description": "Health check level: l0 (basic), l1 (services), l2 (deep)",
                        "default": "l0",
                    },
                },
            },
            "server": "learning-engine",
        },
        # Quality gates
        "run_typecheck": {
            "description": "Run TypeScript type check (gate-1). "
            + "Use for: validating TypeScript types before commit or deployment. "
            + "NOT for: JavaScript files, runtime execution, or linting.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "server": "quality-gates",
        },
        "run_lint": {
            "description": "Run linting (gate-2). "
            + "Use for: checking code style, finding potential errors, or enforcing conventions. "
            + "NOT for: type checking, test execution, or file operations.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "server": "quality-gates",
        },
        # Playwright
        "browser_navigate": {
            "description": "Navigate to a URL in browser. "
            + "Use for: opening web pages, testing web apps, or extracting web content. "
            + "NOT for: local file operations, database queries, or API calls without a browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                },
                "required": ["url"],
            },
            "server": "playwright",
        },
        "browser_click": {
            "description": "Click on an element in browser. "
            + "Use for: interacting with web UI, filling forms, or navigating web apps. "
            + "NOT for: keyboard-only operations, background tasks, or non-browser actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "Element reference"},
                },
                "required": ["ref"],
            },
            "server": "playwright",
        },
        # SQLite
        "sqlite_query": {
            "description": "Execute a SELECT query (read-only) on the routing outcomes database. "
            + "Use for: querying delegation outcomes, agent performance stats, or routing analytics. "
            + "NOT for: INSERT/UPDATE/DELETE operations or schema changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
            "server": "sqlite",
        },
        "get_outcomes": {
            "description": "Get delegation outcomes from the learning engine. "
            + "Use for: viewing task delegation history, agent performance, or routing stats. "
            + "NOT for: executing tasks, file operations, or direct SQL queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Filter by agent name (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum outcomes to return",
                        "default": 20,
                    },
                },
            },
            "server": "learning-engine",
        },
    }

    def __init__(self, config_path: str = OPENCODE_CONFIG_PATH):
        self.config_path = config_path
        self._tools: Dict[str, MCPTool] = {}
        self._handlers: Dict[str, Callable] = {}
        self._load_config()
        self._discover_tools()

    def _load_config(self) -> None:
        """Load MCP configuration from opencode.json."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            logger.warning(f"Config not found: {self.config_path}")
            self.mcp_servers = {}
            return

        with open(config_file) as f:
            config = json.load(f)

        self.mcp_servers = config.get("mcp", {})
        logger.info(f"Loaded {len(self.mcp_servers)} MCP server configs")

    def _discover_tools(self) -> None:
        """Discover available tools from known schemas."""
        for tool_name, tool_spec in self.KNOWN_TOOLS.items():
            self._tools[tool_name] = MCPTool(
                name=tool_name,
                description=tool_spec["description"],
                parameters=tool_spec["parameters"],
                mcp_server=tool_spec["server"],
            )

        logger.info(f"Discovered {len(self._tools)} MCP tools")

    def get_tools(self) -> List[MCPTool]:
        """Get all available tools."""
        return list(self._tools.values())

    def get_tools_openai_format(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        return [tool.to_openai_format() for tool in self._tools.values()]

    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for a tool."""
        self._handlers[tool_name] = handler
        logger.info(f"Registered handler for: {tool_name}")

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if tool_name not in self._handlers:
            # Return placeholder for tools without handlers
            return {
                "error": f"No handler for tool: {tool_name}",
                "tool": tool_name,
                "arguments": arguments,
                "note": "Tool exists but handler not registered",
            }

        handler = self._handlers[tool_name]
        try:
            result = await handler(arguments)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e), "tool": tool_name}

    def list_tools(self) -> List[str]:
        """List tool names."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self._tools.get(name)

    def get_tools_by_server(self, server: str) -> List[MCPTool]:
        """Get tools for a specific MCP server."""
        return [t for t in self._tools.values() if t.mcp_server == server]

    def is_server_available(self, server: str) -> bool:
        """Check if an MCP server is configured."""
        return server in self.mcp_servers


# Global loader instance
_loader: Optional[MCPToolLoader] = None


def get_tool_loader(config_path: str = OPENCODE_CONFIG_PATH) -> MCPToolLoader:
    """Get the global tool loader instance."""
    global _loader
    if _loader is None:
        _loader = MCPToolLoader(config_path)
    return _loader


def get_all_tools() -> List[Dict[str, Any]]:
    """Convenience function to get all tools in OpenAI format."""
    return get_tool_loader().get_tools_openai_format()


if __name__ == "__main__":
    # Test
    loader = MCPToolLoader()
    print(f"Loaded {len(loader.list_tools())} tools:")
    for tool in loader.list_tools()[:10]:
        t = loader.get_tool(tool)
        if t:
            print(f"  - {tool} ({t.mcp_server}): {t.description[:50]}...")
