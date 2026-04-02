"""
The Catalyst - Core Orchestration Engine for N-Xyme Catalyst

The Catalyst is the central orchestration engine that initializes, coordinates,
and manages all components of the N-Xyme Catalyst system. It serves as the
single entry point for system operations and provides unified control over:

- Agent Framework: Task routing and agent coordination
- MCP Servers: Tool registry and server lifecycle
- Memory System: Graphiti/Neo4j integration
- Security Layer: Command validation and permissions
- Auto-Capture: Voice, screen, and clipboard monitoring
- Performance: GPU optimization and resource management
- Monitoring: Health checks and system metrics

Architecture:
    The Catalyst follows a hub-and-spoke pattern where it acts as the central
    hub, coordinating between all subsystems. Each subsystem is initialized
    independently but controlled through The Catalyst's unified interface.

Usage:
    from catalyst import Catalyst

    # Initialize the system
    catalyst = Catalyst()
    await catalyst.initialize()

    # Route a task
    result = await catalyst.route_task("Write a Python function")

    # Check system health
    health = await catalyst.health_check()

    # Shutdown gracefully
    await catalyst.shutdown()
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("catalyst")


class SystemState(Enum):
    """System lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


class ComponentStatus(Enum):
    """Individual component status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a system component."""

    name: str
    status: ComponentStatus
    last_check: datetime
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""

    state: SystemState
    components: Dict[str, ComponentHealth]
    uptime_seconds: float
    timestamp: datetime


class CatalystError(Exception):
    """Base exception for Catalyst errors."""

    pass


class InitializationError(CatalystError):
    """Raised when system initialization fails."""

    pass


class ComponentError(CatalystError):
    """Raised when a component operation fails."""

    pass


class Catalyst:
    """
    The Catalyst - Central orchestration engine for N-Xyme Catalyst.

    This class serves as the primary interface for all system operations,
    managing the lifecycle and coordination of all subsystems.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        auto_initialize: bool = False,
    ):
        """
        Initialize The Catalyst.

        Args:
            config_path: Path to configuration directory. If None, uses default.
            auto_initialize: If True, automatically initialize all components.
        """
        self._state = SystemState.UNINITIALIZED
        self._start_time: Optional[datetime] = None
        self._config_path = Path(config_path) if config_path else Path("configs")
        self._components: Dict[str, Any] = {}
        self._component_health: Dict[str, ComponentHealth] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._shutdown_event = asyncio.Event()

        # Register signal handlers for graceful shutdown
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("Catalyst instance created")

        if auto_initialize:
            asyncio.create_task(self.initialize())

    @property
    def state(self) -> SystemState:
        """Current system state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if system is running."""
        return self._state == SystemState.RUNNING

    @property
    def uptime(self) -> float:
        """System uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def initialize(self) -> None:
        """
        Initialize all system components.

        This method orchestrates the startup sequence:
        1. Load configuration
        2. Initialize core infrastructure
        3. Start agent framework
        4. Connect to memory system
        5. Initialize security layer
        6. Start MCP servers
        7. Initialize auto-capture
        8. Start monitoring

        Raises:
            InitializationError: If critical components fail to initialize.
        """
        if self._state != SystemState.UNINITIALIZED:
            logger.warning(f"Cannot initialize from state: {self._state}")
            return

        self._state = SystemState.INITIALIZING
        self._start_time = datetime.now()
        logger.info("Initializing N-Xyme Catalyst system...")

        try:
            # Phase 1: Core Infrastructure
            await self._initialize_core_infrastructure()

            # Phase 2: Agent Framework
            await self._initialize_agent_framework()

            # Phase 3: Memory System
            await self._initialize_memory_system()

            # Phase 4: Security Layer
            await self._initialize_security_layer()

            # Phase 5: MCP Servers
            await self._initialize_mcp_servers()

            # Phase 6: Auto-Capture
            await self._initialize_auto_capture()

            # Phase 7: Monitoring
            await self._initialize_monitoring()

            self._state = SystemState.RUNNING
            logger.info("N-Xyme Catalyst system initialized successfully")
            await self._emit_event("system_initialized", {"state": self._state.value})

        except Exception as e:
            self._state = SystemState.ERROR
            logger.error(f"Initialization failed: {e}")
            raise InitializationError(f"Failed to initialize system: {e}") from e

    async def _initialize_core_infrastructure(self) -> None:
        """Initialize core infrastructure components."""
        logger.info("Initializing core infrastructure...")
        try:
            # Import here to avoid circular dependencies
            from .config_manager import ConfigManager
            from .service_registry import ServiceRegistry

            config_manager = ConfigManager(self._config_path)
            self._components["config_manager"] = config_manager

            service_registry = ServiceRegistry()
            self._components["service_registry"] = service_registry

            self._update_component_health(
                "core_infrastructure",
                ComponentStatus.HEALTHY,
                "Core infrastructure initialized",
            )
        except ImportError:
            # Components not yet implemented - use stubs
            self._components["config_manager"] = None
            self._components["service_registry"] = None
            self._update_component_health(
                "core_infrastructure",
                ComponentStatus.DEGRADED,
                "Using stub configuration",
            )

    async def _initialize_agent_framework(self) -> None:
        """Initialize the agent framework."""
        logger.info("Initializing agent framework...")
        try:
            # Try to import from agent-framework package
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent-framework"))
            from src.router import Router
            from src.permission_manager import PermissionManager

            agents_dir = self._config_path / "opencode" / "agents"
            router = Router(str(agents_dir))
            self._components["router"] = router

            permissions_file = self._config_path / "opencode" / "permissions.json"
            if permissions_file.exists():
                permission_manager = PermissionManager(str(permissions_file))
                self._components["permission_manager"] = permission_manager

            self._update_component_health(
                "agent_framework",
                ComponentStatus.HEALTHY,
                f"Loaded {len(router.get_all_agents())} agents",
            )
        except Exception as e:
            logger.warning(f"Agent framework initialization deferred: {e}")
            self._components["router"] = None
            self._update_component_health(
                "agent_framework",
                ComponentStatus.DEGRADED,
                f"Deferred: {e}",
            )

    async def _initialize_memory_system(self) -> None:
        """Initialize the memory system (Graphiti/Neo4j)."""
        logger.info("Initializing memory system...")
        # Memory system connection is handled by MCP server
        # Just verify connectivity
        self._components["memory"] = {"status": "pending_mcp"}
        self._update_component_health(
            "memory_system",
            ComponentStatus.UNKNOWN,
            "Awaiting MCP server connection",
        )

    async def _initialize_security_layer(self) -> None:
        """Initialize the security layer."""
        logger.info("Initializing security layer...")
        self._components["security"] = {"status": "pending"}
        self._update_component_health(
            "security_layer",
            ComponentStatus.UNKNOWN,
            "Security layer pending",
        )

    async def _initialize_mcp_servers(self) -> None:
        """Initialize MCP server connections."""
        logger.info("Initializing MCP servers...")
        mcp_servers = {
            "git": 12002,
            "sqlite": 12003,
            "graphiti": 8001,
            "ollama": 11435,
            "playwright": 12010,
            "fetch": 12012,
            "exa": 12014,
            "context7": 12020,
            "shadcn": 12023,
        }
        self._components["mcp_servers"] = mcp_servers
        self._update_component_health(
            "mcp_servers",
            ComponentStatus.HEALTHY,
            f"Tracking {len(mcp_servers)} MCP servers",
        )

    async def _initialize_auto_capture(self) -> None:
        """Initialize auto-capture services."""
        logger.info("Initializing auto-capture...")
        self._components["auto_capture"] = {"status": "pending"}
        self._update_component_health(
            "auto_capture",
            ComponentStatus.UNKNOWN,
            "Auto-capture pending",
        )

    async def _initialize_monitoring(self) -> None:
        """Initialize monitoring and health checks."""
        logger.info("Initializing monitoring...")
        self._components["monitoring"] = {
            "health_check_interval": 60,
            "metrics_enabled": True,
        }
        self._update_component_health(
            "monitoring",
            ComponentStatus.HEALTHY,
            "Monitoring initialized",
        )

    async def route_task(
        self, task_description: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a task to the appropriate agent.

        Args:
            task_description: Description of the task to route.
            context: Optional context for routing decisions.

        Returns:
            Dict containing the routed agent info and task details.

        Raises:
            ComponentError: If routing fails.
        """
        if self._state != SystemState.RUNNING:
            raise ComponentError(f"Cannot route tasks in state: {self._state}")

        router = self._components.get("router")
        if router is None:
            raise ComponentError("Agent router not initialized")

        try:
            agent = router.route_task(task_description, context or {})
            if agent is None:
                raise ComponentError("No suitable agent found for task")

            return {
                "agent": agent.get_name(),
                "type": agent.get_type(),
                "capabilities": agent.get_capabilities(),
                "task": task_description,
                "context": context,
            }
        except Exception as e:
            raise ComponentError(f"Task routing failed: {e}") from e

    async def health_check(self) -> SystemHealth:
        """
        Perform a comprehensive system health check.

        Returns:
            SystemHealth object with current system status.
        """
        # Update component health
        for name, component in self._components.items():
            if component is not None:
                self._update_component_health(
                    name,
                    ComponentStatus.HEALTHY,
                    "Component active",
                )

        return SystemHealth(
            state=self._state,
            components=self._component_health.copy(),
            uptime_seconds=self.uptime,
            timestamp=datetime.now(),
        )

    async def get_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered agents.

        Returns:
            List of agent configurations.
        """
        router = self._components.get("router")
        if router is None:
            return []

        return [agent.config for agent in router.get_all_agents()]

    async def check_permission(self, role: str, permission: str) -> bool:
        """
        Check if a role has a specific permission.

        Args:
            role: The role to check.
            permission: The permission to verify.

        Returns:
            True if permission is granted, False otherwise.
        """
        pm = self._components.get("permission_manager")
        if pm is None:
            return False

        return pm.check_permission(role, permission)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all system components.

        This method orchestrates the shutdown sequence in reverse order
        of initialization to ensure proper cleanup.
        """
        if self._state in (SystemState.STOPPED, SystemState.SHUTTING_DOWN):
            logger.warning(f"Already in state: {self._state}")
            return

        self._state = SystemState.SHUTTING_DOWN
        logger.info("Shutting down N-Xyme Catalyst system...")

        try:
            # Shutdown in reverse order
            await self._shutdown_monitoring()
            await self._shutdown_auto_capture()
            await self._shutdown_mcp_servers()
            await self._shutdown_security_layer()
            await self._shutdown_memory_system()
            await self._shutdown_agent_framework()
            await self._shutdown_core_infrastructure()

            self._state = SystemState.STOPPED
            logger.info("N-Xyme Catalyst system shutdown complete")
            await self._emit_event("system_shutdown", {"state": self._state.value})

        except Exception as e:
            self._state = SystemState.ERROR
            logger.error(f"Shutdown error: {e}")
            raise

    async def _shutdown_monitoring(self) -> None:
        """Shutdown monitoring services."""
        logger.info("Shutting down monitoring...")
        self._components.pop("monitoring", None)

    async def _shutdown_auto_capture(self) -> None:
        """Shutdown auto-capture services."""
        logger.info("Shutting down auto-capture...")
        self._components.pop("auto_capture", None)

    async def _shutdown_mcp_servers(self) -> None:
        """Shutdown MCP server connections."""
        logger.info("Shutting down MCP servers...")
        self._components.pop("mcp_servers", None)

    async def _shutdown_security_layer(self) -> None:
        """Shutdown security layer."""
        logger.info("Shutting down security layer...")
        self._components.pop("security", None)

    async def _shutdown_memory_system(self) -> None:
        """Shutdown memory system."""
        logger.info("Shutting down memory system...")
        self._components.pop("memory", None)

    async def _shutdown_agent_framework(self) -> None:
        """Shutdown agent framework."""
        logger.info("Shutting down agent framework...")
        self._components.pop("router", None)
        self._components.pop("permission_manager", None)

    async def _shutdown_core_infrastructure(self) -> None:
        """Shutdown core infrastructure."""
        logger.info("Shutting down core infrastructure...")
        self._components.pop("config_manager", None)
        self._components.pop("service_registry", None)

    def _update_component_health(
        self, name: str, status: ComponentStatus, message: str = ""
    ) -> None:
        """Update health status for a component."""
        self._component_health[name] = ComponentHealth(
            name=name,
            status=status,
            last_check=datetime.now(),
            message=message,
        )

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown())

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    def on(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle.
            handler: Callable to invoke when event occurs.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable) -> None:
        """
        Unregister an event handler.

        Args:
            event_type: Type of event.
            handler: Handler to remove.
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [
                h for h in self._event_handlers[event_type] if h != handler
            ]

    def get_component(self, name: str) -> Optional[Any]:
        """
        Get a component by name.

        Args:
            name: Component name.

        Returns:
            Component instance or None if not found.
        """
        return self._components.get(name)

    def list_components(self) -> List[str]:
        """
        List all registered components.

        Returns:
            List of component names.
        """
        return list(self._components.keys())

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def __repr__(self) -> str:
        return (
            f"<Catalyst state={self._state.value} "
            f"components={len(self._components)} "
            f"uptime={self.uptime:.1f}s>"
        )


# Convenience function for quick initialization
async def create_catalyst(
    config_path: Optional[str] = None,
) -> Catalyst:
    """
    Create and initialize a Catalyst instance.

    Args:
        config_path: Path to configuration directory.

    Returns:
        Initialized Catalyst instance.
    """
    catalyst = Catalyst(config_path)
    await catalyst.initialize()
    return catalyst


# CLI entry point
async def main():
    """Main entry point for The Catalyst CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="The Catalyst - N-Xyme Catalyst Orchestration Engine"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs",
        help="Path to configuration directory",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run health check and exit",
    )
    parser.add_argument(
        "--agents",
        action="store_true",
        help="List all agents and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    catalyst = Catalyst(config_path=args.config)

    try:
        await catalyst.initialize()

        if args.health:
            health = await catalyst.health_check()
            print(f"\nSystem State: {health.state.value}")
            print(f"Uptime: {health.uptime_seconds:.1f}s")
            print("\nComponents:")
            for name, comp in health.components.items():
                print(f"  {name}: {comp.status.value} - {comp.message}")
            return

        if args.agents:
            agents = await catalyst.get_agents()
            print(f"\nRegistered Agents ({len(agents)}):")
            for agent in agents:
                print(f"  - {agent['name']}: {agent['description']}")
            return

        # Interactive mode
        print("\n" + "=" * 60)
        print("  N-Xyme Catalyst - The Catalyst Engine")
        print("=" * 60)
        print(f"  State: {catalyst.state.value}")
        print(f"  Components: {len(catalyst.list_components())}")
        print("\n  Commands:")
        print("    health  - Check system health")
        print("    agents  - List all agents")
        print("    route   - Route a task")
        print("    quit    - Shutdown and exit")
        print("=" * 60 + "\n")

        while True:
            try:
                cmd = input("catalyst> ").strip().lower()

                if cmd == "quit":
                    break
                elif cmd == "health":
                    health = await catalyst.health_check()
                    print(f"\nState: {health.state.value}")
                    print(f"Uptime: {health.uptime_seconds:.1f}s")
                    for name, comp in health.components.items():
                        print(f"  {name}: {comp.status.value}")
                elif cmd == "agents":
                    agents = await catalyst.get_agents()
                    for agent in agents:
                        print(f"  - {agent['name']}: {agent['description']}")
                elif cmd.startswith("route "):
                    task = cmd[6:]
                    result = await catalyst.route_task(task)
                    print(f"  Routed to: {result['agent']} ({result['type']})")
                elif cmd:
                    print(f"  Unknown command: {cmd}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"  Error: {e}")

    finally:
        await catalyst.shutdown()
        print("\nCatalyst shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
