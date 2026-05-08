#!/usr/bin/env python3
"""
Generate Rosetta training data with CORRECT tool names matching verification.

This creates training data where the tool names EXACTLY match what the
verification script expects (78 MCP function names).
"""

import json
from pathlib import Path

# The 78 tools expected by verification (from verify_rosetta_78.py)
TOOLS = [
    (
        "memory_search",
        [
            "search memory for",
            "find in memory",
            "look up in",
            "query memory for",
            "retrieve from memory",
        ],
    ),
    (
        "memory_write",
        [
            "write to memory",
            "save to memory",
            "store in memory",
            "remember",
            "log to memory",
        ],
    ),
    (
        "memory_stats",
        ["get memory stats", "show memory statistics", "memory usage", "memory info"],
    ),
    (
        "get_active_context",
        ["get active context", "show current context", "what is the active context"],
    ),
    (
        "get_user_context",
        ["get user context", "user preferences", "user profile", "user settings"],
    ),
    (
        "get_bmad_workflows",
        ["get bmad workflows", "list bmad workflows", "show available workflows"],
    ),
    (
        "context_get_bmad_agents",
        ["get bmad agents", "list bmad agents", "show available agents"],
    ),
    (
        "route_task",
        ["route task", "delegate task", "route this task to", "find agent for"],
    ),
    (
        "record_outcome",
        ["record outcome", "log result", "save task outcome", "track success"],
    ),
    (
        "get_learning_stats",
        ["get learning stats", "show learning statistics", "learning progress"],
    ),
    ("git_status", ["git status", "check git status", "show working tree status"]),
    ("git_log", ["git log", "show commits", "recent git history", "git commits"]),
    ("git_diff", ["git diff", "show changes", "view diff", "unstaged changes"]),
    (
        "github_search_code",
        ["search github code", "search code on github", "find in github repos"],
    ),
    ("github_list_issues", ["list github issues", "show issues", "github issues for"]),
    (
        "github_get_file",
        ["get github file", "fetch file from github", "download file from repo"],
    ),
    (
        "github_search_repos",
        ["search github repos", "find repositories", "search repositories"],
    ),
    (
        "github_create_issue",
        ["create github issue", "open issue", "new issue on github"],
    ),
    ("github_create_pr", ["create pull request", "open pull request", "submit pr"]),
    ("github_fork", ["fork repository", "fork repo", "fork on github"]),
    ("github_create_branch", ["create branch", "new branch", "make new branch"]),
    ("fetch_url", ["fetch url", "retrieve url", "get url content"]),
    ("fetch_markdown", ["fetch markdown", "get markdown", "fetch as markdown"]),
    ("fetch_html", ["fetch html", "get html", "fetch as html"]),
    ("fetch_json", ["fetch json", "get json", "fetch as json"]),
    (
        "context7_query_docs",
        ["query context7 docs", "search documentation", "docs for"],
    ),
    (
        "context7_resolve_library",
        ["resolve context7 library", "find library", "lookup library"],
    ),
    (
        "sequential_thinking",
        ["think step by step", "analyze systematically", "reason step by step"],
    ),
    (
        "browser_navigate",
        ["navigate browser", "go to url", "open url in browser", "visit"],
    ),
    ("browser_click", ["click element", "click on", "press button", "click"]),
    ("browser_fill", ["fill form", "type in field", "fill input", "enter text"]),
    ("browser_get_text", ["get element text", "extract text", "read text from"]),
    ("browser_screenshot", ["take screenshot", "capture screen", "screenshot of page"]),
    ("read_file", ["read file", "show file contents", "display file", "cat file"]),
    ("write_file", ["write file", "create file", "save file", "write to"]),
    ("list_directory", ["list directory", "show files", "ls", "list files in"]),
    ("sqlite_query", ["query sqlite", "run sql", "execute sqlite query"]),
    ("sqlite_list_tables", ["list sqlite tables", "show tables", "sqlite tables"]),
    ("sqlite_sample_table", ["sample sqlite table", "get table data", "view table"]),
    ("run_typecheck", ["run type check", "typecheck", "check types"]),
    ("run_lint", ["run lint", "lint code", "check code quality"]),
    ("run_format", ["run format", "format code", "autoformat"]),
    ("run_tests", ["run tests", "execute tests", "run test suite"]),
    ("run_secrets_scan", ["scan for secrets", "check for secrets", "secrets scan"]),
    ("get_health", ["get health", "check health", "system health"]),
    ("session_list", ["list sessions", "show sessions", "all sessions"]),
    ("session_info", ["session info", "get session details", "session metadata"]),
    ("session_read", ["read session", "load session", "get session content"]),
    ("session_search", ["search sessions", "find sessions", "search in sessions"]),
    ("knowledge_search", ["search knowledge", "knowledge search", "find in knowledge"]),
    (
        "knowledge_write",
        ["write knowledge", "save to knowledge", "add to knowledge base"],
    ),
    ("brain_get_mind_state", ["get mind state", "brain state", "mind status"]),
    (
        "brain_update_mind_state",
        ["update mind state", "set mind state", "brain update"],
    ),
    (
        "brain_get_session_history",
        ["get session history", "brain history", "past sessions"],
    ),
    ("brain_context_get_active", ["get brain active context", "brain active context"]),
    ("brain_context_get_user", ["get brain user context", "brain user context"]),
    (
        "brain_context_get_constraints",
        ["get constraints", "show constraints", "behavioral constraints"],
    ),
    ("agent_delegate_task", ["delegate to agent", "delegate task", "send to agent"]),
    ("agent_get_status", ["get agent status", "agent status", "check agent"]),
    ("grep", ["grep", "search in files", "find in codebase"]),
    ("glob", ["glob", "find files", "file pattern search"]),
    ("read", ["read", "read file", "show contents"]),
    ("lsp_diagnostics", ["lsp diagnostics", "show errors", "code diagnostics"]),
    ("lsp_goto_definition", ["go to definition", "jump to definition", "goto def"]),
    ("lsp_find_references", ["find references", "show references", "references"]),
    ("lsp_rename", ["rename symbol", "rename function", "rename variable"]),
    ("athena_smart_search", ["athena search", "smart search", "athena smart"]),
    ("notion_search", ["search notion", "notion search", "find in notion"]),
    ("notion_get_page", ["get notion page", "fetch page", "load notion"]),
    ("notion_create_page", ["create notion page", "new notion page", "add page"]),
    ("notion_update_page", ["update notion page", "modify page", "edit page"]),
    (
        "telegram_send_message",
        ["send telegram message", "telegram send", "send message"],
    ),
    (
        "telegram_get_messages",
        ["get telegram messages", "read telegram", "telegram messages"],
    ),
    ("telegram_get_bot_info", ["get telegram bot info", "bot info", "telegram bot"]),
    ("websearch", ["web search", "search the web", "google search"]),
    ("codesearch", ["code search", "search code", "find code"]),
    ("ask_question", ["ask question", "question", "get answer"]),
    ("done", ["done", "complete", "finish", "task complete"]),
]


def generate_training_data():
    """Generate training data with correct tool names and paraphrases."""
    data = []

    for tool_name, prompts in TOOLS:
        # Generate multiple variations for each tool
        for prompt_base in prompts:
            # Create variations
            variations = [
                prompt_base,
                prompt_base.capitalize(),
                f"Can you {prompt_base}?",
                f"Please {prompt_base}",
                prompt_base.replace(" ", "_"),
            ]

            for variation in variations[:3]:  # Limit per tool
                # Output format - tool name in quotes
                output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ --query "test" }}}}[/TOOL_CALL]'

                data.append({"input": variation, "output": output})

    return data


def main():
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "datasets" / "rosetta_78_correct_train.jsonl"

    print("Generating training data with correct tool names...")
    data = generate_training_data()

    # Write to JSONL
    with open(output_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(data)} training examples")
    print(f"Saved to: {output_path}")

    # Show sample
    print("\nSample:")
    for item in data[:3]:
        print(f"  Input: {item['input']}")
        print(f"  Output: {item['output']}")


if __name__ == "__main__":
    main()
