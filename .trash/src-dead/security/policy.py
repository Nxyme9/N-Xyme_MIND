"""Security policy definitions for agent filesystem access.

Provides default policies per agent type, custom policy support,
and policy validation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.security.sandbox import AccessLevel


@dataclass
class AgentPolicy:
    """Filesystem access policy for a specific agent type."""

    agent_type: str
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    access_level: AccessLevel = AccessLevel.READ
    follow_symlinks: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "allowed_paths": self.allowed_paths,
            "denied_paths": self.denied_paths,
            "access_level": self.access_level.value,
            "follow_symlinks": self.follow_symlinks,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentPolicy":
        return cls(
            agent_type=data["agent_type"],
            allowed_paths=data.get("allowed_paths", []),
            denied_paths=data.get("denied_paths", []),
            access_level=AccessLevel(data.get("access_level", "read")),
            follow_symlinks=data.get("follow_symlinks", False),
            description=data.get("description", ""),
        )


class SecurityPolicy:
    """Manages filesystem access policies for all agent types.

    Provides default policies, custom policy support, and validation.
    """

    DEFAULT_POLICIES: dict[str, AgentPolicy] = {
        "sisyphus": AgentPolicy(
            agent_type="sisyphus",
            allowed_paths=["."],
            access_level=AccessLevel.FULL,
            follow_symlinks=True,
            description="Primary orchestrator — full workspace access",
        ),
        "prometheus": AgentPolicy(
            agent_type="prometheus",
            allowed_paths=["."],
            access_level=AccessLevel.READ_WRITE,
            follow_symlinks=True,
            description="Plan builder — read/write workspace",
        ),
        "hephaestus": AgentPolicy(
            agent_type="hephaestus",
            allowed_paths=["src/", "tests/", "bin/"],
            access_level=AccessLevel.READ_WRITE,
            follow_symlinks=False,
            description="Implementation agent — code directories only",
        ),
        "oracle": AgentPolicy(
            agent_type="oracle",
            allowed_paths=["."],
            access_level=AccessLevel.READ,
            follow_symlinks=True,
            description="Architecture reviewer — read-only workspace",
        ),
        "explore": AgentPolicy(
            agent_type="explore",
            allowed_paths=["src/", "tests/", "docs/", "bin/"],
            access_level=AccessLevel.READ,
            follow_symlinks=False,
            description="Codebase search agent — read code directories",
        ),
        "librarian": AgentPolicy(
            agent_type="librarian",
            allowed_paths=["."],
            access_level=AccessLevel.READ,
            follow_symlinks=False,
            description="External research agent — read workspace",
        ),
        "metis": AgentPolicy(
            agent_type="metis",
            allowed_paths=["."],
            access_level=AccessLevel.READ,
            follow_symlinks=True,
            description="Pre-planning agent — read-only workspace",
        ),
        "momus": AgentPolicy(
            agent_type="momus",
            allowed_paths=["."],
            access_level=AccessLevel.READ,
            follow_symlinks=True,
            description="Adversarial reviewer — read-only workspace",
        ),
        "atlas": AgentPolicy(
            agent_type="atlas",
            allowed_paths=["src/", "tests/", "bin/"],
            access_level=AccessLevel.READ_WRITE,
            follow_symlinks=False,
            description="Plan executor — code directories read/write",
        ),
        "sisyphus-junior": AgentPolicy(
            agent_type="sisyphus-junior",
            allowed_paths=["src/", "tests/"],
            access_level=AccessLevel.READ_WRITE,
            follow_symlinks=False,
            description="Trivial fix agent — limited read/write",
        ),
    }

    ALWAYS_DENIED: list[str] = [
        "/etc",
        "/proc",
        "/sys",
        "/dev",
        "/root",
        "/var/log",
        "/tmp",
    ]

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._workspace_root = (
            Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        )
        self._policies: dict[str, AgentPolicy] = dict(self.DEFAULT_POLICIES)
        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """Resolve all relative paths against workspace root."""
        for policy in self._policies.values():
            policy.allowed_paths = [str(self._resolve(p)) for p in policy.allowed_paths]
            policy.denied_paths = [
                str(self._resolve(p)) for p in (policy.denied_paths or [])
            ] + list(self.ALWAYS_DENIED)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        return (self._workspace_root / p).resolve()

    def get_policy(self, agent_type: str) -> AgentPolicy | None:
        return self._policies.get(agent_type)

    def set_policy(self, policy: AgentPolicy) -> None:
        policy.allowed_paths = [str(self._resolve(p)) for p in policy.allowed_paths]
        policy.denied_paths = [
            str(self._resolve(p)) for p in (policy.denied_paths or [])
        ] + list(self.ALWAYS_DENIED)
        self._policies[policy.agent_type] = policy

    def remove_policy(self, agent_type: str) -> bool:
        if agent_type in self.DEFAULT_POLICIES:
            return False
        return self._policies.pop(agent_type, None) is not None

    def list_policies(self) -> list[AgentPolicy]:
        return list(self._policies.values())

    def validate_policy(self, policy: AgentPolicy) -> list[str]:
        """Validate a policy and return a list of errors (empty if valid)."""
        errors: list[str] = []

        if not policy.agent_type or not policy.agent_type.strip():
            errors.append("agent_type must be non-empty")

        if not policy.allowed_paths:
            errors.append("allowed_paths must not be empty")

        for path in policy.allowed_paths:
            p = Path(path)
            if not p.is_absolute():
                errors.append(f"allowed_path must be absolute: {path}")

        for path in policy.denied_paths:
            p = Path(path)
            if not p.is_absolute():
                errors.append(f"denied_path must be absolute: {path}")

        if policy.access_level not in AccessLevel:
            errors.append(f"invalid access_level: {policy.access_level}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            agent_type: policy.to_dict()
            for agent_type, policy in self._policies.items()
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], workspace_root: str | Path | None = None
    ) -> "SecurityPolicy":
        policy = cls(workspace_root=workspace_root)
        for agent_type, policy_data in data.items():
            agent_policy = AgentPolicy.from_dict(
                {"agent_type": agent_type, **policy_data}
            )
            policy.set_policy(agent_policy)
        return policy

    @classmethod
    def from_json(
        cls, json_str: str, workspace_root: str | Path | None = None
    ) -> "SecurityPolicy":
        data = json.loads(json_str)
        return cls.from_dict(data, workspace_root=workspace_root)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())

    @classmethod
    def load(
        cls, path: str | Path, workspace_root: str | Path | None = None
    ) -> "SecurityPolicy":
        p = Path(path)
        if not p.exists():
            return cls(workspace_root=workspace_root)
        return cls.from_json(p.read_text(), workspace_root=workspace_root)
