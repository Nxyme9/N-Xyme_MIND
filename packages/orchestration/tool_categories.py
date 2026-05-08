#!/usr/bin/env python3
"""Tool Categories - Category-based tool system for efficient context loading.

This module provides a categorization system that splits available tools into
categories for efficient context loading, enabling hybrid tool awareness.

Research: Category-based injection saves 60-80% context tokens.

Categories:
- EXECUTION: File operations, bash commands, directory management
- SEARCH: Code search, grep, AST patterns
- GIT: Version control operations
- MEMORY: Context and memory retrieval
- QUALITY: Type checking, linting, validation
- INTEGRATION: GitHub, Notion, Obsidian, Telegram
- ORCHESTRATION: Task delegation, background operations
"""

from typing import Dict, List, Optional

# =============================================================================
# TOOL CATEGORIES - Maps categories to actual tool names from MCP servers
# =============================================================================

TOOL_CATEGORIES: Dict[str, List[str]] = {
    "EXECUTION": [
        # Filesystem MCP tools
        "read_file",
        "write_file",
        "list_directory",
        # Note: bash is handled externally (not a registered MCP tool)
    ],
    "SEARCH": [
        # Note: grep is external, not in MCP - keeping for reference
        "glob",
        # AST grep tools (if available)
        "ast_grep_search",
        "ast_grep_replace",
    ],
    "GIT": [
        "git_status",
        "git_log",
        "git_diff",
        "git_branch",
    ],
    "MEMORY": [
        # Unified memory tools
        "memory_search",
        "memory_write",
        "unified-memory_search",
        "unified-memory_memory_write",
        # Athena context
        "athena_smart_search",
        "get_active_context",
        "get_user_context",
    ],
    "QUALITY": [
        # Quality gates
        "run_typecheck",
        "run_lint",
        "run_format",
        "run_tests",
        "run_secrets_scan",
        "run_placeholder_check",
        "run_deps_check",
        "run_sast",
    ],
    "INTEGRATION": [
        # GitHub MCP
        "github_search_repositories",
        "github_list_issues",
        "github_create_issue",
        "github_get_issue",
        "github_create_pull_request",
        "github_get_pull_request",
        "github_list_pull_requests",
        # Notion MCP
        "notion_API-get-user",
        "notion_API-get-users",
        "notion_API-post-page",
        "notion_API-retrieve-a-page",
        "notion_API-query-data-source",
        # Obsidian MCP
        "obsidian_obsidian_list_files_in_vault",
        "obsidian_obsidian_get_file_contents",
        "obsidian_obsidian_simple_search",
        # Telegram MCP
        "telegram_send_message",
        "telegram_get_messages",
    ],
    "ORCHESTRATION": [
        # Orchestration MCP tools
        "orchestration_spawn",
        "orchestration_task_status",
        "orchestration_tools_list",
        "orchestration_get_session_state",
        # Learning engine routing
        "route_task",
        "record_outcome",
        "intelligence_route",
        "intelligence_score_complexity",
        # Trigger guardian
        "trigger-guardian_check_trigger",
        "trigger-guardian_register_trigger",
    ],
}

# =============================================================================
# CATEGORY KEYWORDS - Positive and negative activation rules
# =============================================================================

CATEGORY_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "EXECUTION": {
        "positive": [
            "run",
            "execute",
            "create",
            "write",
            "edit",
            "delete",
            "modify",
            "change",
            "update",
            "replace",
            "add",
            "remove",
            "mkdir",
            "touch",
            "copy",
            "move",
            "rename",
            "install",
            "build",
            "compile",
            "test",
            "deploy",
            "start",
            "stop",
            "restart",
            "init",
            "setup",
            "configure",
        ],
        "negative": [
            "find",
            "search",
            "look for",
            "where is",
            "grep",
            "commit",
            "push",
            "pull",
            "merge",
            "branch",
            "remember",
            "save",
            "recall",
            "context",
            "check",
            "verify",
            "validate",
            "lint",
            "typecheck",
            "issue",
            "pr",
            "repo",
            "github",
        ],
    },
    "SEARCH": {
        "positive": [
            "find",
            "search",
            "where",
            "grep",
            "look for",
            "locate",
            "search for",
            "find all",
            "find where",
            "search in",
            "list all",
            "show me",
            "get all",
            "filter",
            "match",
            "scan",
            "query",
            "explore",
            "discover",
            "enumerate",
            "trace",
            "inspect",
            "lookup",
            "find files",
        ],
        "negative": [
            "run",
            "execute",
            "create",
            "write",
            "edit",
            "commit",
            "push",
            "pull",
            "merge",
            "remember",
            "save",
            "context",
        ],
    },
    "GIT": {
        "positive": [
            "commit",
            "push",
            "pull",
            "fetch",
            "merge",
            "branch",
            "rebase",
            "stash",
            "checkout",
            "diff",
            "log",
            "status",
            "add",
            "reset",
            "cherry-pick",
            "tag",
            "clone",
            "git",
            "version control",
            "vcs",
        ],
        "negative": [
            "find",
            "search",
            "grep",
            "run",
            "execute",
            "create",
            "write",
            "edit",
            "remember",
            "save",
            "context",
            "check",
            "verify",
            "validate",
        ],
    },
    "MEMORY": {
        "positive": [
            "remember",
            "save",
            "recall",
            "context",
            "session",
            "retrieve",
            "load",
            "store",
            "persist",
            "cache",
            "previous",
            "past",
            "history",
            "knowledge",
            "forget",
            "clear memory",
            "reset context",
            "memory",
            "learn",
            "record",
            "note",
            "log",
            "track",
            "accumulate",
            "retain",
        ],
        "negative": [
            "find",
            "search",
            "grep",
            "run",
            "execute",
            "create",
            "write",
            "edit",
            "commit",
            "push",
            "pull",
            "merge",
            "check",
            "verify",
            "validate",
            "lint",
        ],
    },
    "QUALITY": {
        "positive": [
            "check",
            "verify",
            "validate",
            "lint",
            "typecheck",
            "format",
            "test",
            "quality",
            "security",
            "scan",
            "type check",
            "prettier",
            "eslint",
            "mypy",
            "build",
            "compile",
            "type",
            "style",
            "ensure",
            "assure",
            "confirm",
            "inspect",
            "audit",
            "review",
            "sanity",
        ],
        "negative": [
            "find",
            "search",
            "grep",
            "run",
            "execute",
            "create",
            "write",
            "edit",
            "commit",
            "push",
            "pull",
            "merge",
            "remember",
            "save",
            "context",
        ],
    },
    "INTEGRATION": {
        "positive": [
            "issue",
            "issues",
            "pr",
            "pull request",
            "repo",
            "repository",
            "github",
            "notion",
            "obsidian",
            "telegram",
            "create issue",
            "list issues",
            "create pr",
            "send message",
            "notify",
            "webhook",
            "sync",
            "integrate",
            "connect",
            "import",
            "export",
            "publish",
            "deploy",
            "push",
            "pull",
            "merge",
            "branch",
            "fork",
            "clone",
            "star",
            "watch",
        ],
        "negative": [
            "find",
            "search",
            "grep",
            "run",
            "execute",
            "create file",
            "write file",
            "edit",
            "commit",
            "push",
            "pull",
            "merge",
            "remember",
            "save",
            "context",
            "check",
            "verify",
            "validate",
            "lint",
        ],
    },
    "ORCHESTRATION": {
        "positive": [
            "delegate",
            "spawn",
            "dispatch",
            "route",
            "task",
            "agent",
            "subagent",
            "background",
            "async",
            "spawn agent",
            "delegate to",
            "route to",
            "parallel",
            "concurrent",
            "fire",
            "orchestrate",
            "coordinate",
            "manage",
            "schedule",
            "queue",
            "pipeline",
            "workflow",
            "automate",
        ],
        "negative": [
            "find",
            "search",
            "grep",
            "create file",
            "write file",
            "edit file",
            "commit",
            "push",
            "pull",
            "remember",
            "save",
            "context",
            "check",
            "verify",
            "validate",
        ],
    },
}

# =============================================================================
# CATEGORY DESCRIPTIONS - For building context manifests
# =============================================================================

CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "EXECUTION": "File operations, bash commands, directory management - use when user wants to run commands, create/modify files, or execute scripts.",
    "SEARCH": "Code search, grep, glob, AST patterns - use when user wants to find files, search code, or locate patterns.",
    "GIT": "Version control operations - use when user wants to commit, push, pull, merge, or check git status.",
    "MEMORY": "Context and memory retrieval - use when user wants to recall past sessions, load context, or save information.",
    "QUALITY": "Type checking, linting, validation - use when user wants to verify code quality, run tests, or validate types.",
    "INTEGRATION": "External services - use when user wants to interact with GitHub, Notion, Obsidian, or Telegram.",
    "ORCHESTRATION": "Task delegation and routing - use when user wants to spawn agents, route tasks, or manage orchestration.",
}

# =============================================================================
# CATEGORY TOOL DESCRIPTIONS - Detailed descriptions for each tool
# =============================================================================

CATEGORY_TOOL_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    "EXECUTION": {
        "read_file": "Read a file from the local filesystem. Use for: examining code, configs, or text files. NOT for: binary files or executing code.",
        "write_file": "Write content to a file (creates or overwrites). Use for: creating new files, updating configs, or writing code. WARNING: overwrites existing files.",
        "list_directory": "List files and directories in a path. Use for: exploring directory structure or finding files.",
    },
    "SEARCH": {
        "glob": "Find files matching a pattern. Use for: locating files by name patterns like **/*.py.",
        "ast_grep_search": "Search code patterns using AST-aware matching. Use for: finding specific code patterns across the codebase.",
        "ast_grep_replace": "Replace code patterns using AST-aware rewriting. Use for: making structural code changes across files.",
    },
    "GIT": {
        "git_status": "Shows the working tree status. Use for: checking modified/staged/untracked files before commit.",
        "git_log": "Shows the commit logs. Use for: viewing commit history or understanding project timeline.",
        "git_diff": "Shows differences between branches or commits. Use for: comparing code changes or reviewing modifications.",
        "git_branch": "Shows Git branches. Use for: listing branches or seeing current branch.",
    },
    "MEMORY": {
        "memory_search": "Search across all memory sources (Athena, session, file content, MCP). Use for: finding previously stored information.",
        "memory_write": "Write memory using MemoryManager. Use for: storing important information or session context.",
        "athena_smart_search": "Search Athena's knowledge base using hybrid RAG. Use for: finding project-specific knowledge or code patterns.",
        "get_active_context": "Get current active context from memory bank. Use for: understanding current project state or session goals.",
        "get_user_context": "Get user context from memory bank. Use for: understanding user preferences or communication style.",
    },
    "QUALITY": {
        "run_typecheck": "Run TypeScript type check (gate-1). Use for: validating TypeScript types before commit or deployment.",
        "run_lint": "Run linting (gate-2). Use for: checking code style or finding potential errors.",
        "run_format": "Run formatting check (gate-3). Use for: verifying code formatting conventions.",
        "run_tests": "Run test suite (gate-4). Use for: executing tests to verify code correctness.",
        "run_secrets_scan": "Scan for secrets (gate-5). Use for: detecting exposed credentials or API keys.",
        "run_placeholder_check": "Check for placeholders (gate-6). Use for: finding TODO/FIXME/placeholder markers.",
        "run_deps_check": "Check dependencies (gate-9). Use for: verifying dependency versions and security.",
        "run_sast": "Run SAST with bandit (gate-10). Use for: static application security testing.",
    },
    "INTEGRATION": {
        "github_search_repositories": "Find GitHub repositories by name or description. Use for: discovering libraries or example projects.",
        "github_list_issues": "List issues in a GitHub repository. Use for: viewing open/closed issues or checking project status.",
        "github_create_issue": "Create a new issue in a GitHub repository. Use for: reporting bugs or requesting features.",
        "notion_API-post-page": "Create a page in Notion. Use for: adding tasks or documentation to Notion.",
        "notion_API-query-data-source": "Query a Notion database. Use for: searching Notion for information.",
        "obsidian_obsidian_get_file_contents": "Read a file from Obsidian vault. Use for: accessing notes or documentation.",
        "obsidian_obsidian_simple_search": "Search documents in Obsidian vault. Use for: finding notes or information.",
        "telegram_send_message": "Send a text message to Telegram. Use for: sending notifications or updates.",
    },
    "ORCHESTRATION": {
        "orchestration_spawn": "Spawn an agent task. Use for: delegating work to subagents or running parallel tasks.",
        "orchestration_task_status": "Get status of a task. Use for: checking progress of spawned tasks.",
        "route_task": "Get routing recommendation for a task using Q-Learning. Use for: determining which agent to use.",
        "intelligence_route": "Route a task to the optimal agent. Use for: intelligent task delegation.",
        "trigger-guardian_check_trigger": "Check if input matches any registered trigger. Use for: detecting command patterns.",
    },
}

# =============================================================================
# FUNCTIONS
# =============================================================================


def get_relevant_categories(user_message: str) -> List[str]:
    """Detect relevant categories based on user message keywords.

    Args:
        user_message: The user's input message to analyze.

    Returns:
        List of category names that are relevant to the message.
        Sorted by relevance (most relevant first).
    """
    message_lower = user_message.lower()
    category_scores: Dict[str, float] = {}

    for category, rules in CATEGORY_KEYWORDS.items():
        positive_matches = 0
        negative_matches = 0

        # Check positive keywords
        for keyword in rules["positive"]:
            if keyword in message_lower:
                positive_matches += 1

        # Check negative keywords
        for keyword in rules["negative"]:
            if keyword in message_lower:
                negative_matches += 1

        # Calculate score: positive matches minus penalty for negative matches
        score = positive_matches - (negative_matches * 0.5)
        category_scores[category] = score

    # Sort by score descending and filter out zero/negative scores
    sorted_categories = sorted(
        category_scores.items(), key=lambda x: x[1], reverse=True
    )

    # Return categories with positive scores
    relevant = [cat for cat, score in sorted_categories if score > 0]

    # If no categories matched, return all categories (fallback)
    if not relevant:
        return list(TOOL_CATEGORIES.keys())

    return relevant


def get_tools_for_category(category: str) -> List[str]:
    """Get tool names for a specific category.

    Args:
        category: The category name to get tools for.

    Returns:
        List of tool names in the category.
        Empty list if category doesn't exist.
    """
    return TOOL_CATEGORIES.get(category, [])


def get_tool_description(category: str, tool: str) -> Optional[str]:
    """Get description for a specific tool in a category.

    Args:
        category: The category name.
        tool: The tool name.

    Returns:
        Tool description or None if not found.
    """
    if category in CATEGORY_TOOL_DESCRIPTIONS:
        return CATEGORY_TOOL_DESCRIPTIONS[category].get(tool)
    return None


def build_category_manifest(categories: List[str]) -> str:
    """Build a prompt section describing relevant tools for the categories.

    This generates a context section that can be injected into prompts
    to inform the model about available tools for the current task.

    Args:
        categories: List of category names to include.

    Returns:
        Formatted string describing the categories and their tools.
    """
    if not categories:
        return "# Available Tools\n\nNo specific tools selected."

    lines = [
        "# Available Tools (Category-Based Context)",
        "",
        "The following tools are relevant to your current task:",
        "",
    ]

    for category in categories:
        if category not in TOOL_CATEGORIES:
            continue

        # Add category description
        desc = CATEGORY_DESCRIPTIONS.get(category, "No description available.")
        lines.append(f"## {category}")
        lines.append(f"_{desc}_")
        lines.append("")

        # Add tools in category
        tools = TOOL_CATEGORIES[category]
        if tools:
            lines.append("Available tools:")
            for tool in tools:
                tool_desc = get_tool_description(category, tool)
                if tool_desc:
                    # Truncate long descriptions
                    short_desc = tool_desc.split(".")[0] + "."
                    lines.append(f"  - `{tool}`: {short_desc}")
                else:
                    lines.append(f"  - `{tool}`")
            lines.append("")
        else:
            lines.append("  (No specific tools defined)")
            lines.append("")

    return "\n".join(lines)


def get_all_categories() -> List[str]:
    """Get list of all available categories.

    Returns:
        List of all category names.
    """
    return list(TOOL_CATEGORIES.keys())


def get_category_for_tool(tool_name: str) -> Optional[str]:
    """Find which category a tool belongs to.

    Args:
        tool_name: The name of the tool.

    Returns:
        Category name or None if tool not found in any category.
    """
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return category
    return None


def validate_categories(categories: List[str]) -> bool:
    """Validate that all category names are valid.

    Args:
        categories: List of category names to validate.

    Returns:
        True if all categories are valid.
    """
    valid_categories = set(TOOL_CATEGORIES.keys())
    return all(cat in valid_categories for cat in categories)


# =============================================================================
# MAIN / TEST
# =============================================================================

if __name__ == "__main__":
    # Test the module
    print("=== Tool Categories Test ===\n")

    # Test 1: Get relevant categories
    test_messages = [
        "Find all Python files in the project",
        "Commit my changes and push to main",
        "Remember that the user prefers dark mode",
        "Run the linter and type checker",
        "Create a new issue on GitHub",
        "Spawn an agent to handle this",
    ]

    for msg in test_messages:
        categories = get_relevant_categories(msg)
        print(f"Message: '{msg}'")
        print(f"  Categories: {categories}")
        print()

    # Test 2: Get tools for category
    print("=== Tools for EXECUTION ===")
    print(get_tools_for_category("EXECUTION"))
    print()

    # Test 3: Build manifest
    print("=== Category Manifest ===")
    manifest = build_category_manifest(["EXECUTION", "SEARCH"])
    print(manifest[:500] + "...")
    print()

    # Test 4: Get category for tool
    print("=== Category for 'git_status' ===")
    print(get_category_for_tool("git_status"))
    print()

    print("=== All categories ===")
    print(get_all_categories())
