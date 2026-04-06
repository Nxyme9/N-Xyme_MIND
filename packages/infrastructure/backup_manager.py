"""Backup Manager — Automated backup system"""

import logging, shutil, time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self, backup_dir: str = "data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, source_path: str, name: Optional[str] = None) -> Dict:
        source = Path(source_path)
        if not source.exists():
            return {"success": False, "error": "Source not found"}
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name = name or source.stem
        backup_path = self.backup_dir / f"{name}_{timestamp}"
        if source.is_dir():
            shutil.copytree(source, backup_path)
        else:
            backup_path = backup_path.with_suffix(source.suffix)
            shutil.copy2(source, backup_path)
        logger.info(f"BackupManager: Backed up {source} to {backup_path}")
        return {"success": True, "backup": str(backup_path)}

    def restore(self, backup_name: str, target_path: str) -> Dict:
        backups = list(self.backup_dir.glob(f"{backup_name}*"))
        if not backups:
            return {"success": False, "error": "Backup not found"}
        latest = max(backups, key=lambda p: p.stat().st_mtime)
        if latest.is_dir():
            shutil.copytree(latest, target_path)
        else:
            shutil.copy2(latest, target_path)
        return {"success": True, "restored": str(latest)}

    def list_backups(self) -> List[str]:
        return [p.name for p in self.backup_dir.iterdir()]
