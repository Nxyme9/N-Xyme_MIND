"""Cloud Sync — Synchronize files to cloud storage"""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class CloudSync:
    def __init__(self, local_dir: str = "data/sync"):
        self.local_dir = Path(local_dir)
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self._synced: Dict[str, str] = {}

    def register(self, local_path: str, remote_path: str):
        self._synced[local_path] = remote_path

    def sync_up(self, local_path: str) -> Dict:
        path = Path(local_path)
        if not path.exists():
            return {"success": False, "error": "File not found"}
        remote = self._synced.get(local_path)
        if remote:
            import shutil

            shutil.copy2(path, self.local_dir / Path(remote).name)
            return {"success": True, "remote": remote}
        return {"success": False, "error": "Not registered"}

    def sync_down(self, remote_path: str, local_path: str) -> Dict:
        src = self.local_dir / Path(remote_path).name
        if src.exists():
            import shutil

            shutil.copy2(src, local_path)
            return {"success": True, "local": local_path}
        return {"success": False, "error": "Remote file not found"}

    def list_synced(self) -> Dict:
        return self._synced.copy()
