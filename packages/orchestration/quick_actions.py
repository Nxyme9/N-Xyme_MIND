"""
Quick Actions — Fast command execution (ported from LIVE)

Provides quick access to common operations.

Usage:
    actions = QuickActions()
    actions.run("open_file", path="test.py")
    actions.run("run_tests")
    actions.run("git_commit", message="fix: update")
"""

import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QuickActions:
    """Fast command execution."""

    def __init__(self):
        self._actions: Dict[str, Callable] = {}
        self._register_defaults()
        logger.info("QuickActions: Initialized")

    def _register_defaults(self):
        """Register default actions."""
        self._actions = {
            "open_file": self._open_file,
            "run_tests": self._run_tests,
            "run_command": self._run_command,
            "git_status": self._git_status,
            "git_commit": self._git_commit,
            "git_push": self._git_push,
            "npm_install": self._npm_install,
            "pip_install": self._pip_install,
            "start_service": self._start_service,
            "stop_service": self._stop_service,
        }

    def register(self, name: str, handler: Callable):
        """Register custom action."""
        self._actions[name] = handler

    def run(self, action: str, **kwargs) -> Any:
        """Run an action."""
        handler = self._actions.get(action)
        if not handler:
            logger.error(f"QuickActions: Unknown action '{action}'")
            return None

        try:
            return handler(**kwargs)
        except Exception as e:
            logger.error(f"QuickActions: '{action}' failed: {e}")
            return None

    def list_actions(self) -> List[str]:
        """List available actions."""
        return list(self._actions.keys())

    # Default action handlers

    def _open_file(self, path: str) -> str:
        """Open file in default editor."""
        import os

        os.startfile(path)
        return f"Opened {path}"

    def _run_tests(self, path: str = ".", verbose: bool = False) -> str:
        """Run tests."""
        cmd = ["pytest", path]
        if verbose:
            cmd.append("-v")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout[:500]

    def _run_command(self, cmd: str, cwd: str = ".") -> str:
        """Run shell command."""
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        return result.stdout[:500]

    def _git_status(self) -> str:
        """Get git status."""
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:500]

    def _git_commit(self, message: str) -> str:
        """Git commit."""
        subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:500]

    def _git_push(self) -> str:
        """Git push."""
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout[:500]

    def _npm_install(self, cwd: str = ".") -> str:
        """npm install."""
        result = subprocess.run(
            ["npm", "install"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
        )
        return result.stdout[:500]

    def _pip_install(self, package: str) -> str:
        """pip install."""
        result = subprocess.run(
            ["pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout[:500]

    def _start_service(self, name: str) -> str:
        """Start PM2 service."""
        result = subprocess.run(
            ["pm2", "start", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout[:200]

    def _stop_service(self, name: str) -> str:
        """Stop PM2 service."""
        result = subprocess.run(
            ["pm2", "stop", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout[:200]
