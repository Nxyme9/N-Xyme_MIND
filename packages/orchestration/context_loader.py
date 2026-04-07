"""Context Loader — Hierarchical context loading for agent loop.

Based on Claude Code's CLAUDE.md pattern:
- Hierarchical loading: current dir → parent dirs → path-scoped rules → skills → auto memory → MCP tool names
- Thread-safe with TTL caching
- LoadedContext dataclass with all context components

Usage:
    loader = ContextLoader()
    context = loader.load_context(working_dir="/path/to/project")
    # context.system_rules, context.project_context, context.skills, etc.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_MAX_DEPTH = 10  # Max parent directory traversal

# Well-known context files (in order of precedence)
CONTEXT_FILES = [
    "CLAUDE.md",  # Claude Code standard
    "AGENTS.md",  # Workspace rules
    ".claude.md",  # Alternative naming
    ".agents.md",  # Alternative naming
]


@dataclass
class LoadedContext:
    """Container for loaded context components.

    Attributes:
        system_rules: Global system rules from root or default
        project_context: Project-specific context from current directory
        path_scoped_rules: Rules from current and parent directories
        skills: Auto-detected skills relevant to the context
        memory_context: Relevant memory from auto-memory system
        tool_names: Available MCP tool names for this context
        working_dir: The directory this context was loaded for
        loaded_files: List of files that were loaded to build this context
    """

    system_rules: str = ""
    project_context: str = ""
    path_scoped_rules: Dict[str, str] = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)
    memory_context: str = ""
    tool_names: List[str] = field(default_factory=list)
    working_dir: str = ""
    loaded_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "system_rules": self.system_rules,
            "project_context": self.project_context,
            "path_scoped_rules": self.path_scoped_rules,
            "skills": self.skills,
            "memory_context": self.memory_context,
            "tool_names": self.tool_names,
            "working_dir": self.working_dir,
            "loaded_files": self.loaded_files,
        }

    def is_empty(self) -> bool:
        """Check if context has any meaningful content."""
        return (
            not self.system_rules
            and not self.project_context
            and not self.path_scoped_rules
            and not self.memory_context
        )


class ContextLoader:
    """Hierarchical context loader with TTL caching.

    Loads context from multiple sources in order of precedence:
        1. Current working directory (CLAUDE.md, AGENTS.md)
        2. Parent directories (traversed up to MAX_DEPTH)
        3. Path-scoped rules (collected from all levels)
        4. Skills (auto-detected from context)
        5. Auto memory (from memory system)
        6. MCP tool names (from MCP servers)

    Thread-safe with caching (default 5-minute TTL).

    Usage:
        loader = ContextLoader()
        context = loader.load_context(working_dir="/path/to/project")
        print(context.system_rules, context.project_context)
    """

    def __init__(
        self,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ):
        """Initialize context loader.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
            max_depth: Maximum parent directory traversal depth (default: 10)
        """
        self._cache_ttl = cache_ttl
        self._max_depth = max_depth
        self._lock = threading.Lock()
        self._cache: Dict[str, tuple[float, LoadedContext]] = {}

        # Optional imports - graceful fallback if unavailable
        self._memory_available = False
        self._mcp_tools_available = False

        self._init_optional_modules()

    def _init_optional_modules(self) -> None:
        """Initialize optional modules with graceful fallback."""
        # Memory system
        try:
            from packages.memory_core.router import get_default_router

            self._memory_available = True
            self._memory_router = get_default_router
            logger.debug("Memory system available")
        except ImportError as e:
            logger.debug(f"Memory system not available: {e}")

        # MCP tools
        try:
            from packages.orchestration.mcp_server import MCPServer

            self._mcp_available = True
            logger.debug("MCP server available")
        except ImportError as e:
            logger.debug(f"MCP server not available: {e}")

    def load_context(self, working_dir: str) -> LoadedContext:
        """Load hierarchical context for the given working directory.

        Args:
            working_dir: Directory to load context for

        Returns:
            LoadedContext with all context components
        """
        # Normalize path for cache key
        cache_key = str(Path(working_dir).resolve())

        # Check cache first (thread-safe)
        with self._lock:
            if cache_key in self._cache:
                timestamp, cached = self._cache[cache_key]
                elapsed = time.time() - timestamp
                if elapsed < self._cache_ttl:
                    logger.debug(
                        f"Returning cached context for {cache_key} (age: {elapsed:.1f}s)"
                    )
                    return cached

        # Cache miss or expired - build context
        logger.info(f"Building context for working directory: {working_dir}")
        context = self._build_context(working_dir)

        # Update cache (thread-safe)
        with self._lock:
            self._cache[cache_key] = (time.time(), context)

        return context

    def _build_context(self, working_dir: str) -> LoadedContext:
        """Build hierarchical context from multiple sources.

        Args:
            working_dir: Directory to load context for

        Returns:
            LoadedContext with all context components
        """
        context = LoadedContext(working_dir=working_dir)
        loaded_files: List[str] = []

        # 1. Path-scoped rules (current and parent directories)
        path_rules = self._load_path_scoped_rules(working_dir)
        context.path_scoped_rules = path_rules
        loaded_files.extend(path_rules.keys())

        # 2. System rules (from root or default)
        context.system_rules = self._load_system_rules(path_rules)

        # 3. Project context (from current directory)
        context.project_context = self._load_project_context(working_dir)

        # 4. Skills (auto-detected from context)
        context.skills = self._detect_skills(path_rules, context.project_context)

        # 5. Auto memory (from memory system)
        context.memory_context = self._load_memory_context(working_dir)

        # 6. MCP tool names
        context.tool_names = self._get_mcp_tool_names()

        context.loaded_files = loaded_files
        return context

    def _load_path_scoped_rules(self, working_dir: str) -> Dict[str, str]:
        """Load rules from current and parent directories.

        Traverses from current directory up to max_depth, collecting
        CLAUDE.md and AGENTS.md files at each level.

        Args:
            working_dir: Starting directory

        Returns:
            Dict mapping file path to content
        """
        rules: Dict[str, str] = {}
        current = Path(working_dir).resolve()

        if not current.exists():
            logger.warning(f"Working directory does not exist: {working_dir}")
            return rules

        # Traverse up the directory tree
        for _ in range(self._max_depth):
            for context_file in CONTEXT_FILES:
                file_path = current / context_file
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8").strip()
                        if content:
                            rules[str(file_path)] = content
                            logger.debug(f"Loaded context file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")

            # Move to parent directory
            parent = current.parent
            if parent == current:
                # Reached filesystem root
                break
            current = parent

        return rules

    def _load_system_rules(self, path_rules: Dict[str, str]) -> str:
        """Load system rules from path rules or generate default.

        Args:
            path_rules: Path-scoped rules dict

        Returns:
            System rules string
        """
        # Find AGENTS.md at highest level (usually root)
        root_agents = None
        root_path = None

        for path, content in path_rules.items():
            if "AGENTS.md" in path:
                # Track the highest-level AGENTS.md
                path_obj = Path(path)
                if root_path is None or path_obj.is_relative_to(root_path):
                    root_path = path_obj.parent
                    root_agents = content

        if root_agents:
            return root_agents

        # Default system rules
        return self._default_system_rules()

    def _default_system_rules(self) -> str:
        """Generate default system rules when no AGENTS.md found.

        Returns:
            Default system rules string
        """
        return """# Default System Rules

## Agent Behavior
- Always verify before committing
- Never use `as any`, `@ts-ignore`, or suppress errors
- Prefer existing patterns over new approaches
- Delegate implementation to specialized agents

## Code Quality
- Run quality gates before completion
- Type safety is mandatory
- Error handling must be specific (no bare except)
- Tests required for new features

## Context
- Use hierarchical context loading (CLAUDE.md pattern)
- Cache context with TTL
- Thread-safe operations
"""

    def _load_project_context(self, working_dir: str) -> str:
        """Load project-specific context from current directory.

        Args:
            working_dir: Working directory

        Returns:
            Project context string
        """
        # Look for project config files
        project_files = [
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "requirements.txt",
            "setup.py",
        ]

        context_parts: List[str] = []
        dir_path = Path(working_dir)

        for project_file in project_files:
            file_path = dir_path / project_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8").strip()
                    if content:
                        # Extract relevant info
                        if project_file == "pyproject.toml":
                            context_parts.append(self._parse_pyproject(content))
                        elif project_file == "package.json":
                            context_parts.append(self._parse_package_json(content))
                        else:
                            context_parts.append(
                                f"# {project_file}\n```\n{content[:500]}\n```"
                            )
                except Exception as e:
                    logger.debug(f"Failed to read {project_file}: {e}")

        return "\n\n".join(context_parts) if context_parts else ""

    def _parse_pyproject(self, content: str) -> str:
        """Extract relevant info from pyproject.toml.

        Args:
            content: Raw pyproject.toml content

        Returns:
            Parsed context string
        """
        # Simple extraction - get project name and dependencies
        lines = content.split("\n")
        project_name = "Unknown"
        dependencies = []

        in_dependencies = False
        for line in lines:
            if "[project]" in line or "[tool.pytest]" in line:
                in_dependencies = False
            if line.startswith("name ="):
                project_name = line.split("=")[1].strip().strip('"')
            if "dependencies" in line.lower():
                in_dependencies = True
            elif in_dependencies and line.strip().startswith("["):
                in_dependencies = False

        return f"# Python Project: {project_name}"

    def _parse_package_json(self, content: str) -> str:
        """Extract relevant info from package.json.

        Args:
            content: Raw package.json content

        Returns:
            Parsed context string
        """
        try:
            data = json.loads(content)
            name = data.get("name", "Unknown")
            version = data.get("version", "unknown")
            return f"# NPM Project: {name}@{version}"
        except json.JSONDecodeError:
            return "# NPM Project (parse failed)"

    def _detect_skills(
        self, path_rules: Dict[str, str], project_context: str
    ) -> List[str]:
        """Auto-detect skills from context.

        Args:
            path_rules: Path-scoped rules
            project_context: Project context

        Returns:
            List of detected skill names
        """
        skills: List[str] = []

        # Combine all text for detection
        all_text = " ".join(path_rules.values()) + " " + project_context

        # Keyword-based skill detection
        skill_keywords = {
            "git": ["git", "commit", "branch", "rebase", "merge"],
            "frontend-ui-ux": ["ui", "css", "layout", "design", "react", "vue", "html"],
            "playwright": ["browser", "test", "automation", "scrape", "click"],
            "dev-browser": ["navigate", "form", "login", "screenshot"],
            "review-work": ["review", "verify", "test", "QA", "validate"],
        }

        for skill, keywords in skill_keywords.items():
            if any(kw.lower() in all_text.lower() for kw in keywords):
                skills.append(skill)

        return skills

    def _load_memory_context(self, working_dir: str) -> str:
        """Load relevant memory from auto-memory system.

        Args:
            working_dir: Working directory

        Returns:
            Memory context string
        """
        if not self._memory_available:
            return ""

        try:
            # Try to get relevant memory for this working directory
            router = self._memory_router()
            # Query for recent context
            results = router.search(f"working_dir:{working_dir}", top_k=5)
            if results:
                return "\n".join([r.content for r in results])
        except Exception as e:
            logger.debug(f"Failed to load memory context: {e}")

        return ""

    def _get_mcp_tool_names(self) -> List[str]:
        """Get available MCP tool names.

        Returns:
            List of MCP tool names
        """
        if not hasattr(self, "_mcp_available") or not self._mcp_available:
            return self._default_tool_names()

        try:
            # Try to get tool names from MCP server
            # This would require MCP server to expose tool listing
            return self._default_tool_names()
        except Exception as e:
            logger.debug(f"Failed to get MCP tools: {e}")

        return self._default_tool_names()

    def _default_tool_names(self) -> List[str]:
        """Get default MCP tool names.

        Returns:
            List of default tool names
        """
        return [
            "filesystem",
            "git",
            "github",
            "context7",
            "fetch",
            "sequential-thinking",
            "memory",
            "athena",
            "athena-context",
            "trigger-guardian",
            "nx-mind",
            "unified-memory",
        ]

    def clear_cache(self, working_dir: Optional[str] = None) -> None:
        """Clear cached context.

        Args:
            working_dir: Specific directory to clear, or None for all
        """
        with self._lock:
            if working_dir:
                cache_key = str(Path(working_dir).resolve())
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.info(f"Cleared cache for {cache_key}")
            else:
                self._cache.clear()
                logger.info("Cleared all context cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats
        """
        with self._lock:
            return {
                "entries": len(self._cache),
                "ttl_seconds": self._cache_ttl,
                "max_depth": self._max_depth,
            }


# Default instance for convenience
_default_loader: Optional[ContextLoader] = None


def get_default_loader() -> ContextLoader:
    """Get or create default ContextLoader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = ContextLoader()
    return _default_loader


__all__ = [
    "ContextLoader",
    "LoadedContext",
    "get_default_loader",
]
