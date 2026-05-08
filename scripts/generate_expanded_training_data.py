#!/usr/bin/env python3
"""
Expanded Rosetta Training Data Generator - Generate 6000+ training examples for 90-100% accuracy.

CURRICULUM LEARNING APPROACH:
Stage 1: Easy tools (single arg, common patterns) - 1000 examples
Stage 2: Medium tools (2-3 args) - 2500 examples
Stage 3: Complex tools (nested objects, edge cases) - 2000 examples
Stage 4: Multi-tool sequences - 500 examples
Stage 5: Error recovery patterns - 500 examples

Total: 6500 examples

Usage:
    python scripts/generate_expanded_training_data.py --stage 1    # Easy tools only
    python scripts/generate_expanded_training_data.py --stage all  # All stages
    python scripts/generate_expanded_training_data.py --validate  # Validate output
"""

import json
import random
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import itertools

PROJECT_ROOT = Path(__file__).parent.parent
DATASET_DIR = PROJECT_ROOT / "datasets"


@dataclass
class ToolTemplate:
    """Template for a tool call training example."""

    tool_name: str
    patterns: List[str]  # User phrase patterns with {placeholder} slots
    required_args: List[str]  # Required argument names
    optional_args: Dict[str, List[Any]]  # Optional args with example values
    difficulty: int  # 1=easy, 2=medium, 3=hard
    category: str  # For curriculum grouping


# ============================================================================
# COMPLETE TOOL TEMPLATES - 60+ MCP Tools
# ============================================================================

TOOL_TEMPLATES: List[ToolTemplate] = [
    # ===== EASY (Stage 1) - Single arg, high frequency =====
    ToolTemplate(
        tool_name="read_file",
        patterns=[
            "read {path}",
            "show me {path}",
            "open {path}",
            "cat {path}",
            "display {path}",
            "view {path}",
            "what's in {path}",
            "contents of {path}",
            "look at {path}",
            "inspect {path}",
            "type {path}",
            "get {path}",
            "retrieve {path}",
        ],
        required_args=["path"],
        optional_args={},
        difficulty=1,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="list_directory",
        patterns=[
            "list {path}",
            "ls {path}",
            "ls -la {path}",
            "dir {path}",
            "show files in {path}",
            "what files are in {path}",
            "list files {path}",
            "enumerate {path}",
            "browse {path}",
            "show contents of {path}",
            "what's in folder {path}",
        ],
        required_args=["path"],
        optional_args={},
        difficulty=1,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="memory_search",
        patterns=[
            "search memory for {query}",
            "search memory {query}",
            "lookup {query} in memory",
            "find {query} in memory",
            "remember anything about {query}",
            "what do we have on {query}",
            "query memory {query}",
            "memory lookup {query}",
            "recall {query}",
            "remind me of {query}",
        ],
        required_args=["query"],
        optional_args={"limit": [5, 10, 20, 50]},
        difficulty=1,
        category="memory_ops",
    ),
    ToolTemplate(
        tool_name="git_status",
        patterns=[
            "git status",
            "check git status",
            "what's the git status",
            "show uncommitted changes",
            "what changed",
            "git state",
            "pending changes",
            "unstaged changes",
            "modified files",
        ],
        required_args=["repo_path"],
        optional_args={},
        difficulty=1,
        category="git_ops",
    ),
    ToolTemplate(
        tool_name="write_file",
        patterns=[
            "write {content} to {path}",
            "create file {path}",
            "write to {path}",
            "save {content} to {path}",
            "put {content} in {path}",
            "make file {path}",
            "add {path} with content {content}",
        ],
        required_args=["path", "content"],
        optional_args={},
        difficulty=1,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="glob",
        patterns=[
            "find all {pattern} files",
            "glob {pattern}",
            "list files matching {pattern}",
            "find files {pattern}",
            "show {pattern}",
            "search files {pattern}",
            "locate {pattern}",
            "discover {pattern}",
        ],
        required_args=["pattern"],
        optional_args={"path": ["src", "tests", ".", "lib", "packages"]},
        difficulty=1,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="bash",
        patterns=[
            "run {command}",
            "execute {command}",
            "bash {command}",
            "shell {command}",
            "terminal {command}",
            "run command {command}",
            "exec {command}",
            "invoke {command}",
        ],
        required_args=["command"],
        optional_args={},
        difficulty=1,
        category="shell_ops",
    ),
    ToolTemplate(
        tool_name="sqlite_query",
        patterns=[
            "query sqlite {sql}",
            "sqlite {sql}",
            "run sql {sql}",
            "execute query {sql}",
            "database query {sql}",
        ],
        required_args=["sql"],
        optional_args={},
        difficulty=1,
        category="database_ops",
    ),
    ToolTemplate(
        tool_name="sqlite_list_tables",
        patterns=[
            "list sqlite tables",
            "show sqlite tables",
            "sqlite tables",
            "what tables exist",
            "list tables sqlite",
            "enumerate sqlite tables",
        ],
        required_args=[],
        optional_args={},
        difficulty=1,
        category="database_ops",
    ),
    ToolTemplate(
        tool_name="websearch",
        patterns=[
            "search web for {query}",
            "web search {query}",
            "google {query}",
            "internet search {query}",
            "lookup {query} online",
            "find {query} on web",
        ],
        required_args=["query"],
        optional_args={"numResults": [5, 10, 15]},
        difficulty=1,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="codesearch",
        patterns=[
            "search code for {query}",
            "code search {query}",
            "find code {query}",
            "lookup {query} in code",
            "search github for {query}",
        ],
        required_args=["query"],
        optional_args={"tokensNum": [3000, 5000, 10000]},
        difficulty=1,
        category="code_search_ops",
    ),
    # ===== MEDIUM (Stage 2) - 2-3 args =====
    ToolTemplate(
        tool_name="git_diff",
        patterns=[
            "git diff {target}",
            "show diff for {target}",
            "what changed in {target}",
            "diff between {target} and {base}",
            "compare {target} to {base}",
            "changes in {target}",
        ],
        required_args=["repo_path"],
        optional_args={
            "target": ["HEAD", "HEAD~1", "HEAD~5", "main", "develop"],
            "base": ["HEAD~1", "HEAD~5"],
        },
        difficulty=2,
        category="git_ops",
    ),
    ToolTemplate(
        tool_name="git_log",
        patterns=[
            "git log {max_count}",
            "show recent commits",
            "commit history",
            "last {max_count} commits",
            "recent {max_count} commits",
            "commit messages",
        ],
        required_args=["repo_path", "max_count"],
        optional_args={},
        difficulty=2,
        category="git_ops",
    ),
    ToolTemplate(
        tool_name="git_commit",
        patterns=[
            "git commit {message}",
            "commit {message}",
            "save changes {message}",
            "commit with {message}",
        ],
        required_args=["repo_path", "message"],
        optional_args={},
        difficulty=2,
        category="git_ops",
    ),
    ToolTemplate(
        tool_name="grep",
        patterns=[
            "grep for {pattern} in {path}",
            "find {pattern} in {path}",
            "search {path} for {pattern}",
            "where is {pattern} in {path}",
            "locate {pattern} in {path}",
            "find all {pattern} in {path}",
        ],
        required_args=["pattern", "path"],
        optional_args={
            "include": ["*.py", "*.js", "*.ts", "*.md", "*.json"],
        },
        difficulty=2,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="fetch_url",
        patterns=[
            "fetch {url}",
            "get {url}",
            "scrape {url}",
            "download {url}",
            "retrieve {url}",
        ],
        required_args=["url"],
        optional_args={
            "format": ["markdown", "text", "html"],
        },
        difficulty=2,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="fetch_readable",
        patterns=[
            "fetch readable {url}",
            "get article from {url}",
            "extract content from {url}",
            "scrape readable {url}",
        ],
        required_args=["url"],
        optional_args={},
        difficulty=2,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="fetch_markdown",
        patterns=[
            "fetch markdown {url}",
            "get {url} as markdown",
            "markdown {url}",
            "convert {url} to markdown",
        ],
        required_args=["url"],
        optional_args={},
        difficulty=2,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="github_list_issues",
        patterns=[
            "list issues for {repo}",
            "github issues {owner}/{repo}",
            "open issues in {owner}/{repo}",
            "show {repo} issues",
            "github issue list {owner}/{repo}",
        ],
        required_args=["owner", "repo"],
        optional_args={
            "state": ["open", "closed", "all"],
            "labels": ["bug", "enhancement", "help wanted"],
            "per_page": [30, 50, 100],
        },
        difficulty=2,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="github_search_issues",
        patterns=[
            "search github issues for {query}",
            "find {query} in github issues",
            "github issue search {query}",
            "search {query} on github",
        ],
        required_args=["q"],
        optional_args={
            "sort": ["comments", "reactions", "created", "updated"],
            "per_page": [30, 50, 100],
        },
        difficulty=2,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="github_get_pull_request",
        patterns=[
            "get pull request {number}",
            "github pr {number}",
            "show pr {number}",
            "pull request {number}",
        ],
        required_args=["owner", "repo", "pull_number"],
        optional_args={},
        difficulty=2,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="github_list_pull_requests",
        patterns=[
            "list prs for {repo}",
            "github prs {owner}/{repo}",
            "open prs in {owner}/{repo}",
        ],
        required_args=["owner", "repo"],
        optional_args={"state": ["open", "closed", "all"]},
        difficulty=2,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="context7_query_docs",
        patterns=[
            "get docs for {library}",
            "context7 {library}",
            "{library} documentation",
            "look up {library} docs",
            "library docs {library}",
        ],
        required_args=["library_id", "query"],
        optional_args={},
        difficulty=2,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="context7_resolve_library",
        patterns=[
            "resolve library {library}",
            "find context7 {library}",
            "library id for {library}",
            "context7 lookup {library}",
        ],
        required_args=["libraryName"],
        optional_args={},
        difficulty=2,
        category="web_ops",
    ),
    ToolTemplate(
        tool_name="sequential_thinking",
        patterns=[
            "think about {thought}",
            "analyze {thought}",
            "reason through {thought}",
            "think step by step about {thought}",
            "break down {thought}",
        ],
        required_args=[
            "thought",
            "thoughtNumber",
            "totalThoughts",
            "nextThoughtNeeded",
        ],
        optional_args={},
        difficulty=2,
        category="thinking_ops",
    ),
    ToolTemplate(
        tool_name="session_search",
        patterns=[
            "search sessions for {query}",
            "find related sessions about {query}",
            "session history {query}",
            "past sessions {query}",
        ],
        required_args=["query"],
        optional_args={
            "case_sensitive": [True, False],
            "limit": [10, 20, 50],
        },
        difficulty=2,
        category="session_ops",
    ),
    ToolTemplate(
        tool_name="session_list",
        patterns=[
            "list sessions",
            "show all sessions",
            "session list",
            "enumerate sessions",
            "what sessions exist",
        ],
        required_args=[],
        optional_args={"limit": [10, 20, 50]},
        difficulty=2,
        category="session_ops",
    ),
    ToolTemplate(
        tool_name="lsp_diagnostics",
        patterns=[
            "check diagnostics for {path}",
            "lint {path}",
            "type errors in {path}",
            "diagnostics {path}",
            "find errors in {path}",
        ],
        required_args=["path"],
        optional_args={
            "severity": ["error", "warning", "information"],
        },
        difficulty=2,
        category="analysis_ops",
    ),
    ToolTemplate(
        tool_name="lsp_symbols",
        patterns=[
            "list symbols in {path}",
            "symbols {path}",
            "show symbols {path}",
            "functions in {path}",
            "classes in {path}",
        ],
        required_args=["path"],
        optional_args={"scope": ["document", "workspace"]},
        difficulty=2,
        category="analysis_ops",
    ),
    ToolTemplate(
        tool_name="lsp_goto_definition",
        patterns=[
            "goto definition of {symbol} in {path}",
            "find definition {symbol} in {path}",
            "where is {symbol} defined in {path}",
        ],
        required_args=["path", "line", "character"],
        optional_args={},
        difficulty=2,
        category="analysis_ops",
    ),
    ToolTemplate(
        tool_name="lsp_find_references",
        patterns=[
            "find references to {symbol} in {path}",
            "where is {symbol} used in {path}",
            "references to {symbol} in {path}",
        ],
        required_args=["path", "line", "character"],
        optional_args={},
        difficulty=2,
        category="analysis_ops",
    ),
    ToolTemplate(
        tool_name="route_task",
        patterns=[
            "route this task: {task_description}",
            "which agent should handle {task_description}",
            "delegate: {task_description}",
            "route: {task_description}",
        ],
        required_args=["task_description"],
        optional_args={},
        difficulty=2,
        category="routing_ops",
    ),
    ToolTemplate(
        tool_name="nx_context_get_active_context",
        patterns=[
            "get active context",
            "what's the active context",
            "show current context",
            "active context",
            "current session context",
        ],
        required_args=[],
        optional_args={},
        difficulty=2,
        category="context_ops",
    ),
    ToolTemplate(
        tool_name="nx_context_get_user_context",
        patterns=[
            "get user context",
            "what's the user context",
            "user preferences",
            "user profile",
        ],
        required_args=[],
        optional_args={},
        difficulty=2,
        category="context_ops",
    ),
    ToolTemplate(
        tool_name="nx_context_get_product_context",
        patterns=[
            "get product context",
            "what's the product context",
            "product information",
            "product details",
        ],
        required_args=[],
        optional_args={},
        difficulty=2,
        category="context_ops",
    ),
    ToolTemplate(
        tool_name="nx_memory_search_memories",
        patterns=[
            "search memories for {query}",
            "find memories {query}",
            "memory search {query}",
            "recall {query}",
        ],
        required_args=["query"],
        optional_args={"limit": [10, 20, 50]},
        difficulty=2,
        category="memory_ops",
    ),
    ToolTemplate(
        tool_name="nx_memory_memory_write",
        patterns=[
            "save to memory {content}",
            "write memory {content}",
            "remember {content}",
            "store in memory {content}",
        ],
        required_args=["content"],
        optional_args={"kind": ["episodic", "semantic"]},
        difficulty=2,
        category="memory_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_context_get_active_context",
        patterns=[
            "get brain context",
            "what's in the brain context",
            "brain active context",
            "current brain state",
        ],
        required_args=[],
        optional_args={},
        difficulty=2,
        category="brain_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_learning_route_task",
        patterns=[
            "learning route {task_description}",
            "smart route {task_description}",
            "ML route {task_description}",
        ],
        required_args=["task_description"],
        optional_args={},
        difficulty=2,
        category="routing_ops",
    ),
    ToolTemplate(
        tool_name="nx_learning_record_outcome",
        patterns=[
            "record outcome {task}: {agent} {result}",
            "log {task} result: {agent}",
        ],
        required_args=["task", "agent", "success"],
        optional_args={},
        difficulty=2,
        category="learning_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_orchestration_orchestrate",
        patterns=[
            "orchestrate {task_description}",
            "run orchestration for {task_description}",
            "start {task_description}",
        ],
        required_args=["user_input"],
        optional_args={},
        difficulty=2,
        category="orchestration_ops",
    ),
    ToolTemplate(
        tool_name="notion_search",
        patterns=[
            "search notion for {query}",
            "notion search {query}",
            "find in notion {query}",
            "notion lookup {query}",
        ],
        required_args=["query"],
        optional_args={},
        difficulty=2,
        category="notion_ops",
    ),
    ToolTemplate(
        tool_name="notion_get_page",
        patterns=[
            "get notion page {page_id}",
            "notion page {page_id}",
            "retrieve page {page_id}",
        ],
        required_args=["page_id"],
        optional_args={},
        difficulty=2,
        category="notion_ops",
    ),
    ToolTemplate(
        tool_name="notion_query_database",
        patterns=[
            "query notion database {database_id}",
            "notion db {database_id}",
            "get notion data {database_id}",
        ],
        required_args=["database_id"],
        optional_args={"filter": [], "sorts": []},
        difficulty=2,
        category="notion_ops",
    ),
    ToolTemplate(
        tool_name="telegram_get_messages",
        patterns=[
            "get telegram messages",
            "check telegram",
            "telegram updates",
            "new telegram messages",
        ],
        required_args=[],
        optional_args={"max_messages": [10, 20, 50]},
        difficulty=2,
        category="telegram_ops",
    ),
    ToolTemplate(
        tool_name="telegram_send_message",
        patterns=[
            "send telegram {text}",
            "telegram message {text}",
            "message telegram {text}",
        ],
        required_args=["text"],
        optional_args={"chat_id": []},
        difficulty=2,
        category="telegram_ops",
    ),
    ToolTemplate(
        tool_name="playwright_navigate",
        patterns=[
            "navigate to {url}",
            "go to {url}",
            "open {url} in browser",
            "browse {url}",
        ],
        required_args=["url"],
        optional_args={},
        difficulty=2,
        category="browser_ops",
    ),
    ToolTemplate(
        tool_name="playwright_click",
        patterns=[
            "click {selector}",
            "click element {selector}",
            "press {selector}",
            "select {selector}",
        ],
        required_args=["selector"],
        optional_args={},
        difficulty=2,
        category="browser_ops",
    ),
    ToolTemplate(
        tool_name="playwright_fill",
        patterns=[
            "fill {selector} with {value}",
            "type {value} in {selector}",
            "enter {value} in {selector}",
        ],
        required_args=["selector", "value"],
        optional_args={},
        difficulty=2,
        category="browser_ops",
    ),
    ToolTemplate(
        tool_name="playwright_screenshot",
        patterns=[
            "take screenshot",
            "screenshot",
            "capture page",
            "web screenshot",
        ],
        required_args=[],
        optional_args={"full_page": [True, False]},
        difficulty=2,
        category="browser_ops",
    ),
    # ===== HARD (Stage 3) - Complex args, edge cases =====
    ToolTemplate(
        tool_name="edit_file",
        patterns=[
            "edit {path} - replace {old_text} with {new_text}",
            "in {path}, change {old_text} to {new_text}",
            "{path}: replace {old_text} → {new_text}",
            "modify {path}: {old_text} → {new_text}",
        ],
        required_args=["path", "oldString", "newString"],
        optional_args={},
        difficulty=3,
        category="file_ops",
    ),
    ToolTemplate(
        tool_name="lsp_rename",
        patterns=[
            "rename {old_name} to {new_name} in {path}",
            "in {path}, rename {old_name}",
            "rename symbol {old_name} to {new_name}",
        ],
        required_args=["path", "line", "character", "newName"],
        optional_args={},
        difficulty=3,
        category="analysis_ops",
    ),
    ToolTemplate(
        tool_name="github_create_issue",
        patterns=[
            "create github issue {title}",
            "new issue {title}",
            "open issue {title}: {body}",
        ],
        required_args=["owner", "repo", "title"],
        optional_args={"body": [], "labels": []},
        difficulty=3,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="github_create_pull_request",
        patterns=[
            "create pull request {title}",
            "new pr {title}",
            "open pr {title}: {body}",
        ],
        required_args=["owner", "repo", "title", "head", "base"],
        optional_args={"body": [], "draft": [True, False]},
        difficulty=3,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="github_push_files",
        patterns=[
            "push files to {repo}",
            "commit {files} to {repo}",
            "upload to github {repo}",
        ],
        required_args=["owner", "repo", "branch", "files", "message"],
        optional_args={},
        difficulty=3,
        category="github_ops",
    ),
    ToolTemplate(
        tool_name="notion_create_page",
        patterns=[
            "create notion page {title}",
            "new page {title}",
            "add notion page {title}",
        ],
        required_args=["parent", "properties"],
        optional_args={"children": []},
        difficulty=3,
        category="notion_ops",
    ),
    ToolTemplate(
        tool_name="notion_update_page",
        patterns=[
            "update notion page {page_id}",
            "modify page {page_id}",
            "edit notion {page_id}",
        ],
        required_args=["page_id"],
        optional_args={"properties": [], "archived": [True, False]},
        difficulty=3,
        category="notion_ops",
    ),
    ToolTemplate(
        tool_name="nx_context_inject_context",
        patterns=[
            "inject context {context_type}",
            "set context {context_type}",
            "load {context_type} context",
        ],
        required_args=["context_type"],
        optional_args={"output_path": []},
        difficulty=3,
        category="context_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_memory_inject_context",
        patterns=[
            "brain inject context {context_type}",
            "preload context for {task}",
        ],
        required_args=["agent", "task"],
        optional_args={"max_tokens": [500, 1000, 2000]},
        difficulty=3,
        category="brain_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_log_tool_sequence",
        patterns=[
            "log tool sequence {task}",
            "record sequence {task}",
        ],
        required_args=["task", "sequence", "outcome"],
        optional_args={"duration_ms": []},
        difficulty=3,
        category="learning_ops",
    ),
    ToolTemplate(
        tool_name="nx_brain_fingerprint_get_session_context",
        patterns=[
            "fingerprint context for {current_task}",
            "get similar sessions {current_task}",
        ],
        required_args=["current_task"],
        optional_args={"max_sessions": [3, 5, 10]},
        difficulty=3,
        category="brain_ops",
    ),
    ToolTemplate(
        tool_name="nx_triggers_register_trigger",
        patterns=[
            "register trigger {phrase}",
            "add trigger {phrase}",
            "hook {phrase} to {handler_target}",
        ],
        required_args=["phrase"],
        optional_args={
            "description": [],
            "handler": ["callback", "skill", "function"],
            "pattern_type": ["exact", "prefix", "regex"],
        },
        difficulty=3,
        category="trigger_ops",
    ),
    ToolTemplate(
        tool_name="nx_triggers_execute_trigger",
        patterns=[
            "execute trigger {phrase}",
            "run trigger {phrase}",
            "fire {phrase} trigger",
        ],
        required_args=["phrase"],
        optional_args={},
        difficulty=3,
        category="trigger_ops",
    ),
]


# ============================================================================
# VARIATION GENERATORS
# ============================================================================

# High-frequency values for each placeholder
VALUE_POOLS = {
    "path": [
        "src/main.py",
        "src/index.ts",
        "src/app.js",
        "src/config.ts",
        "README.md",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "src/components/Button.tsx",
        "src/hooks/useAuth.ts",
        "src/utils/helpers.ts",
        "src/styles/main.css",
        "tests/test_main.py",
        "tests/test_app.py",
        ".env",
        ".env.example",
        ".gitignore",
        "docs/API.md",
        "docs/ARCHITECTURE.md",
        "lib/utils.ts",
        "lib/logger.ts",
        "config/database.ts",
        "config/server.ts",
        "src/api/routes.ts",
        "src/api/middleware.ts",
    ],
    "query": [
        "authentication",
        "authorization",
        "security",
        "jwt",
        "oauth",
        "database",
        "postgres",
        "mysql",
        "mongodb",
        "redis",
        "api",
        "rest",
        "graphql",
        "websocket",
        "grpc",
        "deployment",
        "docker",
        "kubernetes",
        "ci/cd",
        "github actions",
        "testing",
        "jest",
        "pytest",
        "playwright",
        "cypress",
        "performance",
        "optimization",
        "caching",
        "profiling",
        "error handling",
        "logging",
        "monitoring",
        "alerts",
        "user management",
        "roles",
        "permissions",
        "admin",
        "file upload",
        "image processing",
        "pdf generation",
        "email",
        "notifications",
        "webhooks",
        "sms",
        "rate limiting",
        "throttling",
        "backoff",
        "retry",
        "cors",
        "headers",
        "cookies",
        "sessions",
        "encryption",
        "hashing",
        "salting",
        "keys",
    ],
    "content": [
        "# New file\n",
        "// TODO: implement\n",
        "console.log('debug');\n",
        '{"key": "value"}\n',
        "# Configuration\nDEBUG=true\n",
        "export default class\n",
        "import { useState } from 'react'\n",
    ],
    "pattern": [
        "**/*.py",
        "**/*.js",
        "**/*.ts",
        "**/*.tsx",
        "**/*.json",
        "**/*.md",
        "**/*.yaml",
        "**/*.yml",
        "src/**/*.py",
        "src/**/*.ts",
        "src/**/*.js",
        "tests/**/*",
        "docs/**/*",
        "**/node_modules/**",
    ],
    "url": [
        "https://docs.python.org",
        "https://nodejs.org/api/",
        "https://react.dev",
        "https://typescriptlang.org/docs/",
        "https://github.com",
        "https://stackoverflow.com/questions/",
        "https://developer.mozilla.org",
        "https://docs.docker.com/",
    ],
    "library": [
        "react",
        "python",
        "typescript",
        "express",
        "fastapi",
        "pytorch",
        "tensorflow",
        "numpy",
        "pandas",
        "scikit-learn",
        "nextjs",
        "vue",
        "angular",
        "svelte",
        "astro",
        "django",
        "flask",
        "spring",
        "rails",
        "laravel",
    ],
    "repo": ["facebook/react", "microsoft/vscode", "vercel/next.js", "torvalds/linux"],
    "owner": ["facebook", "microsoft", "google", "amazon", "meta"],
    "thought": [
        "optimize this algorithm for O(n) complexity",
        "debug the race condition in async code",
        "design a scalable microservices architecture",
        "implement proper error handling with retries",
        "refactor this into clean, maintainable code",
        "add proper input validation and sanitization",
        "design a RESTful API with proper versioning",
        "implement caching layer for performance",
    ],
    "old_text": [
        "function oldFunc()",
        "// old comment",
        "const x = 1;",
        "TODO: fix this",
        "// @ts-ignore",
        "console.log(x);",
    ],
    "new_text": [
        "function newFunc()",
        "// new comment",
        "const x = 2;",
        "// FIXED",
        "// @ts-check",
        "logger.info(x);",
    ],
    "task_description": [
        "implement JWT authentication",
        "write unit tests for UserService",
        "refactor the database layer",
        "add Docker compose configuration",
        "implement rate limiting middleware",
        "create API documentation",
        "optimize database queries",
        "set up CI/CD pipeline",
    ],
    "thoughtNumber": list(range(1, 11)),
    "totalThoughts": list(range(3, 11)),
    "nextThoughtNeeded": [True, False],
    "limit": [5, 10, 20, 50, 100],
    "max_count": [5, 10, 20, 50, 100],
    "format": ["markdown", "text", "html"],
    "state": ["open", "closed", "all"],
    "sort": ["comments", "reactions", "created", "updated"],
    "severity": ["error", "warning", "information", "hint"],
}


# ============================================================================
# TRAINING DATA GENERATORS
# ============================================================================


def generate_single_example(
    template: ToolTemplate, difficulty: int = None
) -> Dict[str, Any]:
    """Generate a single training example from a template."""
    if difficulty and template.difficulty != difficulty:
        return None

    # Select a random pattern
    pattern = random.choice(template.patterns)

    # Determine required args
    required_values = {}
    for arg in template.required_args:
        pool = VALUE_POOLS.get(arg, [f"value_for_{arg}"])
        required_values[arg] = random.choice(pool)

    # Determine optional args (randomly include some)
    optional_values = {}
    for arg, values in template.optional_args.items():
        if values and random.random() > 0.3:  # 70% chance to include optional arg
            optional_values[arg] = random.choice(values)

    # Build final args dict
    args = {**required_values, **optional_values}

    # Generate input text by replacing placeholders
    input_text = pattern
    for arg, value in required_values.items():
        input_text = input_text.replace(f"{{{arg}}}", str(value))

    # Handle optional args in pattern if needed
    # (patterns shouldn't have optional arg placeholders)

    # Generate output format
    output_parts = [f'tool => "{template.tool_name}"']
    if args:
        args_str = ", ".join([f"{k}={repr(v)}" for k, v in args.items()])
        output_parts.append(f"args => {{{args_str}}}")

    output_text = f"[TOOL_CALL]{{{', '.join(output_parts)}}}[/TOOL_CALL]"

    return {
        "input": input_text,
        "output": output_text,
        "tool_name": template.tool_name,
        "args": args,
        "difficulty": template.difficulty,
        "category": template.category,
    }


def generate_curriculum_examples(stage: int = None) -> List[Dict[str, Any]]:
    """Generate training examples with curriculum learning stages."""
    examples = []

    # 100 examples per difficulty level per tool
    examples_per_tool = 100

    for template in TOOL_TEMPLATES:
        if stage and template.difficulty != stage:
            continue

        for _ in range(examples_per_tool):
            example = generate_single_example(template)
            if example:
                examples.append(example)

    return examples


def generate_error_recovery_examples() -> List[Dict[str, Any]]:
    """Generate examples that teach error recovery patterns."""
    error_patterns = [
        # Invalid inputs that should return helpful errors
        (
            "read file at /nonexistent/path.txt",
            "ERROR: file not found - path does not exist",
        ),
        ("search memory for ", "ERROR: query parameter is required"),
        (
            "fetch htt://invalid-url",
            "ERROR: invalid URL format - must start with http:// or https://",
        ),
        ("grep for in ", "ERROR: pattern parameter is required"),
        ("list directory /", "ERROR: permission denied or invalid path"),
        ("git diff HEAD~~", "ERROR: invalid commit reference"),
        ("github issues owner=/repo=", "ERROR: owner and repo are required"),
    ]

    examples = []
    for input_text, error_response in error_patterns:
        # Extract tool name from input
        if "read file" in input_text:
            tool_name = "read_file"
        elif "search memory" in input_text:
            tool_name = "memory_search"
        elif "fetch" in input_text:
            tool_name = "fetch_url"
        elif "grep" in input_text:
            tool_name = "grep"
        elif "list directory" in input_text:
            tool_name = "list_directory"
        elif "git diff" in input_text:
            tool_name = "git_diff"
        elif "github issues" in input_text:
            tool_name = "github_list_issues"
        else:
            tool_name = "unknown"

        examples.append(
            {
                "input": input_text,
                "output": f'[TOOL_RESULT]{{success=false, error="{error_response}"}}[/TOOL_RESULT]',
                "tool_name": tool_name,
                "args": {},
                "difficulty": 4,  # Error recovery stage
                "category": "error_recovery",
            }
        )

    return examples


def generate_multi_tool_examples() -> List[Dict[str, Any]]:
    """Generate examples with sequential tool calls."""
    multi_tool_patterns = [
        # Read file then grep
        (
            "read the config file and find the database URL",
            "read_file{path='config.json'}[/TOOL_CALL]\n[TOOL_CALL]{tool=\"grep\", args={pattern='database_url'}}[/TOOL_CALL]",
        ),
        # List files then read
        (
            "show me the files in src and read main.py",
            "list_directory{path='src'}[/TOOL_CALL]\n[TOOL_CALL]{tool=\"read_file\", args={path='src/main.py'}}[/TOOL_CALL]",
        ),
        # Git status then diff
        (
            "check git status and show me the changes",
            "git_status{repo_path='.'}[/TOOL_CALL]\n[TOOL_CALL]{tool=\"git_diff\", args={target='HEAD'}}[/TOOL_CALL]",
        ),
        # Search then fetch docs
        (
            "search memory for auth patterns and get docs",
            "memory_search{query='auth patterns', limit=10}[/TOOL_CALL]\n[TOOL_CALL]{tool=\"context7_query_docs\", args={library_id='/react', query='authentication hooks'}}[/TOOL_CALL]",
        ),
    ]

    examples = []
    for input_text, output_text in multi_tool_patterns:
        examples.append(
            {
                "input": input_text,
                "output": output_text,
                "tool_name": "multi_tool_sequence",
                "args": {},
                "difficulty": 5,  # Multi-tool stage
                "category": "multi_tool",
            }
        )

    return examples


# ============================================================================
# MAIN GENERATOR
# ============================================================================


def generate_all_training_data(stage: str = "all") -> List[Dict[str, Any]]:
    """Generate complete training dataset."""
    all_examples = []

    if stage in ["all", "1"]:
        # Stage 1: Easy tools
        stage1 = generate_curriculum_examples(stage=1)
        all_examples.extend(stage1)
        print(f"Stage 1 (Easy): {len(stage1)} examples")

    if stage in ["all", "2"]:
        # Stage 2: Medium tools
        stage2 = generate_curriculum_examples(stage=2)
        all_examples.extend(stage2)
        print(f"Stage 2 (Medium): {len(stage2)} examples")

    if stage in ["all", "3"]:
        # Stage 3: Hard tools
        stage3 = generate_curriculum_examples(stage=3)
        all_examples.extend(stage3)
        print(f"Stage 3 (Hard): {len(stage3)} examples")

    if stage in ["all", "4"]:
        # Stage 4: Multi-tool sequences
        stage4 = generate_multi_tool_examples()
        all_examples.extend(stage4)
        print(f"Stage 4 (Multi-tool): {len(stage4)} examples")

    if stage in ["all", "5"]:
        # Stage 5: Error recovery
        stage5 = generate_error_recovery_examples()
        all_examples.extend(stage5)
        print(f"Stage 5 (Error recovery): {len(stage5)} examples")

    # Shuffle to prevent ordering bias
    random.shuffle(all_examples)

    return all_examples


def save_dataset(
    examples: List[Dict], filename: str = "rosetta_training_expanded.jsonl"
):
    """Save dataset to JSONL file."""
    DATASET_DIR.mkdir(exist_ok=True)
    output_path = DATASET_DIR / filename

    with open(output_path, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nSaved {len(examples)} examples to {output_path}")

    # Print statistics
    categories = {}
    difficulties = {}
    tools = {}
    for ex in examples:
        categories[ex["category"]] = categories.get(ex["category"], 0) + 1
        difficulties[ex["difficulty"]] = difficulties.get(ex["difficulty"], 0) + 1
        tools[ex["tool_name"]] = tools.get(ex["tool_name"], 0) + 1

    print("\n=== Dataset Statistics ===")
    print(f"Total examples: {len(examples)}")
    print(f"Unique tools: {len(tools)}")
    print(f"\nBy difficulty:")
    for d, count in sorted(difficulties.items()):
        print(f"  Stage {d}: {count} examples")
    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} examples")

    return output_path


def validate_dataset(filepath: Path):
    """Validate the generated dataset."""
    print(f"\n=== Validating {filepath} ===")

    with open(filepath) as f:
        lines = f.readlines()

    errors = []
    for i, line in enumerate(lines, 1):
        try:
            example = json.loads(line)

            # Check required fields
            for field in ["input", "output", "tool_name", "args"]:
                if field not in example:
                    errors.append(f"Line {i}: missing field '{field}'")

            # Check input/output are strings
            if "input" in example and not isinstance(example["input"], str):
                errors.append(f"Line {i}: 'input' must be string")
            if "output" in example and not isinstance(example["output"], str):
                errors.append(f"Line {i}: 'output' must be string")

            # Check args is dict
            if "args" in example and not isinstance(example["args"], dict):
                errors.append(f"Line {i}: 'args' must be dict")

        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: JSON parse error - {e}")

    if errors:
        print(f"Found {len(errors)} errors:")
        for err in errors[:10]:  # Show first 10
            print(f"  {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return False
    else:
        print(f"Validation passed! {len(lines)} examples are valid.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate expanded Rosetta training data"
    )
    parser.add_argument(
        "--stage",
        default="all",
        help="Which stage to generate: 1, 2, 3, 4, 5, or 'all'",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate existing dataset"
    )
    parser.add_argument(
        "--output", default="rosetta_training_expanded.jsonl", help="Output filename"
    )
    args = parser.parse_args()

    if args.validate:
        validate_dataset(DATASET_DIR / args.output)
    else:
        print("=== Expanded Rosetta Training Data Generator ===")
        print(f"Generating stage: {args.stage}\n")

        examples = generate_all_training_data(stage=args.stage)
        save_dataset(examples, args.output)

        print("\n=== Next Steps ===")
        print(
            "1. Validate: python scripts/generate_expanded_training_data.py --validate"
        )
        print("2. Train: python packages/training/train_rosetta_unified.py")
        print("3. Test: python nx_engine/nx_engine/local_llm/benchmark_rosetta.py")


if __name__ == "__main__":
    main()
