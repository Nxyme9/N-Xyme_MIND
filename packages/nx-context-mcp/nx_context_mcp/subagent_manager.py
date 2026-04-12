"""
Subagent Manager for N-Xyme_MIND
================================
Implements subagent context isolation based on leaked Anthropic source code patterns.

Provides complete isolation for spawned subagents with:
- Own MCP server initialization
- Own message history slice
- Own tool resolution
- Proper cleanup lifecycle

Reference: tools/AgentTool/runAgent.ts from Anthropic source
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Definition Types
# =============================================================================


class AgentSource(str, Enum):
    """Source of agent definition."""

    BUILTIN = "builtin"
    PLUGIN = "plugin"
    CUSTOM = "custom"


class AgentType(str, Enum):
    """Type of agent."""

    EXPLORE = "Explore"
    PLAN = "Plan"
    GENERAL = "General"
    VERIFICATION = "Verification"


class IsolationMode(str, Enum):
    """Isolation mode for subagent."""

    NONE = "none"  # Share parent context
    SHARED_TOOLS = "shared_tools"  # Share tools but not state
    FULL = "full"  # Complete isolation


class PermissionMode(str, Enum):
    """Permission mode for agent."""

    BYPASS = "bypassPermissions"
    ACCEPT_EDITS = "acceptEdits"
    AUTO = "auto"
    BUBBLE = "bubble"
    READ_ONLY = "readOnly"


@dataclass
class AgentFrontmatterSchema:
    """Frontmatter schema support for agent definition."""

    # Tools configuration
    tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)

    # Model and prompt
    prompt: str = ""
    model: str = ""
    effort: Optional[int] = None

    # Permission
    permission_mode: Optional[PermissionMode] = None

    # MCP servers (additive to parent's)
    mcp_servers: list[str] = field(default_factory=list)

    # Hooks
    hooks: list[dict[str, Any]] = field(default_factory=list)

    # Limits
    max_turns: int = 50

    # Skills to preload
    skills: list[str] = field(default_factory=list)

    # Memory configuration
    memory: dict[str, Any] = field(default_factory=dict)

    # Isolation mode
    isolation_mode: IsolationMode = IsolationMode.FULL

    # Additional options
    omit_claude_md: bool = False
    critical_system_reminder: bool = False


@dataclass
class BuiltInAgentDefinition:
    """Built-in agent definition."""

    agent_type: AgentType
    name: str
    description: str
    source: AgentSource = AgentSource.BUILTIN
    frontmatter: AgentFrontmatterSchema = field(default_factory=AgentFrontmatterSchema)

    # Built-in agents have these defaults
    def __post_init__(self):
        if self.frontmatter.tools:
            return
        # Set default tools based on agent type
        if self.agent_type == AgentType.EXPLORE:
            self.frontmatter.tools = ["read", "grep", "glob", "glob_app"]
            self.frontmatter.disallowed_tools = ["edit", "write", "bash"]
            self.frontmatter.permission_mode = PermissionMode.READ_ONLY
        elif self.agent_type == AgentType.PLAN:
            self.frontmatter.tools = ["read", "grep", "glob"]
            self.frontmatter.max_turns = 10
        elif self.agent_type == AgentType.VERIFICATION:
            self.frontmatter.tools = ["read", "lsp_diagnostics", "bash"]


@dataclass
class CustomAgentDefinition:
    """Custom agent definition loaded from files."""

    agent_type: str
    name: str
    description: str
    source: AgentSource = AgentSource.CUSTOM
    frontmatter: AgentFrontmatterSchema = field(default_factory=AgentFrontmatterSchema)
    file_path: Optional[Path] = None


@dataclass
class PluginAgentDefinition:
    """Plugin agent definition from plugins."""

    agent_type: str
    name: str
    description: str
    source: AgentSource = AgentSource.PLUGIN
    frontmatter: AgentFrontmatterSchema = field(default_factory=AgentFrontmatterSchema)
    plugin_name: str = ""


# Union type for any agent definition
AgentDefinition = BuiltInAgentDefinition | CustomAgentDefinition | PluginAgentDefinition


# =============================================================================
# Subagent Context - Complete Isolation
# =============================================================================


@dataclass
class SubagentContext:
    """
    Subagent context with complete isolation from parent.

    Provides:
    - Own message history slice
    - Own MCP server initialization
    - Own tool resolution
    - Isolated state management
    """

    # Unique identifier for this subagent
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Agent type and name
    agent_type: str = ""
    agent_name: str = ""

    # Message history (isolated from parent)
    messages: list[dict[str, Any]] = field(default_factory=list)

    # Parent context reference (for fallback, not for direct access)
    parent_agent_id: Optional[str] = None

    # MCP servers (own initialization)
    mcp_servers: list[str] = field(default_factory=list)
    mcp_clients: list[Any] = field(default_factory=list)
    mcp_tools: list[dict[str, Any]] = field(default_factory=list)

    # Tool resolution
    available_tools: list[dict[str, Any]] = field(default_factory=list)
    resolved_tools: list[dict[str, Any]] = field(default_factory=list)

    # State management
    state: dict[str, Any] = field(default_factory=dict)

    # File state cache (cloned from parent or fresh)
    read_file_state: dict[str, Any] = field(default_factory=dict)

    # Permission mode
    permission_mode: PermissionMode = PermissionMode.AUTO

    # Isolation mode
    isolation_mode: IsolationMode = IsolationMode.FULL

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    # Cleanup callbacks
    cleanup_callbacks: list[Callable[[], Any]] = field(default_factory=list)

    # Session hooks
    session_hooks: list[dict[str, Any]] = field(default_factory=list)

    # Skills to preload
    skills: list[str] = field(default_factory=list)

    # Model configuration
    model: str = ""
    effort: Optional[int] = None

    # Max turns
    max_turns: int = 50

    # Additional context
    system_context: dict[str, Any] = field(default_factory=dict)
    user_context: dict[str, Any] = field(default_factory=dict)

    def is_fully_isolated(self) -> bool:
        """Check if this context is fully isolated."""
        return self.isolation_mode == IsolationMode.FULL

    def is_read_only(self) -> bool:
        """Check if this is a read-only agent."""
        return self.permission_mode == PermissionMode.READ_ONLY

    def add_cleanup_callback(self, callback: Callable[[], Any]) -> None:
        """Add a cleanup callback to be called on context destruction."""
        self.cleanup_callbacks.append(callback)

    async def cleanup(self) -> None:
        """Clean up all resources held by this context."""
        logger.info(f"Cleaning up subagent context: {self.agent_id}")

        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.warning(f"Cleanup callback error: {e}")

        # Clean up MCP clients
        for client in self.mcp_clients:
            try:
                if hasattr(client, "cleanup"):
                    if asyncio.iscoroutinefunction(client.cleanup):
                        await client.cleanup()
                    else:
                        client.cleanup()
            except Exception as e:
                logger.warning(f"MCP client cleanup error: {e}")

        # Clear all state
        self.messages.clear()
        self.mcp_clients.clear()
        self.mcp_tools.clear()
        self.available_tools.clear()
        self.resolved_tools.clear()
        self.state.clear()
        self.read_file_state.clear()
        self.cleanup_callbacks.clear()
        self.session_hooks.clear()

        logger.info(f"Subagent context cleaned: {self.agent_id}")


# =============================================================================
# Agent Loader - Load agent definitions
# =============================================================================


class AgentLoader:
    """
    Loads agent definitions from various sources.
    Supports built-in, custom, and plugin agents.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._loaded_agents: dict[str, AgentDefinition] = {}

    def get_builtin_agent(self, agent_type: AgentType) -> BuiltInAgentDefinition:
        """Get a built-in agent definition."""
        if agent_type in self._loaded_agents:
            return self._loaded_agents[agent_type.value]  # type: ignore

        # Create built-in agent based on type
        if agent_type == AgentType.EXPLORE:
            agent = BuiltInAgentDefinition(
                agent_type=AgentType.EXPLORE,
                name="Explore",
                description="Read-only agent for searching and exploring codebase",
                frontmatter=AgentFrontmatterSchema(
                    tools=["read", "grep", "glob", "glob_app"],
                    disallowed_tools=["edit", "write", "bash"],
                    permission_mode=PermissionMode.READ_ONLY,
                    max_turns=30,
                    omit_claude_md=True,
                ),
            )
        elif agent_type == AgentType.PLAN:
            agent = BuiltInAgentDefinition(
                agent_type=AgentType.PLAN,
                name="Plan",
                description="Planning agent for creating detailed work plans",
                frontmatter=AgentFrontmatterSchema(
                    tools=["read", "grep", "glob"],
                    max_turns=10,
                    omit_claude_md=True,
                ),
            )
        elif agent_type == AgentType.GENERAL:
            agent = BuiltInAgentDefinition(
                agent_type=AgentType.GENERAL,
                name="General Purpose",
                description="General purpose agent for various tasks",
                frontmatter=AgentFrontmatterSchema(
                    max_turns=50,
                ),
            )
        elif agent_type == AgentType.VERIFICATION:
            agent = BuiltInAgentDefinition(
                agent_type=AgentType.VERIFICATION,
                name="Verification",
                description="Verification agent for quality assurance",
                frontmatter=AgentFrontmatterSchema(
                    tools=["read", "lsp_diagnostics", "bash"],
                    max_turns=20,
                ),
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        self._loaded_agents[agent_type.value] = agent
        return agent

    def load_agent_from_file(self, file_path: Path) -> Optional[CustomAgentDefinition]:
        """Load custom agent from file (YAML, JSON, or MD with frontmatter)."""
        try:
            content = file_path.read_text()

            # Parse frontmatter if present
            frontmatter = AgentFrontmatterSchema()
            body = ""

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1].strip()
                    body = parts[2].strip()

                    # Parse YAML frontmatter
                    import yaml

                    fm_data = yaml.safe_load(fm_text) or {}

                    frontmatter = AgentFrontmatterSchema(
                        tools=fm_data.get("tools", []),
                        disallowed_tools=fm_data.get("disallowed_tools", []),
                        prompt=fm_data.get("prompt", ""),
                        model=fm_data.get("model", ""),
                        effort=fm_data.get("effort"),
                        permission_mode=PermissionMode(fm_data["permission_mode"])
                        if fm_data.get("permission_mode")
                        else None,
                        mcp_servers=fm_data.get("mcp_servers", []),
                        hooks=fm_data.get("hooks", []),
                        max_turns=fm_data.get("max_turns", 50),
                        skills=fm_data.get("skills", []),
                        memory=fm_data.get("memory", {}),
                        isolation_mode=IsolationMode(
                            fm_data.get("isolation_mode", "full")
                        ),
                    )

            # Extract name from filename
            name = file_path.stem

            # Extract description from body first line
            description = body.split("\n")[0] if body else f"Custom agent: {name}"

            agent = CustomAgentDefinition(
                agent_type=name,
                name=name,
                description=description,
                source=AgentSource.CUSTOM,
                frontmatter=frontmatter,
                file_path=file_path,
            )

            self._loaded_agents[name] = agent
            return agent

        except Exception as e:
            logger.warning(f"Failed to load agent from {file_path}: {e}")
            return None

    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """Get agent by name (checks built-in first, then custom)."""
        if name in self._loaded_agents:
            return self._loaded_agents[name]

        # Check if it's a built-in
        try:
            agent_type = AgentType(name)
            return self.get_builtin_agent(agent_type)
        except ValueError:
            pass

        # Check for custom agents in agents directory
        agents_dir = self.project_root / "agents"
        if agents_dir.exists():
            for ext in [".md", ".yaml", ".yml", ".json"]:
                agent_file = agents_dir / f"{name}{ext}"
                if agent_file.exists():
                    return self.load_agent_from_file(agent_file)

        return None


# =============================================================================
# MCP Server Manager
# =============================================================================


class MCPServerManager:
    """
    Manages MCP server connections for subagents.
    Handles initialization and cleanup of MCP servers.
    """

    def __init__(self):
        self._connections: dict[str, Any] = {}
        self._cleanup_funcs: dict[str, Callable[[], Any]] = {}

    async def connect_servers(
        self,
        server_configs: list[str],
        parent_clients: list[Any] = None,
    ) -> tuple[list[Any], list[dict[str, Any]], Callable[[], Any]]:
        """
        Connect to MCP servers for an agent.

        Returns:
            - clients: Merged list (parent + agent-specific)
            - tools: Agent MCP tools
            - cleanup: Cleanup function
        """
        agent_clients = []
        newly_created = []
        agent_tools = []

        for spec in server_configs:
            client = None
            name = ""
            is_newly_created = False

            if isinstance(spec, str):
                # Reference by name - look up existing config
                name = spec
                # In a real implementation, this would look up config and connect
                # For now, we'll track the reference
                logger.debug(f"MCP server reference: {spec}")
            else:
                # Inline definition { name: config }
                entries = list(spec.items()) if isinstance(spec, dict) else []
                if entries:
                    name, config = entries[0]
                    is_newly_created = True
                    logger.debug(f"MCP server inline: {name}")

            if client and is_newly_created:
                agent_clients.append(client)
                newly_created.append(client)

                # Fetch tools if connected
                if hasattr(client, "tools"):
                    agent_tools.extend(client.tools)

        # Merge parent and agent clients
        all_clients = []
        if parent_clients:
            all_clients.extend(parent_clients)
        all_clients.extend(agent_clients)

        # Create cleanup function
        cleanup = self._create_cleanup_func(newly_created)

        return all_clients, agent_tools, cleanup

    def _create_cleanup_func(self, clients: list[Any]) -> Callable[[], Any]:
        """Create cleanup function for agent-specific clients."""

        def cleanup():
            for client in clients:
                try:
                    if hasattr(client, "cleanup"):
                        client.cleanup()
                except Exception as e:
                    logger.warning(f"MCP cleanup error: {e}")

        return cleanup

    async def cleanup_all(self) -> None:
        """Clean up all MCP connections."""
        for name, cleanup in self._cleanup_funcs.items():
            try:
                cleanup()
            except Exception as e:
                logger.warning(f"MCP connection cleanup error for {name}: {e}")

        self._connections.clear()
        self._cleanup_funcs.clear()


# =============================================================================
# Tool Resolver
# =============================================================================


class ToolResolver:
    """
    Resolves tools for an agent based on agent definition and available tools.
    """

    @staticmethod
    def resolve_tools(
        agent_definition: AgentDefinition,
        available_tools: list[dict[str, Any]],
        disallowed_tools: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Resolve tools for an agent based on frontmatter configuration.

        Filters available tools based on:
        - tools (whitelist): Only these tools
        - disallowed_tools (blacklist): Exclude these tools
        """
        if isinstance(agent_definition, BuiltInAgentDefinition):
            frontmatter = agent_definition.frontmatter
        elif isinstance(agent_definition, CustomAgentDefinition):
            frontmatter = agent_definition.frontmatter
        elif isinstance(agent_definition, PluginAgentDefinition):
            frontmatter = agent_definition.frontmatter
        else:
            return available_tools

        resolved = available_tools

        # Apply whitelist if specified
        if frontmatter.tools:
            tool_names = set(frontmatter.tools)
            resolved = [t for t in resolved if t.get("name") in tool_names]

        # Apply blacklist
        blacklist = set(frontmatter.disallowed_tools or [])
        if disallowed_tools:
            blacklist.update(disallowed_tools)

        if blacklist:
            resolved = [t for t in resolved if t.get("name") not in blacklist]

        return resolved

    @staticmethod
    def get_agent_tools(agent_type: AgentType) -> list[str]:
        """Get default tools for a built-in agent type."""
        if agent_type == AgentType.EXPLORE:
            return ["read", "grep", "glob", "glob_app"]
        elif agent_type == AgentType.PLAN:
            return ["read", "grep", "glob"]
        elif agent_type == AgentType.GENERAL:
            return ["read", "grep", "glob", "edit", "write", "bash"]
        elif agent_type == AgentType.VERIFICATION:
            return ["read", "lsp_diagnostics", "bash", "quality_gates_run_all_gates"]
        return []


# =============================================================================
# Built-in Agents Registry
# =============================================================================


class BuiltInAgents:
    """Registry of built-in agents."""

    AGENTS: dict[AgentType, BuiltInAgentDefinition] = {}

    @classmethod
    def register(cls, agent: BuiltInAgentDefinition) -> None:
        """Register a built-in agent."""
        cls.AGENTS[agent.agent_type] = agent

    @classmethod
    def get(cls, agent_type: AgentType) -> Optional[BuiltInAgentDefinition]:
        """Get a built-in agent."""
        return cls.AGENTS.get(agent_type)

    @classmethod
    def get_all(cls) -> list[BuiltInAgentDefinition]:
        """Get all built-in agents."""
        return list(cls.AGENTS.values())

    @classmethod
    def initialize(cls, loader: AgentLoader) -> None:
        """Initialize built-in agents from loader."""
        for agent_type in AgentType:
            agent = loader.get_builtin_agent(agent_type)
            cls.register(agent)


# =============================================================================
# Agent Runner - Execute agent lifecycle
# =============================================================================


class AgentRunner:
    """
    Runs agent lifecycle: initialization, execution, cleanup.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.loader = AgentLoader(self.project_root)
        self.mcp_manager = MCPServerManager()
        self._active_contexts: dict[str, SubagentContext] = {}

        # Initialize built-in agents
        BuiltInAgents.initialize(self.loader)

    async def create_subagent_context(
        self,
        agent_definition: AgentDefinition,
        parent_context: Optional[SubagentContext] = None,
        fork_context_messages: list[dict[str, Any]] = None,
        parent_mcp_clients: list[Any] = None,
        parent_tools: list[dict[str, Any]] = None,
    ) -> SubagentContext:
        """
        Create a subagent context with complete isolation.

        This is the main entry point - creates a fully isolated context
        based on leaked Anthropic patterns.
        """
        # Get frontmatter
        if isinstance(agent_definition, BuiltInAgentDefinition):
            frontmatter = agent_definition.frontmatter
            agent_name = agent_definition.name
            agent_type_str = agent_definition.agent_type.value
        elif isinstance(agent_definition, CustomAgentDefinition):
            frontmatter = agent_definition.frontmatter
            agent_name = agent_definition.name
            agent_type_str = agent_definition.agent_type
        elif isinstance(agent_definition, PluginAgentDefinition):
            frontmatter = agent_definition.frontmatter
            agent_name = agent_definition.name
            agent_type_str = agent_definition.agent_type
        else:
            frontmatter = AgentFrontmatterSchema()
            agent_name = "Unknown"
            agent_type_str = "Unknown"

        # Determine isolation mode
        isolation_mode = frontmatter.isolation_mode

        # Create context
        context = SubagentContext(
            agent_type=agent_type_str,
            agent_name=agent_name,
            parent_agent_id=parent_context.agent_id if parent_context else None,
            isolation_mode=isolation_mode,
            permission_mode=frontmatter.permission_mode or PermissionMode.AUTO,
            max_turns=frontmatter.max_turns,
            model=frontmatter.model,
            effort=frontmatter.effort,
            skills=frontmatter.skills,
            mcp_servers=frontmatter.mcp_servers,
            session_hooks=frontmatter.hooks,
        )

        # Clone or create fresh file state
        if parent_context and fork_context_messages:
            context.read_file_state = parent_context.read_file_state.copy()
        else:
            context.read_file_state = {}

        # Initialize message history
        if fork_context_messages:
            context.messages = fork_context_messages.copy()
        else:
            context.messages = []

        # Connect MCP servers (additive to parent)
        if frontmatter.mcp_servers:
            clients, tools, mcp_cleanup = await self.mcp_manager.connect_servers(
                frontmatter.mcp_servers,
                parent_mcp_clients,
            )
            context.mcp_clients = clients
            context.mcp_tools = tools
            context.add_cleanup_callback(mcp_cleanup)
        else:
            # Inherit parent MCP clients
            if parent_mcp_clients:
                context.mcp_clients = parent_mcp_clients.copy()

        # Resolve tools
        all_available_tools = list(parent_tools or [])
        if context.mcp_tools:
            all_available_tools.extend(context.mcp_tools)

        context.available_tools = all_available_tools
        context.resolved_tools = ToolResolver.resolve_tools(
            agent_definition,
            all_available_tools,
        )

        # Track active context
        self._active_contexts[context.agent_id] = context

        logger.info(
            f"Created subagent context: {context.agent_id} "
            f"(type={agent_type_str}, isolation={isolation_mode.value})"
        )

        return context

    async def cleanup_context(self, context: SubagentContext) -> None:
        """Clean up a subagent context."""
        await context.cleanup()

        if context.agent_id in self._active_contexts:
            del self._active_contexts[context.agent_id]

        logger.info(f"Cleaned up subagent context: {context.agent_id}")

    def get_active_contexts(self) -> list[SubagentContext]:
        """Get all active subagent contexts."""
        return list(self._active_contexts.values())

    async def cleanup_all(self) -> None:
        """Clean up all active contexts."""
        for context in list(self._active_contexts.values()):
            await self.cleanup_context(context)


# =============================================================================
# Factory Function
# =============================================================================


def create_subagent_manager(project_root: Optional[Path] = None) -> AgentRunner:
    """Create a subagent manager instance."""
    return AgentRunner(project_root)


# =============================================================================
# Convenience Functions
# =============================================================================


async def create_subagent_context(
    agent_type: str,
    project_root: Optional[Path] = None,
    **kwargs,
) -> SubagentContext:
    """
    Convenience function to create a subagent context.

    Args:
        agent_type: Type of agent ("Explore", "Plan", "General", "Verification")
        project_root: Project root directory
        **kwargs: Additional context parameters

    Returns:
        SubagentContext with complete isolation
    """
    runner = create_subagent_manager(project_root)

    # Parse agent type
    try:
        at = AgentType(agent_type)
        agent_def = runner.loader.get_builtin_agent(at)
    except ValueError:
        # Try custom agent
        agent_def = runner.loader.get_agent(agent_type)
        if not agent_def:
            raise ValueError(f"Unknown agent type: {agent_type}")

    return await runner.create_subagent_context(agent_def, **kwargs)


# =============================================================================
# Export
# =============================================================================


__all__ = [
    # Types
    "AgentSource",
    "AgentType",
    "IsolationMode",
    "PermissionMode",
    # Definition types
    "AgentFrontmatterSchema",
    "BuiltInAgentDefinition",
    "CustomAgentDefinition",
    "PluginAgentDefinition",
    "AgentDefinition",
    # Core classes
    "SubagentContext",
    "AgentLoader",
    "AgentRunner",
    "MCPServerManager",
    "ToolResolver",
    "BuiltInAgents",
    # Factory
    "create_subagent_manager",
    "create_subagent_context",
]
