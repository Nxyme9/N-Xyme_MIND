"""Filesystem sandbox for agent path access control.

Provides path validation, symlink resolution, traversal prevention,
and integration with observability (metrics + structured logging).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePath
from typing import Any

from src.tools.observability.logger import get_logger
from src.observability.metrics import get_metrics_collector

logger = get_logger(__name__)


class AccessLevel(Enum):
    """Filesystem access levels for agents."""

    NONE = "none"
    READ = "read"
    READ_WRITE = "read_write"
    FULL = "full"


@dataclass
class ValidationResult:
    """Result of a path validation check."""

    allowed: bool
    path: str
    resolved_path: str | None = None
    reason: str | None = None
    access_level: AccessLevel = AccessLevel.NONE
    agent_type: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "path": self.path,
            "resolved_path": self.resolved_path,
            "reason": self.reason,
            "access_level": self.access_level.value,
            "agent_type": self.agent_type,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class PathTraversalError(ValueError):
    """Raised when a path traversal attack is detected."""


class SymlinkError(ValueError):
    """Raised when a symlink resolution fails or points outside allowed paths."""


class AccessDeniedError(PermissionError):
    """Raised when access to a path is denied by policy."""


class FilesystemSandbox:
    """Filesystem sandbox enforcing per-agent path access policies.

    Features:
    - Allowed path configuration per agent type
    - Path traversal prevention (../ attacks)
    - Symlink resolution and validation
    - Integration with metrics (blocked attempts, validation count)
    - Integration with structured JSON logging
    """

    def __init__(
        self,
        workspace_root: str | Path | None = None,
        default_access: AccessLevel = AccessLevel.READ,
    ) -> None:
        self._workspace_root = (
            Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        )
        self._default_access = default_access
        self._policies: dict[str, dict[str, Any]] = {}
        self._metrics = get_metrics_collector()

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def set_policy(
        self,
        agent_type: str,
        allowed_paths: list[str] | None = None,
        denied_paths: list[str] | None = None,
        access_level: AccessLevel = AccessLevel.READ,
        follow_symlinks: bool = False,
    ) -> None:
        """Set or update the filesystem policy for an agent type."""
        resolved_allowed = [str(Path(p).resolve()) for p in (allowed_paths or [])]
        resolved_denied = [str(Path(p).resolve()) for p in (denied_paths or [])]

        self._policies[agent_type] = {
            "allowed_paths": resolved_allowed,
            "denied_paths": resolved_denied,
            "access_level": access_level,
            "follow_symlinks": follow_symlinks,
        }

    def get_policy(self, agent_type: str) -> dict[str, Any] | None:
        return self._policies.get(agent_type)

    def get_allowed_paths(self, agent_type: str) -> list[str]:
        policy = self.get_policy(agent_type)
        if policy is None:
            return [str(self._workspace_root)]
        return list(policy.get("allowed_paths", [str(self._workspace_root)]))

    def get_access_level(self, agent_type: str) -> AccessLevel:
        policy = self.get_policy(agent_type)
        if policy is None:
            return self._default_access
        return policy.get("access_level", self._default_access)

    def follows_symlinks(self, agent_type: str) -> bool:
        policy = self.get_policy(agent_type)
        if policy is None:
            return False
        return policy.get("follow_symlinks", False)

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    @staticmethod
    def _has_traversal(path: str) -> bool:
        """Detect path traversal attempts in the raw string."""
        parts = PurePath(path).parts
        return ".." in parts

    def _is_within_allowed(self, resolved: Path, agent_type: str) -> bool:
        """Check if a resolved path is within any allowed path."""
        allowed = self.get_allowed_paths(agent_type)
        resolved_str = str(resolved)

        for allowed_path in allowed:
            allowed_resolved = Path(allowed_path).resolve()
            if resolved == allowed_resolved or str(resolved).startswith(
                str(allowed_resolved) + os.sep
            ):
                return True
        return False

    def _is_within_denied(self, resolved: Path, agent_type: str) -> bool:
        """Check if a resolved path is within any denied path."""
        policy = self.get_policy(agent_type)
        if policy is None:
            return False

        denied = policy.get("denied_paths", [])
        resolved_str = str(resolved)

        for denied_path in denied:
            denied_resolved = Path(denied_path).resolve()
            if resolved == denied_resolved or str(resolved).startswith(
                str(denied_resolved) + os.sep
            ):
                return True
        return False

    def validate_path(self, path: str, agent_type: str) -> ValidationResult:
        """Validate if a path is allowed for a given agent type.

        Performs:
        1. Traversal attack detection
        2. Symlink resolution
        3. Allowed/denied path checks
        4. Metrics recording
        5. Structured logging
        """
        self._metrics.counter_inc("sandbox_validations_total")

        # Step 1: Check for path traversal in raw string
        if self._has_traversal(path):
            result = ValidationResult(
                allowed=False,
                path=path,
                reason="Path traversal detected",
                agent_type=agent_type,
            )
            self._record_blocked(result)
            return result

        # Step 2: Resolve the path
        try:
            resolved = self._resolve_path_internal(path)
        except (PathTraversalError, SymlinkError) as exc:
            result = ValidationResult(
                allowed=False,
                path=path,
                reason=str(exc),
                agent_type=agent_type,
            )
            self._record_blocked(result)
            return result

        # Step 3: Check denied paths first (deny overrides allow)
        if self._is_within_denied(resolved, agent_type):
            result = ValidationResult(
                allowed=False,
                path=path,
                resolved_path=str(resolved),
                reason="Path is in denied list",
                agent_type=agent_type,
            )
            self._record_blocked(result)
            return result

        # Step 4: Check allowed paths
        if not self._is_within_allowed(resolved, agent_type):
            result = ValidationResult(
                allowed=False,
                path=path,
                resolved_path=str(resolved),
                reason="Path not in allowed paths",
                agent_type=agent_type,
            )
            self._record_blocked(result)
            return result

        # Step 5: All checks passed
        result = ValidationResult(
            allowed=True,
            path=path,
            resolved_path=str(resolved),
            access_level=self.get_access_level(agent_type),
            agent_type=agent_type,
        )
        self._record_allowed(result)
        return result

    # ------------------------------------------------------------------
    # Symlink resolution
    # ------------------------------------------------------------------

    def _resolve_path_internal(self, path: str) -> Path:
        """Resolve a path including symlinks, validating each component."""
        p = Path(path)

        if not p.is_absolute():
            p = self._workspace_root / p

        if not p.exists():
            return p.resolve()

        return self.resolve_path(str(p))

    def resolve_path(self, path: str) -> Path:
        """Resolve symlinks and validate the result stays within workspace.

        Raises:
            SymlinkError: If a symlink points outside allowed boundaries.
        """
        p = Path(path)

        if not p.is_absolute():
            p = self._workspace_root / p

        if not p.exists():
            return p.resolve()

        # Resolve symlinks step by step
        parts: list[str] = []
        current = Path(p.root) if p.is_absolute() else Path.cwd()

        for part in p.parts[1:] if p.is_absolute() else p.parts:
            current = current / part

            if current.is_symlink():
                target = current.resolve()
                if not str(target).startswith(str(self._workspace_root)):
                    raise SymlinkError(
                        f"Symlink {current} points outside workspace: {target}"
                    )
                current = target
            elif current.exists():
                current = current.resolve()

        return current

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def is_path_allowed(self, path: str, agent_type: str) -> bool:
        """Quick boolean check for path access."""
        return self.validate_path(path, agent_type).allowed

    def check_access_level(
        self, path: str, agent_type: str, required: AccessLevel
    ) -> bool:
        """Check if an agent has at least the required access level for a path."""
        result = self.validate_path(path, agent_type)
        if not result.allowed:
            return False

        level_order = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.READ_WRITE: 2,
            AccessLevel.FULL: 3,
        }

        return level_order.get(result.access_level, 0) >= level_order.get(required, 0)

    # ------------------------------------------------------------------
    # Observability integration
    # ------------------------------------------------------------------

    def _record_allowed(self, result: ValidationResult) -> None:
        self._metrics.counter_inc("sandbox_allowed_total")
        if result.agent_type:
            self._metrics.counter_inc(f"sandbox_allowed_{result.agent_type}_total")

        logger.info(
            "[SANDBOX] ALLOWED: path=%s agent=%s resolved=%s",
            result.path,
            result.agent_type,
            result.resolved_path,
            extra={"context": result.to_dict()},
        )

    def _record_blocked(self, result: ValidationResult) -> None:
        self._metrics.counter_inc("sandbox_blocked_total")
        if result.agent_type:
            self._metrics.counter_inc(f"sandbox_blocked_{result.agent_type}_total")

        logger.warning(
            "[SANDBOX] BLOCKED: path=%s agent=%s reason=%s",
            result.path,
            result.agent_type,
            result.reason,
            extra={"context": result.to_dict()},
        )

    def get_stats(self) -> dict[str, Any]:
        """Get sandbox statistics from metrics."""
        metrics = self._metrics.get_all_metrics()
        counters = metrics.get("counters", {})
        return {
            "total_validations": counters.get("sandbox_validations_total", 0),
            "total_allowed": counters.get("sandbox_allowed_total", 0),
            "total_blocked": counters.get("sandbox_blocked_total", 0),
            "policies_count": len(self._policies),
            "workspace_root": str(self._workspace_root),
        }
