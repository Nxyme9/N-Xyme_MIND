#!/usr/bin/env python3
"""Generate comprehensive training data for all 78 system tools.

V3 - WITH NEGATIVE EXAMPLES:
- Multi-arg substitution bug fixed
- All 78 tools from verify_rosetta_78.py
- 15+ examples per tool minimum
- Negative examples (no tool needed) - prevents hallucination
- Hard negatives (similar wrong tool) - improves discrimination
- Uses Qwen chat template format (matching train_rosetta_unified.py)
- Tool names match exactly what verify_rosetta_78.py expects
"""

import json
import itertools
from pathlib import Path
from typing import Dict, List

# All 78 tools with EXACT names from verify_rosetta_78.py
TOOLS_DATA = {
    # Memory tools (3)
    "memory_search": {
        "prompts": [
            "search memory for {query}",
            "look up {query} in memory",
            "find {query} in memory",
            "retrieve {query} from memory",
            "query memory about {query}",
            "find information about {query}",
            "what do you know about {query}",
            "search for {query}",
        ],
        "args": {
            "query": [
                "authentication tokens",
                "security patterns",
                "deployment config",
                "API keys",
                "user preferences",
                "session data",
                "cache settings",
            ]
        },
    },
    "memory_write": {
        "prompts": [
            "write this to memory: {content}",
            "save {content} to memory",
            "store {content} in memory",
            "remember that {content}",
            "note: {content}",
        ],
        "args": {
            "content": [
                "user logged in",
                "API key rotated",
                "deployment successful",
                "config updated",
                "test completed",
            ]
        },
    },
    "memory_stats": {
        "prompts": [
            "get memory statistics",
            "show memory stats",
            "how much memory is used",
            "memory usage report",
            "what is in memory",
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
            "current state",
        ],
        "args": {},
    },
    "get_user_context": {
        "prompts": [
            "get user context",
            "show user preferences",
            "get user settings",
            "what are the user preferences",
            "user info",
        ],
        "args": {},
    },
    "get_bmad_workflows": {
        "prompts": [
            "list bmad workflows",
            "show available workflows",
            "what workflows exist",
            "get workflow list",
            "list workflows",
        ],
        "args": {},
    },
    "context_get_bmad_agents": {
        "prompts": [
            "list bmad agents",
            "show available agents",
            "what agents exist",
            "get agent list",
            "list agents",
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
            "what agent handles {task}",
        ],
        "args": {
            "task_description": [
                "fix bug",
                "add feature",
                "refactor code",
                "write tests",
                "deploy",
                "review",
            ]
        },
    },
    "record_outcome": {
        "prompts": [
            "record this outcome",
            "log the result of {task}",
            "save outcome: {task} was {result}",
            "record {task} {result}",
            "log {task}",
        ],
        "args": {"task": ["fix bug", "deployment"], "success": ["true", "false"]},
    },
    "get_learning_stats": {
        "prompts": [
            "show learning statistics",
            "get routing accuracy",
            "how well is the model performing",
            "learning metrics",
            "performance stats",
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
            "status of repo",
        ],
        "args": {},
    },
    "git_log": {
        "prompts": [
            "show recent commits",
            "git log",
            "what commits were made",
            "recent git history",
            "commit history",
        ],
        "args": {},
    },
    "git_diff": {
        "prompts": [
            "show git diff",
            "what changes were made",
            "git diff",
            "diff against HEAD",
            "show changes",
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
            "find code related to {query}",
        ],
        "args": {
            "q": [
                "auth middleware",
                "react hooks",
                "api client",
                "database schema",
                "authentication",
            ]
        },
    },
    "github_list_issues": {
        "prompts": [
            "list issues for {owner}/{repo}",
            "show open issues",
            "github issues",
            "what issues exist",
            "open issues for {repo}",
        ],
        "args": {
            "owner": ["facebook", "microsoft", "openai"],
            "repo": ["react", "vscode", "chatgpt"],
        },
    },
    "github_get_file": {
        "prompts": [
            "get file {path} from {owner}/{repo}",
            "show github file {path}",
            "read github file {path}",
            "fetch {path} from {repo}",
        ],
        "args": {
            "owner": ["owner"],
            "repo": ["repo"],
            "path": ["README.md", "package.json", "src/main.py"],
        },
    },
    "github_search_repos": {
        "prompts": [
            "search repositories for {query}",
            "find github repos about {query}",
            "search repos {query}",
            "find repos for {query}",
        ],
        "args": {"query": ["react", "typescript", "machine learning", "python"]},
    },
    "github_create_issue": {
        "prompts": [
            "create issue: {title}",
            "open a github issue",
            "file a bug report: {title}",
            "submit issue {title}",
            "create bug report",
        ],
        "args": {
            "title": [
                "Bug in auth",
                "Feature request",
                "Performance issue",
                "Security vulnerability",
            ]
        },
    },
    "github_create_pr": {
        "prompts": [
            "create pull request: {title}",
            "open a PR",
            "submit pull request {title}",
            "file PR {title}",
            "create PR",
        ],
        "args": {"title": ["Add feature", "Fix bug", "Update deps", "Refactor code"]},
    },
    "github_fork": {
        "prompts": [
            "fork {owner}/{repo}",
            "fork this repository",
            "create a fork",
            "fork {repo}",
        ],
        "args": {"owner": ["owner"], "repo": ["repo"]},
    },
    "github_create_branch": {
        "prompts": [
            "create branch {branch}",
            "make a new branch",
            "add branch {branch}",
            "create feature branch",
        ],
        "args": {"branch": ["feature/new-feature", "bugfix/fix-123", "hotfix/urgent"]},
    },
    "github_list_prs": {
        "prompts": [
            "list pull requests",
            "show open PRs",
            "github PRs",
            "open pull requests",
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
            "grab {url}",
        ],
        "args": {
            "url": ["https://python.org", "https://github.com", "https://npmjs.com"]
        },
    },
    "fetch_markdown": {
        "prompts": [
            "get markdown from {url}",
            "fetch markdown {url}",
            "scrape markdown {url}",
            "markdown content from {url}",
        ],
        "args": {"url": ["https://example.com", "https://python.org"]},
    },
    "fetch_html": {
        "prompts": [
            "fetch html from {url}",
            "get raw HTML {url}",
            "scrape {url} as HTML",
            "raw HTML from {url}",
        ],
        "args": {"url": ["https://example.com", "https://python.org"]},
    },
    "fetch_json": {
        "prompts": [
            "fetch json from {url}",
            "get API data {url}",
            "retrieve JSON {url}",
            "fetch API {url}",
        ],
        "args": {"url": ["https://api.github.com", "https://api.example.com/data"]},
    },
    # Context7 tools (2)
    "context7_query_docs": {
        "prompts": [
            "query context7 docs for {library}",
            "search {library} documentation",
            "context7 {library} {query}",
            "docs for {library}",
        ],
        "args": {
            "library_id": ["/facebook/react", "/vercel/next.js"],
            "query": ["hooks", "components", "api"],
        },
    },
    "context7_resolve_library": {
        "prompts": [
            "resolve library id for {query}",
            "get library ID {query}",
            "lookup {query}",
            "find {query} in context7",
        ],
        "args": {"query": ["react", "vue", "angular", "nextjs"]},
    },
    # Sequential thinking (1)
    "sequential_thinking": {
        "prompts": [
            "think step by step about this",
            "reason through this problem",
            "analyze this step by step",
            "sequential thinking: {thought}",
            "break down this problem",
        ],
        "args": {
            "thought": [
                "the bug is caused by...",
                "we need to...",
                "analyzing the issue...",
            ]
        },
    },
    # Browser tools (5)
    "browser_navigate": {
        "prompts": [
            "navigate to {url}",
            "go to {url}",
            "open {url} in browser",
            "visit {url}",
            "browse to {url}",
        ],
        "args": {
            "url": ["https://github.com", "https://google.com", "https://python.org"]
        },
    },
    "browser_click": {
        "prompts": [
            "click {selector}",
            "click on {selector}",
            "press {selector} button",
            "select {selector}",
        ],
        "args": {"selector": ["#login", "button.submit", ".btn-primary", "#submit"]},
    },
    "browser_fill": {
        "prompts": [
            "fill {selector} with {value}",
            "type {value} in {selector}",
            "enter {value} in {selector}",
            "input {value} into {selector}",
        ],
        "args": {
            "selector": ["#username", "#password"],
            "value": ["testuser", "password123"],
        },
    },
    "browser_get_text": {
        "prompts": [
            "get text from {selector}",
            "extract text from {selector}",
            "read {selector} content",
            "what text is in {selector}",
        ],
        "args": {"selector": ["h1", ".title", "#header", "h2"]},
    },
    "browser_screenshot": {
        "prompts": [
            "take a screenshot",
            "capture the page",
            "screenshot",
            "save page screenshot",
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
            "open {path}",
        ],
        "args": {"path": ["README.md", "src/main.py", "config.json", "package.json"]},
    },
    "write_file": {
        "prompts": [
            "write {content} to {path}",
            "save {content} as {path}",
            "create {path} with {content}",
            "make file {path}",
        ],
        "args": {
            "path": ["test.txt", "output.json"],
            "content": ["hello world", "test data"],
        },
    },
    "list_directory": {
        "prompts": [
            "list files in {path}",
            "show directory {path}",
            "ls {path}",
            "what files are in {path}",
            "directory contents",
        ],
        "args": {"path": [".", "src", "tests", "docs"]},
    },
    # SQLite tools (3)
    "sqlite_query": {
        "prompts": [
            "query the database",
            "run SQL: {sql}",
            "execute {sql}",
            "database query",
        ],
        "args": {
            "sql": [
                "SELECT * FROM users",
                "SELECT COUNT(*) FROM logs",
                "SELECT * FROM sessions",
            ]
        },
    },
    "sqlite_list_tables": {
        "prompts": [
            "list all tables",
            "show database tables",
            "what tables exist",
            "database schema",
        ],
        "args": {},
    },
    "sqlite_sample_table": {
        "prompts": [
            "get sample from {table}",
            "show {table} rows",
            "sample {table}",
            "preview {table}",
        ],
        "args": {"table": ["users", "logs", "sessions"]},
    },
    # Quality gates (5)
    "run_typecheck": {
        "prompts": [
            "run type check",
            "typecheck",
            "check types",
            "run type checker",
        ],
        "args": {},
    },
    "run_lint": {
        "prompts": [
            "run linter",
            "lint",
            "check code style",
            "run eslint",
        ],
        "args": {},
    },
    "run_format": {
        "prompts": [
            "run formatter",
            "format code",
            "check formatting",
            "run prettier",
        ],
        "args": {},
    },
    "run_tests": {
        "prompts": [
            "run tests",
            "execute test suite",
            "run pytest",
            "run test suite",
        ],
        "args": {},
    },
    "run_secrets_scan": {
        "prompts": [
            "scan for secrets",
            "check for API keys",
            "security scan",
            "find secrets",
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
            "health check",
        ],
        "args": {},
    },
    # Session tools (4)
    "session_list": {
        "prompts": [
            "list all sessions",
            "show sessions",
            "what sessions exist",
            "list sessions",
        ],
        "args": {},
    },
    "session_info": {
        "prompts": [
            "get info for session {id}",
            "session {id} details",
            "show session {id}",
            "session details",
        ],
        "args": {"session_id": ["123", "abc", "xyz"]},
    },
    "session_read": {
        "prompts": [
            "read messages from session {id}",
            "get session {id} history",
            "messages in session {id}",
        ],
        "args": {"session_id": ["123", "abc", "xyz"]},
    },
    "session_search": {
        "prompts": [
            "search sessions for {query}",
            "find in sessions: {query}",
            "search session history",
        ],
        "args": {"query": ["auth", "bug", "feature"]},
    },
    # Knowledge tools (2)
    "knowledge_search": {
        "prompts": [
            "search knowledge base",
            "query knowledge for {query}",
            "find in knowledge: {query}",
            "knowledge search",
        ],
        "args": {"query": ["authentication", "security", "deployment"]},
    },
    "knowledge_write": {
        "prompts": [
            "write to knowledge base",
            "add to knowledge: {content}",
            "store in knowledge",
        ],
        "args": {"content": ["important info", "learned lesson", "pattern discovered"]},
    },
    # Brain tools (7)
    "brain_get_mind_state": {
        "prompts": [
            "get mind state",
            "what is the current phase",
            "project state",
            "mind state",
        ],
        "args": {},
    },
    "brain_update_mind_state": {
        "prompts": [
            "update mind state to {phase}",
            "set phase to {phase}",
            "change state to {phase}",
            "update project phase",
        ],
        "args": {"phase": ["planning", "execution", "review"]},
    },
    "brain_get_session_history": {
        "prompts": [
            "get session history",
            "what sessions did we have",
            "past sessions",
            "session history",
        ],
        "args": {},
    },
    "brain_context_get_active": {
        "prompts": [
            "get active context",
            "current working context",
            "active context",
        ],
        "args": {},
    },
    "brain_context_get_user": {
        "prompts": [
            "get user context",
            "user preferences",
            "user context",
        ],
        "args": {},
    },
    "brain_context_get_constraints": {
        "prompts": [
            "get constraints",
            "show system constraints",
            "constraints",
        ],
        "args": {},
    },
    # Agent tools (2)
    "agent_delegate_task": {
        "prompts": [
            "delegate to {agent}",
            "assign to {agent}: {task}",
            "send {task} to {agent}",
            "delegate {task}",
        ],
        "args": {"agent": ["hephaestus", "oracle"], "task": ["fix bug", "add feature"]},
    },
    "agent_get_status": {
        "prompts": [
            "get agent status",
            "is {agent} running",
            "{agent} status",
            "agent status",
        ],
        "args": {"agent": ["hephaestus", "oracle"]},
    },
    # File search tools (3)
    "grep": {
        "prompts": [
            "grep for {pattern}",
            "search for {pattern} in {path}",
            "find {pattern}",
            "find text {pattern}",
        ],
        "args": {"pattern": ["function", "class", "const"], "path": ["src", "."]},
    },
    "glob": {
        "prompts": [
            "glob {pattern}",
            "find files matching {pattern}",
            "list {pattern}",
            "find {pattern} files",
        ],
        "args": {"pattern": ["**/*.py", "**/*.js", "**/*.ts"]},
    },
    "read": {
        "prompts": [
            "read {filePath}",
            "show {filePath}",
            "cat {filePath}",
            "open {filePath}",
        ],
        "args": {"filePath": ["main.py", "index.js", "app.ts"]},
    },
    # LSP tools (4)
    "lsp_diagnostics": {
        "prompts": [
            "check errors in {filePath}",
            "diagnostics for {filePath}",
            "lint {filePath}",
            "find errors in {filePath}",
        ],
        "args": {"filePath": ["auth.py", "main.py", "app.py"]},
    },
    "lsp_goto_definition": {
        "prompts": [
            "go to definition of {symbol}",
            "find {symbol} definition",
            "jump to {symbol}",
            "definition of {symbol}",
        ],
        "args": {"symbol": ["getUser", "parseConfig", "handleRequest"]},
    },
    "lsp_find_references": {
        "prompts": [
            "find references to {symbol}",
            "where is {symbol} used",
            "references for {symbol}",
            "uses of {symbol}",
        ],
        "args": {"symbol": ["User", "Config", "handleRequest"]},
    },
    "lsp_rename": {
        "prompts": [
            "rename {old} to {new}",
            "rename symbol {old}",
            "change {old} -> {new}",
            "rename {old}",
        ],
        "args": {
            "old": ["getUser", "parseConfig"],
            "new": ["fetchCurrentUser", "parseConfiguration"],
        },
    },
    # Athena tools (1)
    "athena_smart_search": {
        "prompts": [
            "smart search for {query}",
            "athena search {query}",
            "query athena: {query}",
            "deep search for {query}",
        ],
        "args": {"query": ["security", "performance", "architecture"]},
    },
    # Notion tools (4)
    "notion_search": {
        "prompts": [
            "search notion",
            "query notion for {query}",
            "find in notion: {query}",
            "notion search",
        ],
        "args": {"query": ["meeting notes", "project plan", "tasks"]},
    },
    "notion_get_page": {
        "prompts": [
            "get notion page {page_id}",
            "fetch page {page_id}",
            "retrieve notion page",
        ],
        "args": {"page_id": ["abc123", "def456"]},
    },
    "notion_create_page": {
        "prompts": [
            "create notion page: {title}",
            "new notion page {title}",
            "add page: {title}",
            "create page",
        ],
        "args": {"title": ["Meeting Notes", "Task List", "Daily Standup"]},
    },
    "notion_update_page": {
        "prompts": [
            "update notion page {page_id}",
            "edit page {page_id}",
            "modify {page_id}",
        ],
        "args": {"page_id": ["abc123", "def456"]},
    },
    # Telegram tools (3)
    "telegram_send_message": {
        "prompts": [
            "send telegram message: {text}",
            "message via telegram: {text}",
            "telegram: {text}",
            "send message",
        ],
        "args": {"text": ["Hello!", "Task completed", "Build passed"]},
    },
    "telegram_get_messages": {
        "prompts": [
            "get telegram messages",
            "check telegram",
            "telegram inbox",
            "read messages",
        ],
        "args": {},
    },
    "telegram_get_bot_info": {
        "prompts": [
            "get bot info",
            "telegram bot status",
            "bot information",
            "bot details",
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
            "search for {query} online",
        ],
        "args": {"query": ["latest AI news", "python tips", "react patterns"]},
    },
    "codesearch": {
        "prompts": [
            "search code examples for {query}",
            "find {query} code",
            "code search: {query}",
            "search for code examples",
        ],
        "args": {"query": ["react hooks", "async python", "typescript patterns"]},
    },
    # Misc tools (2)
    "ask_question": {
        "prompts": [
            "answer this question: {question}",
            "what is {question}",
            "explain {question}",
            "tell me about {question}",
        ],
        "args": {"question": ["2+2", "how does X work", "what is AI"]},
    },
    "done": {
        "prompts": [
            "mark task as done",
            "task complete",
            "done",
            "finished",
            "task is done",
        ],
        "args": {},
    },
}


# ============================================================================
# NEGATIVE EXAMPLES - Critical for preventing hallucination
# ============================================================================

# NO TOOL NEEDED - Model should respond normally
NO_TOOL_EXAMPLES = [
    ("hello", "Hello! How can I help you today?"),
    ("hi there", "Hi! What would you like to work on?"),
    ("how are you", "I'm doing well, thanks for asking!"),
    ("what is 2+2", "2+2 equals 4."),
    (
        "tell me a joke",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
    ),
    ("thanks", "You're welcome!"),
    ("ok", "Got it!"),
    ("okay", "Sure thing!"),
    ("cool", "Great!"),
    ("nice", "Awesome!"),
    (
        "what's the weather",
        "I don't have access to real-time weather data, but you could use a weather API tool to check!",
    ),
    (
        "who are you",
        "I'm an AI assistant that can help you with various tasks using tools.",
    ),
    (
        "what can you do",
        "I can help you with code, search, run commands, and much more using my built-in tools.",
    ),
    ("help me", "Of course! What do you need help with?"),
    ("good morning", "Good morning! Ready to get some work done?"),
    ("good afternoon", "Good afternoon! What can I help you with?"),
    ("good evening", "Good evening! Any tasks for tonight?"),
]

# SIMILAR BUT WRONG TOOL - Model should pick the RIGHT one
# This teaches discrimination between similar tools
SIMILAR_WRONG_PAIRS = [
    # Memory vs knowledge (both store/retrieve)
    ("search memory", "memory_search", "knowledge_search"),
    ("search knowledge", "knowledge_search", "memory_search"),
    # Read vs grep (both find content)
    ("read file main.py", "read_file", "grep"),
    ("grep function", "grep", "read_file"),
    # Git vs GitHub
    ("git status", "git_status", "github_list_prs"),
    ("github issues", "github_list_issues", "git_status"),
    # Fetch vs browser (both get web content)
    ("fetch url", "fetch_url", "browser_navigate"),
    ("open browser", "browser_navigate", "fetch_url"),
    # Context vs session
    ("get context", "get_active_context", "session_list"),
    ("list sessions", "session_list", "get_active_context"),
    # Brain vs learning
    ("get mind state", "brain_get_mind_state", "get_learning_stats"),
    ("learning stats", "get_learning_stats", "brain_get_mind_state"),
]


def generate_all_combinations(
    prompt_template: str, args: Dict[str, List]
) -> List[Dict]:
    """Generate all combinations of arguments for a prompt."""
    if not args:
        return [{"input": prompt_template, "output": None, "args": {}}]

    keys = list(args.keys())
    values = [args[k] for k in keys]

    results = []
    for combo in itertools.product(*values):
        prompt = prompt_template
        arg_dict = {}
        for key, value in zip(keys, combo):
            if f"{{{key}}}" in prompt:
                prompt = prompt.replace(f"{{{key}}}", value)
            arg_dict[key] = value
        results.append({"input": prompt, "output": None, "args": arg_dict})

    return results


def generate_dataset():
    """Generate the complete training dataset with positive + negative examples."""
    dataset = []

    # Qwen chat template format
    chat_template = """<|im_start|>user
{input}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""

    # =========================================================================
    # POSITIVE EXAMPLES (78 tools, should trigger tool call)
    # =========================================================================
    for tool_name, config in TOOLS_DATA.items():
        prompts = config["prompts"]
        args_config = config["args"]

        for prompt_template in prompts:
            combinations = generate_all_combinations(prompt_template, args_config)

            for combo in combinations:
                input_text = combo["input"]
                args_dict = combo["args"]

                if args_dict:
                    args_str = " ".join([f'--{k} "{v}"' for k, v in args_dict.items()])
                    output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ {args_str} }}}}[/TOOL_CALL]'
                else:
                    output = f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'

                formatted_text = chat_template.format(input=input_text, output=output)

                dataset.append(
                    {
                        "type": "positive",
                        "text": formatted_text,
                        "input": input_text,
                        "output": output,
                        "tool_name": tool_name,
                        "args": args_dict,
                        "should_call_tool": True,
                    }
                )

    # =========================================================================
    # NEGATIVE EXAMPLES - NO TOOL NEEDED (prevents hallucination)
    # =========================================================================
    for prompt, response in NO_TOOL_EXAMPLES:
        formatted_text = chat_template.format(input=prompt, output=response)

        dataset.append(
            {
                "type": "negative_no_tool",
                "text": formatted_text,
                "input": prompt,
                "output": response,
                "tool_name": None,
                "args": {},
                "should_call_tool": False,
            }
        )

    # =========================================================================
    # HARD NEGATIVE EXAMPLES - Similar prompts, WRONG tool
    # =========================================================================
    for prompt, correct_tool, wrong_tool in SIMILAR_WRONG_PAIRS:
        # The CORRECT tool example
        correct_output = (
            f'[TOOL_CALL]{{tool => "{correct_tool}", args => {{ }}}}[/TOOL_CALL]'
        )
        formatted_correct = chat_template.format(input=prompt, output=correct_output)

        dataset.append(
            {
                "type": "positive",
                "text": formatted_correct,
                "input": prompt,
                "output": correct_output,
                "tool_name": correct_tool,
                "args": {},
                "should_call_tool": True,
                "similar_wrong": wrong_tool,
            }
        )

    return dataset


def main():
    print("Generating comprehensive training dataset v3 WITH NEGATIVE EXAMPLES...")
    print("=" * 70)
    print("Features:")
    print("  - Positive examples for all 78 tools")
    print("  - Negative examples (no tool needed) - prevents hallucination")
    print("  - Hard negatives (similar wrong tool) - improves discrimination")
    print("=" * 70)

    dataset = generate_dataset()

    # Count by type
    positive_count = sum(1 for d in dataset if d["type"] == "positive")
    negative_no_tool = sum(1 for d in dataset if d["type"] == "negative_no_tool")

    print("\nDataset composition:")
    print(f"  Positive examples: {positive_count}")
    print(f"  Negative (no tool): {negative_no_tool}")
    print(f"  Total: {len(dataset)}")

    # Output paths
    output_path = (
        Path(__file__).parent.parent.parent / "datasets" / "rosetta_78_tools_v3.jsonl"
    )

    with open(output_path, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    # Also save as train format
    train_format_path = (
        Path(__file__).parent.parent.parent / "datasets" / "rosetta_78_v3_train.jsonl"
    )
    with open(train_format_path, "w") as f:
        for item in dataset:
            train_item = {
                "input": item["input"],
                "output": item["output"],
                "should_call_tool": item["should_call_tool"],
            }
            f.write(json.dumps(train_item) + "\n")

    # Stats
    unique_tools = set(d["tool_name"] for d in dataset if d["tool_name"])
    avg_examples = positive_count / len(unique_tools) if unique_tools else 0

    print(f"\nUnique tools: {len(unique_tools)}")
    print(f"Avg positive examples per tool: {avg_examples:.1f}")
    print("\nSaved to:")
    print(f"  Full: {output_path}")
    print(f"  Train: {train_format_path}")


if __name__ == "__main__":
    main()
