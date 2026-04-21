#!/usr/bin/env python3
"""
Rosetta Registry - Tool Name to MCP Function Mapper

Maps Rosetta-trained tool names to actual MCP functions.
This allows Rosetta to actually EXECUTE tools, not just generate JSON.
"""

import json
import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("rosetta_registry")

# =============================================================================
# Tool Registry
# =============================================================================

# Map of Rosetta tool names → (MCP namespace, function_name, description)
TOOL_REGISTRY: Dict[str, Dict[str, str]] = {
    # Memory tools
    "memory_search": {
        "namespace": "unified-memory",
        "function": "search_memories",
        "description": "Search across all memory sources",
        "params": {"query": "str", "limit": "int", "strict": "bool"},
    },
    "memory_write": {
        "namespace": "unified-memory",
        "function": "create_memory",
        "description": "Create a new memory entry",
        "params": {"content": "str", "kind": "str", "scope": "str"},
    },
    "memory_recall": {
        "namespace": "memory",
        "function": "recall_session",
        "description": "Recall session context",
        "params": {"session_id": "str", "limit": "int"},
    },
    
    # Filesystem tools
    "read_file": {
        "namespace": "filesystem",
        "function": "read_file",
        "description": "Read a file from the local filesystem",
        "params": {"filePath": "str", "offset": "int", "limit": "int"},
    },
    "write_file": {
        "namespace": "filesystem",
        "function": "write_file",
        "description": "Write content to a file",
        "params": {"filePath": "str", "content": "str"},
    },
    "edit_file": {
        "namespace": "filesystem",
        "function": "edit_file",
        "description": "Edit a file using string replacement",
        "params": {"filePath": "str", "oldString": "str", "newString": "str"},
    },
    "glob": {
        "namespace": "filesystem",
        "function": "glob",
        "description": "Find files matching a pattern",
        "params": {"pattern": "str", "path": "str"},
    },
    "list_directory": {
        "namespace": "filesystem",
        "function": "list_directory",
        "description": "List directory contents",
        "params": {"path": "str"},
    },
    
    # Git tools
    "git_status": {
        "namespace": "git",
        "function": "git_status",
        "description": "Show working tree status",
        "params": {},
    },
    "git_log": {
        "namespace": "git",
        "function": "git_log",
        "description": "Show commit logs",
        "params": {"max_count": "int"},
    },
    "git_diff": {
        "namespace": "git",
        "function": "git_diff",
        "description": "Show changes",
        "params": {"file_path": "str"},
    },
    
    # GitHub tools
    "github_search_repos": {
        "namespace": "github",
        "function": "search_repositories",
        "description": "Search GitHub repositories",
        "params": {"query": "str"},
    },
    "github_list_issues": {
        "namespace": "github",
        "function": "list_issues",
        "description": "List issues in a repository",
        "params": {"owner": "str", "repo": "str", "state": "str"},
    },
    "github_search_code": {
        "namespace": "github",
        "function": "search_code",
        "description": "Search code on GitHub",
        "params": {"q": "str"},
    },
    "github_create_issue": {
        "namespace": "github",
        "function": "create_issue",
        "description": "Create a new issue",
        "params": {"owner": "str", "repo": "str", "title": "str", "body": "str"},
    },
    
    # Web tools
    "fetch_url": {
        "namespace": "fetch",
        "function": "fetch_fetch_readable",
        "description": "Fetch URL and extract main content",
        "params": {"url": "str", "max_length": "int"},
    },
    "web_search": {
        "namespace": "websearch",
        "function": "web_search_exa",
        "description": "Search the web",
        "params": {"query": "str", "numResults": "int"},
    },
    "context7_query_docs": {
        "namespace": "context7",
        "function": "query_docs",
        "description": "Query documentation",
        "params": {"libraryId": "str", "query": "str"},
    },
    "context7_resolve": {
        "namespace": "context7",
        "function": "resolve-library-id",
        "description": "Resolve a library name to Context7 ID",
        "params": {"query": "str", "libraryName": "str"},
    },
    
    # Database tools
    "sqlite_query": {
        "namespace": "sqlite",
        "function": "sqlite_query",
        "description": "Execute a SQL SELECT query",
        "params": {"sql": "str", "db_path": "str"},
    },
    "sqlite_list_tables": {
        "namespace": "sqlite",
        "function": "sqlite_list_tables",
        "description": "List tables in database",
        "params": {"db_path": "str"},
    },
    
    # System tools
    "get_active_context": {
        "namespace": "nx-context",
        "function": "get_active_context",
        "description": "Get current active context",
        "params": {},
    },
    "get_product_context": {
        "namespace": "nx-context",
        "function": "get_product_context",
        "description": "Get product context",
        "params": {},
    },
    "get_user_context": {
        "namespace": "nx-context",
        "function": "get_user_context",
        "description": "Get user context",
        "params": {},
    },
    "get_constraints": {
        "namespace": "nx-context",
        "function": "get_constraints",
        "description": "Get behavioral constraints",
        "params": {},
    },
    
    # Learning/Routing tools
    "route_task": {
        "namespace": "unified-memory",
        "function": "route_task",
        "description": "Route task to optimal agent",
        "params": {"task_description": "str"},
    },
    "record_outcome": {
        "namespace": "unified-memory",
        "function": "record_delegation_outcome",
        "description": "Record delegation outcome",
        "params": {"task_id": "str", "task_description": "str", "level": "int", "agent": "str", "success": "bool", "latency_ms": "int", "tokens_used": "int"},
    },
    
    # Thinking tools
    "sequential_thinking": {
        "namespace": "sequential-thinking",
        "function": "sequentialthinking",
        "description": "Chain of thought reasoning",
        "params": {"thought": "str", "nextThoughtNeeded": "bool", "thoughtNumber": "int", "totalThoughts": "int"},
    },
    
    # Browser tools
    "browser_navigate": {
        "namespace": "playwright",
        "function": "playwright_navigate",
        "description": "Navigate to URL",
        "params": {"url": "str"},
    },
    "browser_click": {
        "namespace": "playwright",
        "function": "playwright_click",
        "description": "Click element",
        "params": {"selector": "str"},
    },
    "browser_fill": {
        "namespace": "playwright",
        "function": "playwright_fill",
        "description": "Fill form field",
        "params": {"selector": "str", "value": "str"},
    },
    "browser_screenshot": {
        "namespace": "playwright",
        "function": "playwright_screenshot",
        "description": "Take screenshot",
        "params": {"path": "str", "full_page": "bool"},
    },
    
    # Code intelligence
    "lsp_diagnostics": {
        "namespace": "lsp",
        "function": "lsp_diagnostics",
        "description": "Get LSP diagnostics",
        "params": {"filePath": "str", "severity": "str"},
    },
    "lsp_symbols": {
        "namespace": "lsp",
        "function": "lsp_symbols",
        "description": "Get file symbols",
        "params": {"filePath": "str", "scope": "str"},
    },
    "lsp_goto_definition": {
        "namespace": "lsp",
        "function": "lsp_goto_definition",
        "description": "Go to definition",
        "params": {"filePath": "str", "line": "int", "character": "int"},
    },
    
    # Brain/Tunnel tools
    "brain_navigate": {
        "namespace": "nx-brain",
        "function": "browser_navigate",
        "description": "Navigate browser",
        "params": {"url": "str"},
    },
    "brain_search": {
        "namespace": "nx-brain",
        "function": "memory_search_memories",
        "description": "Search memories",
        "params": {"query": "str", "limit": "int"},
    },
    "brain_route": {
        "namespace": "nx-brain",
        "function": "intelligence_route",
        "description": "Route task",
        "params": {"task_description": "str"},
    },
    
    # Session tools
    "session_list": {
        "namespace": "session",
        "function": "session_list",
        "description": "List sessions",
        "params": {"limit": "int"},
    },
    "session_read": {
        "namespace": "session",
        "function": "session_read",
        "description": "Read session messages",
        "params": {"session_id": "str", "limit": "int"},
    },
    "session_search": {
        "namespace": "session",
        "function": "session_search",
        "description": "Search sessions",
        "params": {"query": "str", "limit": "int"},
    },
    
    # Todo tools
    "todowrite": {
        "namespace": "todo",
        "function": "todowrite",
        "description": "Write todo list",
        "params": {"todos": "list"},
    },
    
    # Question tools
    "question_ask": {
        "namespace": "question",
        "function": "question",
        "description": "Ask user a question",
        "params": {"questions": "list"},
    },
    
    # Task tools
    "task_spawn": {
        "namespace": "task",
        "function": "task",
        "description": "Spawn a subagent task",
        "params": {"subagent_type": "str", "prompt": "str", "description": "str", "run_in_background": "bool", "load_skills": "list"},
    },
    
    # Skill tools
    "skill_load": {
        "namespace": "skill",
        "function": "skill",
        "description": "Load a skill",
        "params": {"name": "str", "user_message": "str"},
    },
    
    # Notion tools
    "notion_API-delete-a-block": {
        "namespace": "notion",
        "function": "delete_a_block",
        "description": "Delete a Notion block",
        "params": {"block_id": "str"},
    },
    "notion_API-post-search": {
        "namespace": "notion",
        "function": "post_search",
        "description": "Search Notion",
        "params": {"query": "str"},
    },
    "notion_API-get-block-children": {
        "namespace": "notion",
        "function": "get_block_children",
        "description": "Get Notion block children",
        "params": {"block_id": "str"},
    },
    "notion_API-retrieve-a-page": {
        "namespace": "notion",
        "function": "retrieve_a_page",
        "description": "Retrieve a Notion page",
        "params": {"page_id": "str"},
    },
    "notion_API-post-page": {
        "namespace": "notion",
        "function": "post_page",
        "description": "Create a Notion page",
        "params": {"parent": "dict", "properties": "dict"},
    },
    "notion_API-patch-page": {
        "namespace": "notion",
        "function": "patch_page",
        "description": "Update a Notion page",
        "params": {"page_id": "str", "properties": "dict"},
    },
    "notion_API-create-a-comment": {
        "namespace": "notion",
        "function": "create_a_comment",
        "description": "Create Notion comment",
        "params": {"parent": "dict", "rich_text": "list"},
    },
    "notion_API-retrieve-a-comment": {
        "namespace": "notion",
        "function": "retrieve_a_comment",
        "description": "Retrieve Notion comment",
        "params": {"block_id": "str"},
    },
    "notion_API-query-data-source": {
        "namespace": "notion",
        "function": "query_data_source",
        "description": "Query Notion database",
        "params": {"data_source_id": "str", "filter": "dict"},
    },
    
    # Telegram tools
    "telegram_send_message": {
        "namespace": "telegram",
        "function": "send_message",
        "description": "Send Telegram message",
        "params": {"text": "str", "chat_id": "str"},
    },
    "telegram_get_messages": {
        "namespace": "telegram",
        "function": "get_messages",
        "description": "Get Telegram messages",
        "params": {"chat_id": "str", "max_messages": "int"},
    },
    
    # Brain/Tunnel tools
    "nx_brain_tunnel_get_key": {
        "namespace": "nx-brain",
        "function": "tunnel_get_key",
        "description": "Get tunnel API key",
        "params": {"provider": "str"},
    },
    "nx_brain_memory_memory_search": {
        "namespace": "nx-brain",
        "function": "memory_search_memories",
        "description": "Brain memory search",
        "params": {"query": "str", "limit": "int"},
    },
    "nx_brain_memory_memory_write": {
        "namespace": "nx-brain",
        "function": "memory_memory_write",
        "description": "Brain memory write",
        "params": {"content": "str", "kind": "str"},
    },
    "nx_context_get_product_context": {
        "namespace": "nx-context",
        "function": "get_product_context",
        "description": "Get product context",
        "params": {},
    },
    "nx_context_get_active_context": {
        "namespace": "nx-context",
        "function": "get_active_context",
        "description": "Get active context",
        "params": {},
    },
    "nx_context_get_user_context": {
        "namespace": "nx-context",
        "function": "get_user_context",
        "description": "Get user context",
        "params": {},
    },
    "nx_learning_status": {
        "namespace": "nx-brain",
        "function": "learning_status",
        "description": "Get learning status",
        "params": {},
    },
    "nx_learning_route_task": {
        "namespace": "nx-brain",
        "function": "learning_route_task",
        "description": "Route task via learning",
        "params": {"task_description": "str"},
    },
    "nx_learning_record_outcome": {
        "namespace": "nx-brain",
        "function": "learning_record_outcome",
        "description": "Record learning outcome",
        "params": {"task": "str", "agent": "str", "success": "bool"},
    },
    "nx_learning_execute_hybrid": {
        "namespace": "nx-brain",
        "function": "learning_execute_hybrid",
        "description": "Execute hybrid",
        "params": {"task_description": "str"},
    },
    "nx_intelligence_route": {
        "namespace": "nx-brain",
        "function": "intelligence_route",
        "description": "Route via intelligence",
        "params": {"task_description": "str"},
    },
    "nx_intelligence_score_complexity": {
        "namespace": "nx-brain",
        "function": "intelligence_score_complexity",
        "description": "Score complexity",
        "params": {"task_description": "str"},
    },
    "nx_intelligence_available_agents": {
        "namespace": "nx-brain",
        "function": "intelligence_available_agents",
        "description": "List available agents",
        "params": {},
    },
    "nx_brain_trigger_register": {
        "namespace": "nx-brain",
        "function": "trigger_register",
        "description": "Register trigger",
        "params": {"phrase": "str", "description": "str"},
    },
    "nx_brain_catalyst_detect_state": {
        "namespace": "nx-brain",
        "function": "catalyst_detect_state",
        "description": "Detect catalyst state",
        "params": {"user_input": "str"},
    },
    "nx_brain_system_health_check": {
        "namespace": "nx-brain",
        "function": "system_health_check",
        "description": "System health check",
        "params": {},
    },
    "nx_brain_mind_get_mind_state": {
        "namespace": "nx-brain",
        "function": "mind_get_mind_state",
        "description": "Get mind state",
        "params": {},
    },
    "nx_brain_mind_update_mind_state": {
        "namespace": "nx-brain",
        "function": "mind_update_mind_state",
        "description": "Update mind state",
        "params": {"project": "str", "phase": "str"},
    },
    "nx_brain_fingerprint_get_user_preferences": {
        "namespace": "nx-brain",
        "function": "fingerprint_get_user_preferences",
        "description": "Get user preferences",
        "params": {},
    },
    "nx_pipeline_spawn": {
        "namespace": "nx-brain",
        "function": "pipeline_spawn",
        "description": "Spawn pipeline task",
        "params": {"agent": "str", "task": "str"},
    },
    "nx_delegate_nx_delegate": {
        "namespace": "nx-brain",
        "function": "delegate",
        "description": "Delegate task",
        "params": {"task_description": "str"},
    },
    "nx_brain_tunnel_chat": {
        "namespace": "nx-brain",
        "function": "tunnel_chat",
        "description": "Chat via tunnel",
        "params": {"messages": "list"},
    },
    
    # Quality gates
    "nx_quality_run_typecheck": {
        "namespace": "nx-quality",
        "function": "run_typecheck",
        "description": "Run type check",
        "params": {},
    },
    "nx_quality_run_lint": {
        "namespace": "nx-quality",
        "function": "run_lint",
        "description": "Run linting",
        "params": {},
    },
    "nx_quality_run_tests": {
        "namespace": "nx-quality",
        "function": "run_tests",
        "description": "Run tests",
        "params": {},
    },
    "nx_quality_run_secrets_scan": {
        "namespace": "nx-quality",
        "function": "run_secrets_scan",
        "description": "Scan for secrets",
        "params": {},
    },
    
    # Session tools
    "session_info": {
        "namespace": "session",
        "function": "session_info",
        "description": "Get session info",
        "params": {"session_id": "str"},
    },
    
    # AST tools
    "ast_grep_search": {
        "namespace": "ast-grep",
        "function": "search",
        "description": "AST grep search",
        "params": {"pattern": "str", "lang": "str"},
    },
    "ast_grep_replace": {
        "namespace": "ast-grep",
        "function": "replace",
        "description": "AST grep replace",
        "params": {"pattern": "str", "rewrite": "str", "lang": "str"},
    },
    
    # Code search
    "grep_app_searchGitHub": {
        "namespace": "grep-app",
        "function": "searchGitHub",
        "description": "Search GitHub code",
        "params": {"query": "str", "language": "list"},
    },
    "codesearch": {
        "namespace": "codesearch",
        "function": "search",
        "description": "Code search",
        "params": {"query": "str", "tokensNum": "int"},
    },
    
    # Web fetch
    "fetch_fetch_txt": {
        "namespace": "fetch",
        "function": "fetch_txt",
        "description": "Fetch as text",
        "params": {"url": "str"},
    },
    "fetch_fetch_json": {
        "namespace": "fetch",
        "function": "fetch_json",
        "description": "Fetch as JSON",
        "params": {"url": "str"},
    },
    "fetch_fetch_readable": {
        "namespace": "fetch",
        "function": "fetch_readable",
        "description": "Fetch readable content",
        "params": {"url": "str"},
    },
    "fetch_fetch_youtube_transcript": {
        "namespace": "fetch",
        "function": "fetch_youtube_transcript",
        "description": "Get YouTube transcript",
        "params": {"url": "str"},
    },
    "webfetch": {
        "namespace": "webfetch",
        "function": "fetch",
        "description": "Web fetch",
        "params": {"url": "str", "format": "str"},
    },
    "websearch_web_search_exa": {
        "namespace": "websearch",
        "function": "web_search_exa",
        "description": "Web search",
        "params": {"query": "str", "numResults": "int"},
    },
    
    # LSP tools
    "lsp_find_references": {
        "namespace": "lsp",
        "function": "find_references",
        "description": "Find references",
        "params": {"filePath": "str", "line": "int", "character": "int"},
    },
    "lsp_prepare_rename": {
        "namespace": "lsp",
        "function": "prepare_rename",
        "description": "Prepare rename",
        "params": {"filePath": "str", "line": "int", "character": "int"},
    },
    "lsp_rename": {
        "namespace": "lsp",
        "function": "rename",
        "description": "Rename symbol",
        "params": {"filePath": "str", "line": "int", "character": "int", "newName": "str"},
    },
    
    # GitHub extended
    "github_update_pull_request_branch": {
        "namespace": "github",
        "function": "update_pull_request_branch",
        "description": "Update PR branch",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_create_pull_request": {
        "namespace": "github",
        "function": "create_pull_request",
        "description": "Create PR",
        "params": {"owner": "str", "repo": "str", "title": "str", "head": "str", "base": "str"},
    },
    "github_get_pull_request": {
        "namespace": "github",
        "function": "get_pull_request",
        "description": "Get PR details",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_update_issue": {
        "namespace": "github",
        "function": "update_issue",
        "description": "Update issue",
        "params": {"owner": "str", "repo": "str", "issue_number": "int", "title": "str"},
    },
    "github_get_pull_request_status": {
        "namespace": "github",
        "function": "get_pull_request_status",
        "description": "Get PR status",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_get_pull_request_comments": {
        "namespace": "github",
        "function": "get_pull_request_comments",
        "description": "Get PR comments",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_get_pull_request_files": {
        "namespace": "github",
        "function": "get_pull_request_files",
        "description": "Get PR files",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_get_pull_request_reviews": {
        "namespace": "github",
        "function": "get_pull_request_reviews",
        "description": "Get PR reviews",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_create_pull_request_review": {
        "namespace": "github",
        "function": "create_pull_request_review",
        "description": "Create PR review",
        "params": {"owner": "str", "repo": "str", "pull_number": "int", "body": "str", "event": "str"},
    },
    "github_merge_pull_request": {
        "namespace": "github",
        "function": "merge_pull_request",
        "description": "Merge PR",
        "params": {"owner": "str", "repo": "str", "pull_number": "int"},
    },
    "github_create_or_update_file": {
        "namespace": "github",
        "function": "create_or_update_file",
        "description": "Create/update file",
        "params": {"owner": "str", "repo": "str", "path": "str", "content": "str", "message": "str"},
    },
    "github_push_files": {
        "namespace": "github",
        "function": "push_files",
        "description": "Push multiple files",
        "params": {"owner": "str", "repo": "str", "branch": "str", "files": "list", "message": "str"},
    },
    "github_create_branch": {
        "namespace": "github",
        "function": "create_branch",
        "description": "Create branch",
        "params": {"owner": "str", "repo": "str", "branch": "str"},
    },
    "github_fork_repository": {
        "namespace": "github",
        "function": "fork_repository",
        "description": "Fork repository",
        "params": {"owner": "str", "repo": "str"},
    },
    "github_get_file_contents": {
        "namespace": "github",
        "function": "get_file_contents",
        "description": "Get file contents",
        "params": {"owner": "str", "repo": "str", "path": "str"},
    },
    "github_search_issues": {
        "namespace": "github",
        "function": "search_issues",
        "description": "Search issues",
        "params": {"q": "str"},
    },
    "github_add_issue_comment": {
        "namespace": "github",
        "function": "add_issue_comment",
        "description": "Add issue comment",
        "params": {"owner": "str", "repo": "str", "issue_number": "int", "body": "str"},
    },
    "context7_resolve-library-id": {
        "namespace": "context7",
        "function": "resolve-library-id",
        "description": "Resolve library ID",
        "params": {"query": "str", "libraryName": "str"},
    },
    "sequential-thinking": {
        "namespace": "sequential-thinking",
        "function": "sequentialthinking",
        "description": "Chain of thought",
        "params": {"thought": "str", "nextThoughtNeeded": "bool", "thoughtNumber": "int", "totalThoughts": "int"},
    },
    "skill_mcp": {
        "namespace": "skill",
        "function": "mcp",
        "description": "Skill MCP call",
        "params": {"mcp_name": "str", "tool_name": "str", "arguments": "dict"},
    },
    "look_at": {
        "namespace": "look_at",
        "function": "analyze",
        "description": "Look at media",
        "params": {"file_path": "str", "goal": "str"},
    },
    "bash": {
        "namespace": "bash",
        "function": "run",
        "description": "Run bash command",
        "params": {"command": "str", "workdir": "str"},
    },
    "run_command": {
        "namespace": "bash",
        "function": "run",
        "description": "Run command",
        "params": {"command": "str", "description": "str"},
    },
    "task": {
        "namespace": "task",
        "function": "spawn",
        "description": "Spawn task",
        "params": {"subagent_type": "str", "prompt": "str", "description": "str"},
    },
    "grep": {
        "namespace": "grep",
        "function": "search",
        "description": "Grep search",
        "params": {"pattern": "str", "path": "str", "output_mode": "str"},
    },
    
    # Remaining missing
    "notion_API-update-a-data-source": {
        "namespace": "notion",
        "function": "update_a_data_source",
        "description": "Update Notion database",
        "params": {"data_source_id": "str", "title": "list"},
    },
    "notion_API-get-self": {
        "namespace": "notion",
        "function": "get_self",
        "description": "Get Notion bot user",
        "params": {},
    },
    "notion_API-get-users": {
        "namespace": "notion",
        "function": "get_users",
        "description": "List Notion users",
        "params": {},
    },
    "playwright_navigate": {
        "namespace": "playwright",
        "function": "navigate",
        "description": "Navigate browser",
        "params": {"url": "str"},
    },
    "playwright_fill": {
        "namespace": "playwright",
        "function": "fill",
        "description": "Fill form",
        "params": {"selector": "str", "value": "str"},
    },
    "playwright_click": {
        "namespace": "playwright",
        "function": "click",
        "description": "Click element",
        "params": {"selector": "str"},
    },
    "notion_API-retrieve-a-database": {
        "namespace": "notion",
        "function": "retrieve_a_database",
        "description": "Retrieve Notion database",
        "params": {"database_id": "str"},
    },
    "notion_API-move-page": {
        "namespace": "notion",
        "function": "move_page",
        "description": "Move Notion page",
        "params": {"page_id": "str", "parent": "dict"},
    },
    "notion_API-list-data-source-templates": {
        "namespace": "notion",
        "function": "list_data_source_templates",
        "description": "List database templates",
        "params": {"data_source_id": "str"},
    },
    "notion_API-update-a-block": {
        "namespace": "notion",
        "function": "update_a_block",
        "description": "Update Notion block",
        "params": {"block_id": "str", "type": "dict"},
    },
    "notion_API-get-user": {
        "namespace": "notion",
        "function": "get_user",
        "description": "Get Notion user",
        "params": {"user_id": "str"},
    },
    "nx_brain_learning_route_task": {
        "namespace": "nx-brain",
        "function": "learning_route_task",
        "description": "Learning route task",
        "params": {"task_description": "str"},
    },
    "nx_brain_context_get_active_context": {
        "namespace": "nx-brain",
        "function": "context_get_active_context",
        "description": "Get active context",
        "params": {},
    },
    "websearch": {
        "namespace": "websearch",
        "function": "search",
        "description": "Web search",
        "params": {"query": "str"},
    },
    "skill": {
        "namespace": "skill",
        "function": "load",
        "description": "Load skill",
        "params": {"name": "str", "user_message": "str"},
    },
}


# =============================================================================
# Aliases - Common variations of tool names
# =============================================================================

TOOL_ALIASES: Dict[str, str] = {
    # Memory
    "search": "memory_search",
    "write": "memory_write",
    "save": "memory_write",
    "recall": "memory_recall",
    "mem_search": "memory_search",
    "mem_write": "memory_write",
    
    # Filesystem  
    "read": "read_file",
    "write": "write_file",
    "edit": "edit_file",
    "list": "list_directory",
    "ls": "list_directory",
    "cat": "read_file",
    
    # Git
    "git": "git_status",
    "status": "git_status",
    "log": "git_log",
    "diff": "git_diff",
    
    # GitHub
    "gh_search": "github_search_repos",
    "gh_issues": "github_list_issues",
    "gh_code": "github_search_code",
    "issue": "github_create_issue",
    
    # Web
    "fetch": "fetch_url",
    "fetch_readable": "fetch_url",
    "search_web": "web_search",
    "docs": "context7_query_docs",
    
    # Database
    "query": "sqlite_query",
    "tables": "sqlite_list_tables",
    
    # System
    "context": "get_active_context",
    "product": "get_product_context",
    "user": "get_user_context",
    "constraints": "get_constraints",
    
    # Learning
    "route": "route_task",
    "record": "record_outcome",
    
    # Thinking
    "think": "sequential_thinking",
    "cot": "sequential_thinking",
    
    # Browser
    "navigate": "browser_navigate",
    "click": "browser_click",
    "fill": "browser_fill",
    "screenshot": "browser_screenshot",
    
    # Code
    "diagnostics": "lsp_diagnostics",
    "symbols": "lsp_symbols",
    "goto": "lsp_goto_definition",
    "goto_def": "lsp_goto_definition",
    
    # Brain
    "brain": "brain_search",
    
    # Session
    "sessions": "session_list",
    "read_session": "session_read",
    "search_session": "session_search",
    
    # Todo
    "todo": "todowrite",
    "todos": "todowrite",
    
    # Question
    "ask": "question_ask",
    
    # Task
    "spawn": "task_spawn",
    "delegate": "task_spawn",
}


# =============================================================================
# Functions
# =============================================================================

def get_tool_info(tool_name: str) -> Optional[Dict[str, str]]:
    """Get tool info by name or alias"""
    # Direct lookup
    if tool_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[tool_name]
    
    # Alias lookup
    if tool_name in TOOL_ALIASES:
        canonical = TOOL_ALIASES[tool_name]
        return TOOL_REGISTRY.get(canonical)
    
    return None


def is_supported(tool_name: str) -> bool:
    """Check if tool is supported"""
    return get_tool_info(tool_name) is not None


def list_tools() -> List[Dict[str, Any]]:
    """List all registered tools"""
    tools = []
    for name, info in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "namespace": info["namespace"],
            "function": info["function"],
            "description": info["description"],
            "parameters": info["params"],
        })
    return tools


def list_namespaces() -> List[str]:
    """List all namespaces"""
    namespaces = set()
    for info in TOOL_REGISTRY.values():
        namespaces.add(info["namespace"])
    return sorted(namespaces)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"Registered {len(TOOL_REGISTRY)} tools across {len(list_namespaces())} namespaces")
    print("\nTools:")
    for tool in sorted(TOOL_REGISTRY.keys()):
        info = TOOL_REGISTRY[tool]
        print(f"  {tool}: {info['namespace']}.{info['function']}")