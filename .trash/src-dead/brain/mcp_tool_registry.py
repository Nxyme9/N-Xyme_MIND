"""
MCP Tool Registry - Converts MCP tool definitions to OpenAI-compatible tool schema format.

This module reads MCP tool definitions from opencode.json and provides a registry
for Rosetta Stone to retrieve available tools in the correct format.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Common tool definitions for MCPs without explicit tool definitions
# These are based on MCP capabilities documented in their respective specifications
MCP_TOOL_DEFINITIONS: Dict[str, List[Dict]] = {
    "memory": [
        {
            "name": "search_memories",
            "description": "Search across all memory sources for relevant context",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string"},
                    "limit": {"type": "integer", "description": "Maximum number of results to return (default 10)", "default": 10},
                    "rerank": {"type": "boolean", "description": "Apply LLM-based reranking to top candidates", "default": False},
                    "strict": {"type": "boolean", "description": "Filter out low-confidence results", "default": False}
                },
                "required": ["query"]
            }
        },
        {
            "name": "create_memory",
            "description": "Create a new memory entry in the knowledge graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to store in memory"},
                    "kind": {"type": "string", "description": "Type of memory (episodic, semantic, etc.)"},
                    "scope": {"type": "string", "description": "Scope of the memory (session, project, global)"},
                    "tags": {"type": "array", "description": "Tags for categorization", "items": {"type": "string"}},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                },
                "required": ["content"]
            }
        },
        {
            "name": "get_memory_stats",
            "description": "Get statistics about all memory sources and the learning system",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ],
    "athena": [
        {
            "name": "smart_search",
            "description": "Hybrid RAG search (Canonical + Tags + Vectors + GraphRAG + SQLite + Filenames)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string"},
                    "limit": {"type": "integer", "description": "Maximum number of results to return (default 10)", "default": 10},
                    "rerank": {"type": "boolean", "description": "Apply LLM-based reranking", "default": False},
                    "strict": {"type": "boolean", "description": "Filter out low-confidence results", "default": False}
                },
                "required": ["query"]
            }
        },
        {
            "name": "agentic_search",
            "description": "Multi-step query decomposition with parallel search and cosine validation",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Complex search query"},
                    "limit": {"type": "integer", "description": "Maximum number of results (default 10)", "default": 10},
                    "validate": {"type": "boolean", "description": "Validate results via cosine similarity", "default": True}
                },
                "required": ["query"]
            }
        },
        {
            "name": "quicksave",
            "description": "Save a checkpoint to the current session log",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Brief description of what was accomplished"},
                    "bullets": {"type": "array", "description": "Optional list of specific items to record", "items": {"type": "string"}}
                },
                "required": ["summary"]
            }
        }
    ],
    "github": [
        {
            "name": "list_issues",
            "description": "List issues in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {"type": "string", "description": "Filter by state (open, closed, all)", "default": "open"},
                    "labels": {"type": "array", "description": "Filter by labels", "items": {"type": "string"}},
                    "perPage": {"type": "integer", "description": "Results per page (max 100)", "default": 30}
                },
                "required": ["owner", "repo"]
            }
        },
        {
            "name": "create_pr",
            "description": "Create a new pull request in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "title": {"type": "string", "description": "PR title"},
                    "body": {"type": "string", "description": "PR description"},
                    "head": {"type": "string", "description": "Branch containing changes"},
                    "base": {"type": "string", "description": "Branch to merge into"},
                    "draft": {"type": "boolean", "description": "Create as draft PR", "default": False}
                },
                "required": ["owner", "repo", "title", "head", "base"]
            }
        },
        {
            "name": "search_code",
            "description": "Fast and precise code search across ALL GitHub repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query using GitHub's code search syntax"},
                    "order": {"type": "string", "description": "Sort order (asc, desc)", "default": "desc"},
                    "perPage": {"type": "integer", "description": "Results per page (max 100)", "default": 30},
                    "sort": {"type": "string", "description": "Sort field (indexed only)", "default": "indexed"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_commit",
            "description": "Get details for a commit from a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "sha": {"type": "string", "description": "Commit SHA, branch name, or tag name"}
                },
                "required": ["owner", "repo", "sha"]
            }
        },
        {
            "name": "list_pull_requests",
            "description": "List pull requests in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "state": {"type": "string", "description": "Filter by state (open, closed, all)", "default": "open"},
                    "sort": {"type": "string", "description": "Sort by (created, updated, popularity, long-running)", "default": "created"},
                    "direction": {"type": "string", "description": "Sort direction (asc, desc)", "default": "desc"}
                },
                "required": ["owner", "repo"]
            }
        }
    ],
    "filesystem": [
        {
            "name": "read_file",
            "description": "Read the complete contents of a file from the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "head": {"type": "integer", "description": "If provided, returns only the first N lines"},
                    "tail": {"type": "integer", "description": "If provided, returns only the last N lines"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "list_directory",
            "description": "Get a detailed listing of all files and directories",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory to list"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "search_files",
            "description": "Recursively search for files and directories matching a pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to search in"},
                    "pattern": {"type": "string", "description": "Glob-style pattern to match files"},
                    "excludePatterns": {"type": "array", "description": "Patterns to exclude", "items": {"type": "string"}, "default": []}
                },
                "required": ["path", "pattern"]
            }
        },
        {
            "name": "get_file_info",
            "description": "Retrieve detailed metadata about a file or directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file or directory"}
                },
                "required": ["path"]
            }
        }
    ],
    "fetch": [
        {
            "name": "fetch_url",
            "description": "Fetch content from a specified URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch content from"},
                    "format": {"type": "string", "description": "Output format (text, markdown, html)", "default": "markdown"},
                    "max_length": {"type": "integer", "description": "Maximum number of characters to return", "default": 5000},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
                },
                "required": ["url"]
            }
        },
        {
            "name": "fetch_markdown",
            "description": "Fetch a website and return its contents converted to Markdown",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                    "max_length": {"type": "integer", "description": "Maximum characters to return", "default": 5000},
                    "headers": {"type": "object", "description": "Optional headers to include"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "fetch_readable",
            "description": "Fetch website content parsed by Mozilla Readability, converted to Markdown",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                    "max_length": {"type": "integer", "description": "Maximum characters to return", "default": 5000}
                },
                "required": ["url"]
            }
        }
    ],
    "git": [
        {
            "name": "git_status",
            "description": "Shows the working tree status",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to Git repository"}
                },
                "required": ["repo_path"]
            }
        },
        {
            "name": "git_log",
            "description": "Shows the commit logs",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to Git repository"},
                    "max_count": {"type": "integer", "description": "Maximum number of commits to show", "default": 10}
                },
                "required": ["repo_path"]
            }
        },
        {
            "name": "git_diff",
            "description": "Shows differences between branches or commits",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to Git repository"},
                    "target": {"type": "string", "description": "Target branch or commit to compare with"}
                },
                "required": ["repo_path", "target"]
            }
        },
        {
            "name": "git_show",
            "description": "Shows the contents of a commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to Git repository"},
                    "revision": {"type": "string", "description": "The revision to show (commit hash, branch, tag)"}
                },
                "required": ["repo_path", "revision"]
            }
        }
    ],
    "sequential-thinking": [
        {
            "name": "think",
            "description": "Dynamic and reflective problem-solving through thoughts",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "Current thinking step"},
                    "nextThoughtNeeded": {"type": "boolean", "description": "Whether another thought step is needed"},
                    "thoughtNumber": {"type": "integer", "description": "Current thought number"},
                    "totalThoughts": {"type": "integer", "description": "Estimated total thoughts needed"},
                    "isRevision": {"type": "boolean", "description": "Whether this revises previous thinking", "default": False},
                    "needsMoreThoughts": {"type": "boolean", "description": "If more thoughts are needed", "default": False}
                },
                "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
            }
        }
    ],
    "context7": [
        {
            "name": "query_docs",
            "description": "Retrieves and queries up-to-date documentation and code examples",
            "parameters": {
                "type": "object",
                "properties": {
                    "libraryId": {"type": "string", "description": "Context7-compatible library ID"},
                    "query": {"type": "string", "description": "The question or task you need help with"}
                },
                "required": ["libraryId", "query"]
            }
        },
        {
            "name": "resolve_library_id",
            "description": "Resolves a package/product name to a Context7-compatible library ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "libraryName": {"type": "string", "description": "Library name to search for"},
                    "query": {"type": "string", "description": "The task you need help with"}
                },
                "required": ["libraryName", "query"]
            }
        }
    ],
    "trigger-guardian": [
        {
            "name": "register_trigger",
            "description": "Register a trigger phrase with callback action",
            "parameters": {
                "type": "object",
                "properties": {
                    "phrase": {"type": "string", "description": "The trigger phrase to register"},
                    "description": {"type": "string", "description": "Human-readable description", "default": ""},
                    "handler": {"type": "string", "description": "Handler type (callback, skill, function, workflow)", "default": "callback"},
                    "pattern_type": {"type": "string", "description": "Matching pattern (exact, prefix, regex)", "default": "exact"}
                },
                "required": ["phrase"]
            }
        },
        {
            "name": "list_triggers",
            "description": "Lists all registered triggers",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "check_trigger",
            "description": "Checks if input matches any registered trigger",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_text": {"type": "string", "description": "The input string to check"}
                },
                "required": ["input_text"]
            }
        }
    ],
    "nx-mind": [
        {
            "name": "get_mind_state",
            "description": "Returns current MIND state including project, phase, and active tasks",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "update_mind_state",
            "description": "Updates MIND state with new information",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project name to set"},
                    "phase": {"type": "string", "description": "Current phase (e.g., 1-analysis, 2-planning)"},
                    "active_tasks": {"type": "array", "description": "List of active tasks", "items": {"type": "string"}},
                    "context": {"type": "object", "description": "Additional context key-value pairs"},
                    "clear_context": {"type": "boolean", "description": "Whether to clear existing context", "default": False}
                },
                "required": []
            }
        },
        {
            "name": "get_session_history",
            "description": "Returns history of past sessions with summaries",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of sessions to return", "default": 10}
                },
                "required": []
            }
        }
    ],
    "athena-context": [
        {
            "name": "query_unified_memory",
            "description": "Query the unified memory router for cross-source memory search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_active_context",
            "description": "Returns current active context from memory bank",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_product_context",
            "description": "Returns product context (identity/soul) from memory bank",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_user_context",
            "description": "Returns user context from memory bank",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "inject_context",
            "description": "Writes context into session for prompt injection",
            "parameters": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "description": "Which context to inject (active, product, user, all)", "default": "active"},
                    "output_path": {"type": "string", "description": "Optional path to write the injected context"}
                },
                "required": []
            }
        }
    ],
    "unified-memory": [
        {
            "name": "search_memories",
            "description": "Search across all memory sources (Athena, session, file content, MCP)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
                    "rerank": {"type": "boolean", "description": "Apply LLM-based reranking", "default": False},
                    "strict": {"type": "boolean", "description": "Filter out low-confidence results", "default": False}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_memory_stats",
            "description": "Get memory system statistics from unified memory",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "recall_session",
            "description": "Recall session context from memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of lines from the end of the log", "default": 50},
                    "session_id": {"type": "string", "description": "Specific session ID to recall"}
                },
                "required": []
            }
        },
        {
            "name": "find_context",
            "description": "Find relevant context for a specific task",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task description"},
                    "context_type": {"type": "string", "description": "Type of context (all, semantic, episodic, session)", "default": "all"}
                },
                "required": ["task"]
            }
        }
    ],
    "intelligent-router": [
        {
            "name": "route_task",
            "description": "Get optimal routing decision for a task",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {"type": "string", "description": "Description of the task"}
                },
                "required": ["task_description"]
            }
        },
        {
            "name": "record_delegation_outcome",
            "description": "Log delegation outcome for learning",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Unique task identifier"},
                    "task_description": {"type": "string", "description": "Description of the task"},
                    "level": {"type": "integer", "description": "Complexity level (1-5)"},
                    "agent": {"type": "string", "description": "Agent used"},
                    "success": {"type": "boolean", "description": "Whether the task succeeded"},
                    "latency_ms": {"type": "integer", "description": "Latency in milliseconds"},
                    "tokens_used": {"type": "integer", "description": "Number of tokens used"}
                },
                "required": ["task_id", "task_description", "level", "agent", "success"]
            }
        }
    ],
    "grep": [
        {
            "name": "searchGitHub",
            "description": "Find real-world code examples from over a million public GitHub repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The literal code pattern to search for"},
                    "language": {"type": "array", "description": "Filter by programming language", "items": {"type": "string"}},
                    "repo": {"type": "string", "description": "Filter by repository"},
                    "path": {"type": "string", "description": "Filter by file path"},
                    "matchCase": {"type": "boolean", "description": "Case sensitive search", "default": False},
                    "matchWholeWords": {"type": "boolean", "description": "Match whole words only", "default": False},
                    "useRegexp": {"type": "boolean", "description": "Interpret query as regular expression", "default": False}
                },
                "required": ["query"]
            }
        }
    ]
}


class MCPToolRegistry:
    """
    Registry for MCP tools that converts MCP tool definitions to OpenAI-compatible
    tool schema format for use with Rosetta Stone.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the registry.
        
        Args:
            config_path: Path to opencode.json. If None, uses default location.
        """
        self.config_path = config_path or self._find_config()
        self._mcp_servers: Dict[str, Dict] = {}
        self._tool_cache: Optional[List[Dict]] = None
        self._load_mcp_config()
        logger.info(f"MCP Tool Registry initialized with {len(self._mcp_servers)} MCP servers")

    def _find_config(self) -> str:
        """Find opencode.json in the workspace."""
        # Try current directory first
        config_path = Path("opencode.json")
        if config_path.exists():
            return str(config_path)
        
        # Try workspace root
        workspace_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
        config_path = workspace_root / "opencode.json"
        if config_path.exists():
            return str(config_path)
        
        raise FileNotFoundError("Could not find opencode.json")

    def _load_mcp_config(self):
        """Load MCP configuration from opencode.json."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            mcp_config = config.get("mcp", {})
            self._mcp_servers = mcp_config
            logger.debug(f"Loaded MCP config: {list(mcp_config.keys())}")
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            self._mcp_servers = {}

    def _convert_to_openai_schema(self, tool_def: Dict) -> Dict:
        """Convert a tool definition to OpenAI-compatible schema format.
        
        Args:
            tool_def: Tool definition with name, description, parameters
            
        Returns:
            OpenAI-compatible tool schema: {"type": "function", "function": {...}}
        """
        return {
            "type": "function",
            "function": {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": tool_def.get("parameters", {"type": "object", "properties": {}})
            }
        }

    def _get_tools_for_mcp(self, mcp_name: str) -> List[Dict]:
        """Get tool definitions for a specific MCP server.
        
        Args:
            mcp_name: Name of the MCP server
            
        Returns:
            List of tool definitions in OpenAI schema format
        """
        # Check if MCP has explicit tool definitions in config
        # For now, use common definitions based on MCP capabilities
        if mcp_name in MCP_TOOL_DEFINITIONS:
            return [
                self._convert_to_openai_schema(tool_def)
                for tool_def in MCP_TOOL_DEFINITIONS[mcp_name]
            ]
        
        logger.warning(f"No tool definitions found for MCP: {mcp_name}")
        return []

    def get_tools(self) -> List[Dict]:
        """Get all available tools in OpenAI-compatible format.
        
        Returns:
            List of tool definitions ready for Rosetta Stone
        """
        if self._tool_cache is not None:
            return self._tool_cache
        
        all_tools = []
        for mcp_name in self._mcp_servers.keys():
            tools = self._get_tools_for_mcp(mcp_name)
            all_tools.extend(tools)
        
        self._tool_cache = all_tools
        logger.info(f"Loaded {len(all_tools)} tools from {len(self._mcp_servers)} MCP servers")
        return all_tools

    def get_tool(self, name: str) -> Optional[Dict]:
        """Get a specific tool by name.
        
        Args:
            name: Tool name to find
            
        Returns:
            Tool definition in OpenAI schema format, or None if not found
        """
        tools = self.get_tools()
        for tool in tools:
            if tool.get("function", {}).get("name") == name:
                return tool
        return None

    def list_tools(self) -> List[str]:
        """List all available tool names.
        
        Returns:
            List of tool names
        """
        tools = self.get_tools()
        return [tool.get("function", {}).get("name", "?") for tool in tools]

    def get_tools_by_mcp(self, mcp_name: str) -> List[Dict]:
        """Get tools for a specific MCP server.
        
        Args:
            mcp_name: Name of the MCP server
            
        Returns:
            List of tool definitions in OpenAI schema format
        """
        return self._get_tools_for_mcp(mcp_name)

    def reload(self):
        """Reload MCP configuration and clear cache."""
        self._tool_cache = None
        self._load_mcp_config()
        logger.info("MCP Tool Registry cache cleared and config reloaded")


# Singleton instance for easy access
_registry: Optional[MCPToolRegistry] = None


def get_registry() -> MCPToolRegistry:
    """Get the singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry


def get_tools() -> List[Dict]:
    """Get all available tools (convenience function)."""
    return get_registry().get_tools()


def get_tool(name: str) -> Optional[Dict]:
    """Get a specific tool by name (convenience function)."""
    return get_registry().get_tool(name)


def list_tools() -> List[str]:
    """List all available tool names (convenience function)."""
    return get_registry().list_tools()
