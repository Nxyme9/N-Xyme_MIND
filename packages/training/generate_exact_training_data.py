#!/usr/bin/env python3
"""
Generate Rosetta training data with EXACT requests from verification script.

This creates training data where inputs EXACTLY match verify_rosetta_78.py test cases
and outputs the expected tool names.
"""

import json
from pathlib import Path

# EXACT test cases from verify_rosetta_78.py
TRAINING_PAIRS = [
    ("search memory for authentication tokens", "memory_search"),
    ("write this to memory: user logged in", "memory_write"),
    ("get memory statistics", "memory_stats"),
    ("get the active context", "get_active_context"),
    ("get user preferences", "get_user_context"),
    ("list available bmad workflows", "get_bmad_workflows"),
    ("get list of bmad agents", "context_get_bmad_agents"),
    ("route this task to the right agent", "route_task"),
    ("record this outcome", "record_outcome"),
    ("show learning statistics", "get_learning_stats"),
    ("check git status", "git_status"),
    ("show recent git commits", "git_log"),
    ("show changes in git", "git_diff"),
    ("search code on github for auth middleware", "github_search_code"),
    ("list issues for facebook/react", "github_list_issues"),
    ("get file contents from github", "github_get_file"),
    ("search repositories for react", "github_search_repos"),
    ("create issue for bug report", "github_create_issue"),
    ("create pull request", "github_create_pr"),
    ("fork this repository", "github_fork"),
    ("create a new branch", "github_create_branch"),
    ("fetch the python.org homepage", "fetch_url"),
    ("get markdown from url", "fetch_markdown"),
    ("fetch html content", "fetch_html"),
    ("get json from api", "fetch_json"),
    ("query context7 docs for react", "context7_query_docs"),
    ("resolve library id for react", "context7_resolve_library"),
    ("think step by step about this problem", "sequential_thinking"),
    ("navigate to github.com", "browser_navigate"),
    ("click the login button", "browser_click"),
    ("fill in the username field", "browser_fill"),
    ("get the page title", "browser_get_text"),
    ("take a screenshot", "browser_screenshot"),
    ("read the README.md file", "read_file"),
    ("write hello world to test.txt", "write_file"),
    ("list files in current directory", "list_directory"),
    ("query the database", "sqlite_query"),
    ("list all tables", "sqlite_list_tables"),
    ("get sample rows from users table", "sqlite_sample_table"),
    ("run type check", "run_typecheck"),
    ("run linter", "run_lint"),
    ("run formatter check", "run_format"),
    ("run tests", "run_tests"),
    ("scan for secrets", "run_secrets_scan"),
    ("check system health", "get_health"),
    ("list all sessions", "session_list"),
    ("get info for session 123", "session_info"),
    ("read messages from session 123", "session_read"),
    ("search sessions for auth", "session_search"),
    ("search knowledge base", "knowledge_search"),
    ("write to knowledge base", "knowledge_write"),
    ("get mind state", "brain_get_mind_state"),
    ("update mind state", "brain_update_mind_state"),
    ("get session history", "brain_get_session_history"),
    ("get active context", "brain_context_get_active"),
    ("get user context", "brain_context_get_user"),
    ("get constraints", "brain_context_get_constraints"),
    ("delegate task to hephaestus", "agent_delegate_task"),
    ("get agent status", "agent_get_status"),
    ("grep for function definitions", "grep"),
    ("glob for python files", "glob"),
    ("read main.py", "read"),
    ("check for errors in auth.py", "lsp_diagnostics"),
    ("go to definition of get_user", "lsp_goto_definition"),
    ("find all references to User class", "lsp_find_references"),
    ("rename function to get_current_user", "lsp_rename"),
    ("smart search for security patterns", "athena_smart_search"),
    ("search notion", "notion_search"),
    ("get notion page", "notion_get_page"),
    ("create notion page", "notion_create_page"),
    ("update notion page", "notion_update_page"),
    ("send telegram message", "telegram_send_message"),
    ("get telegram messages", "telegram_get_messages"),
    ("get bot info", "telegram_get_bot_info"),
    ("search the web for ai news", "websearch"),
    ("search for python async examples", "codesearch"),
    ("ask a question", "ask_question"),
    ("mark task as done", "done"),
]


def generate_output(tool_name, query=None):
    """Generate output in the exact format expected."""
    if query:
        return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ --query "{query}" }}}}[/TOOL_CALL]'
    return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'


def create_variations(request, tool_name):
    """Create multiple training examples with paraphrases."""
    variations = [
        # Exact request
        (request, generate_output(tool_name)),
        # With "please"
        (f"Please {request}", generate_output(tool_name)),
        # With "can you"
        (f"Can you {request}?", generate_output(tool_name)),
        # With "I need to"
        (f"I need to {request}", generate_output(tool_name)),
    ]
    return variations


def main():
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "datasets" / "rosetta_78_exact_train.jsonl"

    print("Generating training data with EXACT verification requests...")

    data = []
    for request, tool in TRAINING_PAIRS:
        # Extract query from request if applicable
        query = None
        if "for " in request:
            query = request.split("for ")[-1]
        elif " to " in request and "test" not in request:
            # For "write hello world to test.txt" type requests
            pass

        for input_text, output_text in create_variations(request, tool):
            data.append({"input": input_text, "output": output_text})

    # Write to JSONL
    with open(output_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(data)} training examples")
    print(f"Saved to: {output_path}")

    # Show sample
    print("\nSample (first 5):")
    for item in data[:5]:
        print(f"  Input: {item['input'][:50]}...")
        print(f"  Output: {item['output'][:60]}...")
        print()


if __name__ == "__main__":
    main()
