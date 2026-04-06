"""
packages.platform — N-Xyme Platform bundle.

A unified package containing CLI tools, dashboards, TUI, and operational scripts.
This package provides a consolidated entry point for all platform-level functionality.

Subpackages:
- scripts.health: Health check scripts (L0 blink, L1 pulse, L2 vitals, monitor)
- scripts.quality_gates: Quality gate scripts for CI/CD
- scripts.model: Model routing and selection scripts
- scripts.memory: Memory service scripts
- scripts.ops: Operational scripts (MCP doctor, service management)
- cli: Command-line interface tools
- dashboard: Monitoring and routing dashboards
- tui: Text-based user interface modules
"""

from packages.platform.launcher import main as launch, load_memory_context, check_ollama

__all__ = [
    "launch",
    "main",
    "load_memory_context",
    "check_ollama",
]

__version__ = "0.1.0"
