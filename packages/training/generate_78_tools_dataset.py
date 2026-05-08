#!/usr/bin/env python3
"""Generate comprehensive training data for all 78 system tools.

This script creates the definitive training dataset with diverse prompts for each tool.
"""

import json
from pathlib import Path

# All 78 system tools with multiple prompt variations per tool
TOOLS_DATA = {
    # Memory tools (3)
    "memory_search": {
        "prompts": [
            "search memory for {query}",
            "look up {query} in memory",
            "find {query} in memory",
            "retrieve {query} from memory",
            "query memory about {query}",
        ],
        "args": {"query": ["authentication tokens", "security patterns", "deployment config", "API keys", "user preferences"]},
    },
    "memory_write": {
        "prompts": [
            "write this to memory: {content}",
            "save {content} to memory",
            "store {content} in memory",
            "remember that {content}",
        ],
        "args": {"content": ["user logged in", "API key rotated", "deployment successful", "config updated"]},
    },
    "memory_stats": {
        "prompts": [
            "get memory statistics",
            "show memory stats",
            "how much memory is used",
            "memory usage report",
        ],
        "args": {},
    },
    
    # Context tools (4)
    "get_active_context": {
        "prompts": [
            "get the active context",
            "what is the current context",
            "show current working context",
            "get context",
        ],
        "args": {},
    },
    "get_user_context": {
        "prompts": [
            "get user context",
            "show user preferences",
            "get user settings",
            "what are the user preferences",
        ],
        "args": {},
    },
    "get_bmad_workflows": {
        "prompts": [
            "list bmad workflows",
            "show available workflows",
            "what workflows exist",
            "get workflow list",
        ],
        "args": {},
    },
    "context_get_bmad_agents": {
        "prompts": [
            "list bmad agents",
            "show available agents",
            "what agents exist",
            "get agent list",
        ],
        "args": {},
    },
    
    # Learning tools (3)
    "route_task": {
        "prompts": [
            "route this task to the right agent",
            "which agent should handle this",
            "select agent for {task}",
            "route {task}",
        ],
        "args": {"task": ["fix bug", "add feature", "refactor code", "write tests"]},
    },
    "record_outcome": {
        "prompts": [
            "record this outcome",
            "log the result of {task}",
            "save outcome: {task} was {result}",
            "record {task} {result}",
        ],
        "args": {"task": ["fix bug", "deployment"], "result": ["success", "failed"]},
    },
    "get_learning_stats": {
        "prompts": [
            "show learning statistics",
            "get routing accuracy",
            "how well is the model performing",
            "learning metrics",
        ],
        "args": {},
    },
    
    # Git tools (3)
    "git_status": {
        "prompts": [
            "check git status",
            "what files are changed",
            "git status",
            "show modified files",
        ],
        "args": {},
    },
    "git_log": {
        "prompts": [
            "show recent commits",
            "git log",
            "what commits were made",
            "recent git history",
        ],
        "args": {},
    },
    "git_diff": {
        "prompts": [
            "show git diff",
            "what changes were made",
            "git diff",
            "diff against HEAD",
        ],
        "args": {},
    },
    
    # GitHub tools (9)
    "github_search_code": {
        "prompts": [
            "search code on github for {query}",
            "find {query} on github",
            "github code search {query}",
            "search github for {query}",
        ],
        "args": {"query": ["auth middleware", "react hooks", "api client"]},
    },
    "github_list_issues": {
        "prompts": [
            "list issues for {owner}/{repo}",
            "show open issues",
            "github issues",
            "what issues exist",
        ],
        "args": {"owner": ["facebook", "microsoft", "openai"], "repo": ["react", "vscode", "chatgpt"]},
    },
    "github_get_file": {
        "prompts": [
            "get file {path} from {owner}/{repo}",
            "show github file {path}",
            "read github file {path}",
        ],
        "args": {"owner": ["owner"], "repo": ["repo"], "path": ["README.md", "package.json"]},
    },
    "github_search_repos": {
        "prompts": [
            "search repositories for {query}",
            "find github repos about {query}",
            "search repos {query}",
        ],
        "args": {"query": ["react", "typescript", "machine learning"]},
    },
    "github_create_issue": {
        "prompts": [
            "create issue: {title}",
            "open a github issue",
            "file a bug report: {title}",
            "submit issue {title}",
        ],
        "args": {"title": ["Bug in auth", "Feature request", "Performance issue"]},
    },
    "github_create_pr": {
        "prompts": [
            "create pull request: {title}",
            "open a PR",
            "submit pull request {title}",
            "file PR {title}",
        ],
        "args": {"title": ["Add feature", "Fix bug", "Update deps"]},
    },
    "github_fork": {
        "prompts": [
            "fork {owner}/{repo}",
            "fork this repository",
            "create a fork",
        ],
        "args": {"owner": ["owner"], "repo": ["repo"]},
    },
    "github_create_branch": {
        "prompts": [
            "create branch {branch}",
            "make a new branch",
            "add branch {branch}",
        ],
        "args": {"branch": ["feature/new-feature", "bugfix/fix-123"]},
    },
    "github_list_prs": {
        "prompts": [
            "list pull requests",
            "show open PRs",
            "github PRs",
        ],
        "args": {},
    },
    
    # Fetch tools (4)
    "fetch_url": {
        "prompts": [
            "fetch {url}",
            "get content from {url}",
            "visit {url}",
            "retrieve {url}",
        ],
        "args": {"url": ["https://python.org", "https://github.com"]},
    },
    "fetch_markdown": {
        "prompts": [
            "get markdown from {url}",
            "fetch markdown {url}",
            "scrape markdown {url}",
        ],
        "args": {"url": ["https://example.com"]},
    },
    "fetch_html": {
        "prompts": [
            "fetch html from {url}",
            "get raw HTML {url}",
            "scrape {url} as HTML",
        ],
        "args": {"url": ["https://example.com"]},
    },
    "fetch_json": {
        "prompts": [
            "fetch json from {url}",
            "get API data {url}",
            "retrieve JSON {url}",
        ],
        "args": {"url": ["https://api.github.com"]},
    },
    
    # Context7 tools (2)
    "context7_query_docs": {
        "prompts": [
            "query context7 docs for {library}",
            "search {library} documentation",
            "context7 {library} {query}",
        ],
        "args": {"library": ["react", "nextjs"], "query": ["hooks", "components"]},
    },
    "context7_resolve_library": {
        "prompts": [
            "resolve library id for {library}",
            "get library ID {library}",
            "lookup {library}",
        ],
        "args": {"library": ["react", "vue", "angular"]},
    },
    
    # Sequential thinking (1)
    "sequential_thinking": {
        "prompts": [
            "think step by step about this",
            "reason through this problem",
            "analyze this step by step",
            "sequential thinking: {thought}",
        ],
        "args": {"thought": ["the bug is caused by...", "we need to..."]},
    },
    
    # Browser tools (5)
    "browser_navigate": {
        "prompts": [
            "navigate to {url}",
            "go to {url}",
            "open {url} in browser",
            "visit {url}",
        ],
        "args": {"url": ["https://github.com", "https://google.com"]},
    },
    "browser_click": {
        "prompts": [
            "click {selector}",
            "click on {selector}",
            "press {selector} button",
        ],
        "args": {"selector": ["#login", "button.submit", ".btn-primary"]},
    },
    "browser_fill": {
        "prompts": [
            "fill {selector} with {value}",
            "type {value} in {selector}",
            "enter {value} in {selector}",
        ],
        "args": {"selector": ["#username", "#password"], "value": ["testuser", "password123"]},
    },
    "browser_get_text": {
        "prompts": [
            "get text from {selector}",
            "extract text from {selector}",
            "read {selector} content",
        ],
        "args": {"selector": ["h1", ".title", "#header"]},
    },
    "browser_screenshot": {
        "prompts": [
            "take a screenshot",
            "capture the page",
            "screenshot",
        ],
        "args": {},
    },
    
    # File tools (3)
    "read_file": {
        "prompts": [
            "read {path}",
            "show me {path}",
            "display {path}",
            "cat {path}",
        ],
        "args": {"path": ["README.md", "src/main.py", "config.json"]},
    },
    "write_file": {
        "prompts": [
            "write {content} to {path}",
            "save {content} as {path}",
            "create {path} with {content}",
        ],
        "args": {"path": ["test.txt", "output.json"], "content": ["hello world", "test data"]},
    },
    "list_directory": {
        "prompts": [
            "list files in {path}",
            "show directory {path}",
            "ls {path}",
            "what files are in {path}",
        ],
        "args": {"path": [".", "src", "tests"]},
    },
    
    # SQLite tools (3)
    "sqlite_query": {
        "prompts": [
            "query the database",
            "run SQL: {sql}",
            "execute {sql}",
        ],
        "args": {"sql": ["SELECT * FROM users", "SELECT COUNT(*) FROM logs"]},
    },
    "sqlite_list_tables": {
        "prompts": [
            "list all tables",
            "show database tables",
            "what tables exist",
        ],
        "args": {},
    },
    "sqlite_sample_table": {
        "prompts": [
            "get sample from {table}",
            "show {table} rows",
            "sample {table}",
        ],
        "args": {"table": ["users", "logs", "sessions"]},
    },
    
    # Quality gates (5)
    "run_typecheck": {
        "prompts": [
            "run type check",
            "typecheck",
            "check types",
        ],
        "args": {},
    },
    "run_lint": {
        "prompts": [
            "run linter",
            "lint",
            "check code style",
        ],
        "args": {},
    },
    "run_format": {
        "prompts": [
            "run formatter",
            "format code",
            "check formatting",
        ],
        "args": {},
    },
    "run_tests": {
        "prompts": [
            "run tests",
            "execute test suite",
            "run pytest",
        ],
        "args": {},
    },
    "run_secrets_scan": {
        "prompts": [
            "scan for secrets",
            "check for API keys",
            "security scan",
        ],
        "args": {},
    },
    
    # Health checks (1)
    "get_health": {
        "prompts": [
            "check system health",
            "health status",
            "is the system healthy",
            "system status",
        ],
        "args": {},
    },
    
    # Session tools (4)
    "session_list": {
        "prompts": [
            "list all sessions",
            "show sessions",
            "what sessions exist",
        ],
        "args": {},
    },
    "session_info": {
        "prompts": [
            "get info for session {id}",
            "session {id} details",
            "show session {id}",
        ],
        "args": {"id": ["123", "abc"]},
    },
    "session_read": {
        "prompts": [
            "read messages from session {id}",
            "get session {id} history",
        ],
        "args": {"id": ["123", "abc"]},
    },
    "session_search": {
        "prompts": [
            "search sessions for {query}",
            "find in sessions: {query}",
        ],
        "args": {"query": ["auth", "bug"]},
    },
    
    # Knowledge tools (2)
    "knowledge_search": {
        "prompts": [
            "search knowledge base",
            "query knowledge for {query}",
            "find in knowledge: {query}",
        ],
        "args": {"query": ["authentication", "security"]},
    },
    "knowledge_write": {
        "prompts": [
            "write to knowledge base",
            "add to knowledge: {content}",
        ],
        "args": {"content": ["important info", "learned lesson"]},
    },
    
    # Brain tools (7)
    "brain_get_mind_state": {
        "prompts": [
            "get mind state",
            "what is the current phase",
            "project state",
        ],
        "args": {},
    },
    "brain_update_mind_state": {
        "prompts": [
            "update mind state to {phase}",
            "set phase to {phase}",
            "change state to {phase}",
        ],
        "args": {"phase": ["planning", "execution", "review"]},
    },
    "brain_get_session_history": {
        "prompts": [
            "get session history",
            "what sessions did we have",
            "past sessions",
        ],
        "args": {},
    },
    "brain_context_get_active": {
        "prompts": [
            "get active context",
            "current working context",
        ],
        "args": {},
    },
    "brain_context_get_user": {
        "prompts": [
            "get user context",
            "user preferences",
        ],
        "args": {},
    },
    "brain_context_get_constraints": {
        "prompts": [
            "get constraints",
            "show system constraints",
        ],
        "args": {},
    },
    "brain_update_mind_state": {
        "prompts": [
            "update mind state",
            "change project phase",
        ],
        "args": {},
    },
    
    # Agent tools (2)
    "agent_delegate_task": {
        "prompts": [
            "delegate to {agent}",
            "assign to {agent}: {task}",
            "send {task} to {agent}",
        ],
        "args": {"agent": ["hephaestus", "oracle"], "task": ["fix bug", "add feature"]},
    },
    "agent_get_status": {
        "prompts": [
            "get agent status",
            "is {agent} running",
            "{agent} status",
        ],
        "args": {"agent": ["hephaestus", "oracle"]},
    },
    
    # File search tools (3)
    "grep": {
        "prompts": [
            "grep for {pattern}",
            "search for {pattern} in {path}",
            "find {pattern}",
        ],
        "args": {"pattern": ["function", "class"], "path": ["src", "."]},
    },
    "glob": {
        "prompts": [
            "glob {pattern}",
            "find files matching {pattern}",
            "list {pattern}",
        ],
        "args": {"pattern": ["**/*.py", "**/*.js"]},
    },
    "read": {
        "prompts": [
            "read {filePath}",
            "show {filePath}",
            "cat {filePath}",
        ],
        "args": {"filePath": ["main.py", "index.js"]},
    },
    
    # LSP tools (4)
    "lsp_diagnostics": {
        "prompts": [
            "check errors in {filePath}",
            "diagnostics for {filePath}",
            "lint {filePath}",
        ],
        "args": {"filePath": ["auth.py", "main.py"]},
    },
    "lsp_goto_definition": {
        "prompts": [
            "go to definition of {symbol}",
            "find {symbol} definition",
            "jump to {symbol}",
        ],
        "args": {"symbol": ["getUser", "parseConfig"]},
    },
    "lsp_find_references": {
        "prompts": [
            "find references to {symbol}",
            "where is {symbol} used",
            "references for {symbol}",
        ],
        "args": {"symbol": ["User", "Config"]},
    },
    "lsp_rename": {
        "prompts": [
            "rename {old} to {new}",
            "rename symbol {old}",
            "change {old} -> {new}",
        ],
        "args": {"old": ["getUser"], "new": ["fetchCurrentUser"]},
    },
    
    # Athena tools (1)
    "athena_smart_search": {
        "prompts": [
            "smart search for {query}",
            "athena search {query}",
            "query athena: {query}",
        ],
        "args": {"query": ["security", "performance"]},
    },
    
    # Notion tools (4)
    "notion_search": {
        "prompts": [
            "search notion",
            "query notion for {query}",
            "find in notion: {query}",
        ],
        "args": {"query": ["meeting notes", "project plan"]},
    },
    "notion_get_page": {
        "prompts": [
            "get notion page {page_id}",
            "fetch page {page_id}",
        ],
        "args": {"page_id": ["abc123"]},
    },
    "notion_create_page": {
        "prompts": [
            "create notion page: {title}",
            "new notion page {title}",
            "add page: {title}",
        ],
        "args": {"title": ["Meeting Notes", "Task List"]},
    },
    "notion_update_page": {
        "prompts": [
            "update notion page {page_id}",
            "edit page {page_id}",
        ],
        "args": {"page_id": ["abc123"]},
    },
    
    # Telegram tools (3)
    "telegram_send_message": {
        "prompts": [
            "send telegram message: {text}",
            "message via telegram: {text}",
            "telegram: {text}",
        ],
        "args": {"text": ["Hello!", "Task completed"]},
    },
    "telegram_get_messages": {
        "prompts": [
            "get telegram messages",
            "check telegram",
            "telegram inbox",
        ],
        "args": {},
    },
    "telegram_get_bot_info": {
        "prompts": [
            "get bot info",
            "telegram bot status",
            "bot information",
        ],
        "args": {},
    },
    
    # Web search tools (2)
    "websearch": {
        "prompts": [
            "search the web for {query}",
            "web search: {query}",
            "google {query}",
            "look up {query}",
        ],
        "args": {"query": ["latest AI news", "python tips"]},
    },
    "codesearch": {
        "prompts": [
            "search code examples for {query}",
            "find {query} code",
            "code search: {query}",
        ],
        "args": {"query": ["react hooks", "async python"]},
    },
    
    # Misc tools (2)
    "ask_question": {
        "prompts": [
            "answer this question: {question}",
            "what is {question}",
            "explain {question}",
        ],
        "args": {"question": ["2+2", "how does X work"]},
    },
    "done": {
        "prompts": [
            "mark task as done",
            "task complete",
            "done",
            "finished",
        ],
        "args": {},
    },
}


def generate_dataset():
    """Generate the complete training dataset."""
    dataset = []
    
    for tool_name, config in TOOLS_DATA.items():
        prompts = config["prompts"]
        args_config = config["args"]
        
        # Generate combinations
        for prompt_template in prompts:
            if args_config:
                # Simple single-arg substitution for now
                for arg_name, arg_values in args_config.items():
                    for arg_value in arg_values:
                        if f"{{{arg_name}}}" in prompt_template:
                            prompt = prompt_template.replace(f"{{{arg_name}}}", arg_value)
                            # Build args dict
                            args = {arg_name: arg_value}
                            # Generate output
                            output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ --{arg_name} "{arg_value}" }}}}[/TOOL_CALL]'
                            dataset.append({
                                "input": prompt,
                                "output": output,
                                "tool_name": tool_name,
                                "args": args,
                            })
            else:
                # No args - just use the prompt as-is
                prompt = prompt_template
                output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}[/TOOL_CALL]'
                dataset.append({
                    "input": prompt,
                    "output": output,
                    "tool_name": tool_name,
                    "args": {},
                })
    
    return dataset


def main():
    print("Generating training dataset for all 78 tools...")
    dataset = generate_dataset()
    
    output_path = Path(__file__).parent.parent.parent / "datasets" / "rosetta_78_tools_final.jsonl"
    
    with open(output_path, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")
    
    # Count unique tools
    unique_tools = set(item["tool_name"] for item in dataset)
    print(f"\nGenerated {len(dataset)} examples for {len(unique_tools)} tools:")
    for tool in sorted(unique_tools):
        count = sum(1 for item in dataset if item["tool_name"] == tool)
        print(f"  {tool}: {count} examples")
    
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
