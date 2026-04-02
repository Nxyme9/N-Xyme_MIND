"""Workspace Manager — Manage workspaces and projects"""

import json, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class WorkspaceManager:
    def __init__(self, workspace_file: str = "data/workspaces.json"):
        self.workspace_file = Path(workspace_file)
        self.workspace_file.parent.mkdir(parents=True, exist_ok=True)
        self._workspaces: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.workspace_file.exists():
            self._workspaces = json.loads(self.workspace_file.read_text(encoding="utf-8"))

    def _save(self):
        self.workspace_file.write_text(json.dumps(self._workspaces, indent=2), encoding="utf-8")

    def create(self, name: str, path: str, description: str = ""):
        self._workspaces[name] = {
            "path": path,
            "description": description,
            "created": str(Path(path).stat().st_mtime),
        }
        self._save()

    def get(self, name: str) -> Dict:
        return self._workspaces.get(name, {})

    def list_all(self) -> List[str]:
        return list(self._workspaces.keys())

    def delete(self, name: str) -> bool:
        if name in self._workspaces:
            del self._workspaces[name]
            self._save()
            return True
        return False
