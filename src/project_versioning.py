"""Project Versioning — Git-based project versions"""

import json, logging, subprocess
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ProjectVersioning:
    def __init__(self, project_dir: str = "."):
        self.project_dir = project_dir

    def get_version(self) -> Dict:
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10,
            )
            tag = result.stdout.strip() if result.returncode == 0 else "v0.0.0"
            result2 = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10,
            )
            commit = result2.stdout.strip() if result2.returncode == 0 else "unknown"
            return {"version": tag, "commit": commit}
        except Exception as e:
            return {"error": str(e)}

    def create_tag(self, version: str, message: str = None) -> Dict:
        try:
            msg = message or f"Release {version}"
            subprocess.run(
                ["git", "tag", "-a", version, "-m", msg],
                capture_output=True,
                cwd=self.project_dir,
                timeout=10,
            )
            subprocess.run(["git", "push", "origin", version], capture_output=True, timeout=30)
            return {"success": True, "version": version}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tags(self) -> List[str]:
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-v:refname"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10,
            )
            return [t.strip() for t in result.stdout.split("\n") if t.strip()]
        except:
            return []
