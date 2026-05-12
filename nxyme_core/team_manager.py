import logging
import uuid
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_FILE = Path.home() / ".nxyme" / "teams.json"


@dataclass
class Team:
    id: str
    name: str
    members: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TeamManager:
    def __init__(self):
        self._teams: Dict[str, Team] = {}
        self._load()

    def _load(self):
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text())
                for t in data.get("teams", []):
                    self._teams[t["id"]] = Team(**t)
            except Exception as e:
                logger.warning(f"Failed to load teams: {e}")

    def _save(self):
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"teams": [asdict(t) for t in self._teams.values()]}
        DATA_FILE.write_text(json.dumps(data, indent=2, default=str))

    def create_team(self, name: str, members: List[str] = None) -> str:
        team_id = f"team_{uuid.uuid4().hex[:8]}"
        team = Team(id=team_id, name=name, members=members or [])
        self._teams[team_id] = team
        self._save()
        logger.info(f"Created team {team_id}: {name}")
        return team_id

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        team = self._teams.get(team_id)
        if not team:
            return None
        return {"id": team.id, "name": team.name, "members": team.members, "created_at": team.created_at.isoformat()}

    def list_teams(self) -> List[Dict[str, Any]]:
        return [{"id": t.id, "name": t.name, "members": len(t.members)} for t in self._teams.values()]

    def delete_team(self, team_id: str) -> bool:
        if team_id in self._teams:
            del self._teams[team_id]
            self._save()
            logger.info(f"Deleted team {team_id}")
            return True
        return False

    def add_member(self, team_id: str, member_id: str) -> bool:
        """Add a member to a team."""
        team = self._teams.get(team_id)
        if not team:
            return False
        if member_id not in team.members:
            team.members.append(member_id)
            self._save()
            logger.info(f"Added member {member_id} to team {team_id}")
        return True

    def remove_member(self, team_id: str, member_id: str) -> bool:
        """Remove a member from a team."""
        team = self._teams.get(team_id)
        if not team:
            return False
        if member_id in team.members:
            team.members.remove(member_id)
            self._save()
            logger.info(f"Removed member {member_id} from team {team_id}")
        return True

    def update_team(self, team_id: str, name: str = None, metadata: dict = None) -> bool:
        """Update team properties."""
        team = self._teams.get(team_id)
        if not team:
            return False
        if name:
            team.name = name
        if metadata:
            team.metadata.update(metadata)
        self._save()
        logger.info(f"Updated team {team_id}")
        return True

    def team_exists(self, team_id: str) -> bool:
        """Check if team exists."""
        return team_id in self._teams

    def get_team_members(self, team_id: str) -> List[str]:
        """Get all members of a team."""
        team = self._teams.get(team_id)
        return team.members if team else []


_team_manager: Optional[TeamManager] = None


def get_team_manager() -> TeamManager:
    global _team_manager
    if _team_manager is None:
        _team_manager = TeamManager()
    return _team_manager