"""
Multi-Agent Teams — Team creation, management, and orchestration.

Ported from: tools/TeamCreateTool, tools/TeamDeleteTool (Claude Code)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

TEAM_CREATE_TOOL_NAME = "team_create"
TEAM_DELETE_TOOL_NAME = "team_delete"


@dataclass
class TeamConfig:
    """Configuration for a team of agents."""
    name: str
    description: str = ""
    lead_agent_type: str = "coordinator"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    members: list[str] = field(default_factory=list)
    status: str = "active"
    metadata: dict = field(default_factory=dict)


class TeamRegistry:
    """Registry for managing teams."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".nxyme" / "teams.json"
        self._teams: dict[str, TeamConfig] = {}
        self._load()

    def _load(self) -> None:
        """Load teams from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for name, config in data.items():
                    self._teams[name] = TeamConfig(**config)
            except Exception as e:
                logger.warning(f"Failed to load teams: {e}")

    def _save(self) -> None:
        """Save teams to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: vars(config) for name, config in self._teams.items()}
        self.storage_path.write_text(json.dumps(data, indent=2))

    def create_team(
        self,
        name: str,
        description: str = "",
        lead_agent_type: str = "coordinator",
    ) -> TeamConfig:
        """Create a new team."""
        team = TeamConfig(
            name=name,
            description=description,
            lead_agent_type=lead_agent_type,
        )
        self._teams[name] = team
        self._save()
        logger.info(f"Created team: {name}")
        return team

    def delete_team(self, name: str) -> bool:
        """Delete a team."""
        if name in self._teams:
            del self._teams[name]
            self._save()
            logger.info(f"Deleted team: {name}")
            return True
        return False

    def get_team(self, name: str) -> Optional[TeamConfig]:
        """Get a team by name."""
        return self._teams.get(name)

    def list_teams(self) -> list[TeamConfig]:
        """List all teams."""
        return list(self._teams.values())

    def add_member(self, team_name: str, agent_id: str) -> bool:
        """Add a member to a team."""
        team = self._teams.get(team_name)
        if team:
            if agent_id not in team.members:
                team.members.append(agent_id)
                self._save()
            return True
        return False

    def remove_member(self, team_name: str, agent_id: str) -> bool:
        """Remove a member from a team."""
        team = self._teams.get(team_name)
        if team and agent_id in team.members:
            team.members.remove(agent_id)
            self._save()
            return True
        return False

    def update_team(self, name: str, **updates: Any) -> bool:
        """Update team configuration."""
        team = self._teams.get(name)
        if team:
            for key, value in updates.items():
                if hasattr(team, key):
                    setattr(team, key, value)
            self._save()
            return True
        return False


def create_team(
    name: str,
    description: str = "",
    agent_type: str = "coordinator",
) -> dict[str, Any]:
    """Create a new team (CLI/API entry point)."""
    registry = TeamRegistry()
    team = registry.create_team(name, description, agent_type)
    return {
        "team_name": team.name,
        "team_file_path": str(registry.storage_path),
        "lead_agent_id": f"lead-{team.name}-{uuid.uuid4().hex[:6]}",
        "status": "created",
    }


def delete_team(name: str) -> dict[str, Any]:
    """Delete a team (CLI/API entry point)."""
    registry = TeamRegistry()
    success = registry.delete_team(name)
    return {
        "team_name": name,
        "status": "deleted" if success else "not_found",
    }


def list_teams() -> list[dict[str, Any]]:
    """List all teams (CLI/API entry point)."""
    registry = TeamRegistry()
    return [
        {
            "name": t.name,
            "description": t.description,
            "lead_agent_type": t.lead_agent_type,
            "members": t.members,
            "created_at": t.created_at,
            "status": t.status,
        }
        for t in registry.list_teams()
    ]


def get_team(name: str) -> Optional[dict[str, Any]]:
    """Get a team by name (CLI/API entry point)."""
    registry = TeamRegistry()
    team = registry.get_team(name)
    if team:
        return {
            "name": team.name,
            "description": team.description,
            "lead_agent_type": team.lead_agent_type,
            "members": team.members,
            "created_at": team.created_at,
            "status": team.status,
        }
    return None


def add_team_member(team_name: str, agent_id: str) -> dict[str, Any]:
    """Add a member to a team."""
    registry = TeamRegistry()
    success = registry.add_member(team_name, agent_id)
    return {"team_name": team_name, "agent_id": agent_id, "status": "added" if success else "not_found"}


def remove_team_member(team_name: str, agent_id: str) -> dict[str, Any]:
    """Remove a member from a team."""
    registry = TeamRegistry()
    success = registry.remove_member(team_name, agent_id)
    return {"team_name": team_name, "agent_id": agent_id, "status": "removed" if success else "not_found"}


__all__ = [
    "TeamConfig",
    "TeamRegistry",
    "TEAM_CREATE_TOOL_NAME",
    "TEAM_DELETE_TOOL_NAME",
    "create_team",
    "delete_team",
    "list_teams",
    "get_team",
    "add_team_member",
    "remove_team_member",
]
