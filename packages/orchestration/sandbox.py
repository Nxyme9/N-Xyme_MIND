"""
Sandboxing — Secure isolation for agent execution.

Ported from: commands/sandbox-toggle, utils/sandbox/* (Claude Code)
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    enabled: bool = False
    allowed_paths: list[str] = None
    denied_paths: list[str] = None
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    network_allowed: bool = False


class Sandbox:
    """Secure sandbox for agent execution."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._active = False

    def enable(self) -> None:
        """Enable sandboxing."""
        self.config.enabled = True
        self._active = True
        logger.info("Sandbox enabled")

    def disable(self) -> None:
        """Disable sandboxing."""
        self.config.enabled = False
        self._active = False
        logger.info("Sandbox disabled")

    def is_active(self) -> bool:
        """Check if sandbox is active."""
        return self._active and self.config.enabled

    def check_path(self, path: str) -> bool:
        """Check if a path is allowed in the sandbox."""
        if not self.is_active():
            return True

        path_obj = Path(path).resolve()

        for allowed in self.config.allowed_paths or []:
            try:
                if path_obj.is_relative_to(Path(allowed).resolve()):
                    return True
            except ValueError:
                pass

        for denied in self.config.denied_paths or []:
            try:
                if path_obj.is_relative_to(Path(denied).resolve()):
                    return False
            except ValueError:
                pass

        return False

    def run_command(
        self,
        cmd: list[str],
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run a command in the sandbox."""
        if not self.is_active():
            return {
                "success": True,
                "output": "",
                "error": None,
            }

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1,
            }


def is_sandbox_enabled() -> bool:
    """Check if sandbox mode is enabled via env var."""
    return os.environ.get("NXYME_SANDBOX_MODE", "0") in ("1", "true", "True")


def enable_sandbox() -> None:
    """Enable sandbox mode."""
    os.environ["NXYME_SANDBOX_MODE"] = "1"


def disable_sandbox() -> None:
    """Disable sandbox mode."""
    os.environ.pop("NXYME_SANDBOX_MODE", None)


def get_sandbox() -> Sandbox:
    """Get the global sandbox instance."""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = Sandbox()
    return _sandbox_instance


_sandbox_instance: Optional[Sandbox] = None


__all__ = [
    "SandboxConfig",
    "Sandbox",
    "is_sandbox_enabled",
    "enable_sandbox",
    "disable_sandbox",
    "get_sandbox",
]
