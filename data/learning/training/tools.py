"""
Tool definitions for Rosetta semantic routing.
Contains 25 tools with names and descriptions.
"""

TOOLS = [
    {
        "name": "memory_search",
        "description": "Search through saved memories or notes using keywords or semantic queries."
    },
    {
        "name": "memory_write",
        "description": "Save new information to memory or create new notes and entries."
    },
    {
        "name": "safe_delete",
        "description": "Permanently remove files or directories from the filesystem."
    },
    {
        "name": "session_end",
        "description": "End the current session and clean up associated resources."
    },
    {
        "name": "context_prune",
        "description": "Clear or reset the current context window to free up memory."
    },
    {
        "name": "project_clean",
        "description": "Clean up project files, remove build artifacts, or reset project state."
    },
    {
        "name": "empty_trash",
        "description": "Empty the trash or remove all files marked for deletion."
    },
    {
        "name": "file_read",
        "description": "Read the contents of a file from the filesystem."
    },
    {
        "name": "file_write",
        "description": "Write or create new files on the filesystem."
    },
    {
        "name": "file_edit",
        "description": "Modify existing file contents or update specific sections."
    },
    {
        "name": "directory_create",
        "description": "Create new directories or folders in the filesystem."
    },
    {
        "name": "directory_list",
        "description": "List contents of a directory or explore folder structure."
    },
    {
        "name": "git_clone",
        "description": "Clone a git repository from a remote URL."
    },
    {
        "name": "git_commit",
        "description": "Commit changes to a git repository with a message."
    },
    {
        "name": "git_push",
        "description": "Push local commits to a remote git repository."
    },
    {
        "name": "git_pull",
        "description": "Pull changes from a remote git repository."
    },
    {
        "name": "search_files",
        "description": "Search for files by name or content across the filesystem."
    },
    {
        "name": "run_command",
        "description": "Execute shell commands or run programs in the terminal."
    },
    {
        "name": "install_package",
        "description": "Install software packages or dependencies."
    },
    {
        "name": "web_fetch",
        "description": "Fetch content from URLs or retrieve web pages."
    },
    {
        "name": "code_run",
        "description": "Run code files or execute programming scripts."
    },
    {
        "name": "code_debug",
        "description": "Debug code, set breakpoints, or inspect variables."
    },
    {
        "name": "database_query",
        "description": "Execute database queries or retrieve data from databases."
    },
    {
        "name": "api_request",
        "description": "Make HTTP requests to external APIs or web services."
    },
    {
        "name": "image_process",
        "description": "Process or transform images using various operations."
    },
]


def get_tool_names() -> list:
    """Return list of all tool names."""
    return [t["name"] for t in TOOLS]


def get_tool_description(tool_name: str) -> str:
    """Get description for a specific tool."""
    for tool in TOOLS:
        if tool["name"] == tool_name:
            return tool["description"]
    return ""


def get_tool_text(tool_name: str) -> str:
    """Get combined name: description text for embedding."""
    desc = get_tool_description(tool_name)
    return f"{tool_name}: {desc}"


def get_all_tools_text() -> list:
    """Get list of all tool texts."""
    return [get_tool_text(t["name"]) for t in TOOLS]