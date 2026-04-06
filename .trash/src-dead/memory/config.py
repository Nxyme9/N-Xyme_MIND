"""Memory Drive Configuration — Multi-drive mount point management."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class DriveConfig:
    """Configuration for a mounted drive."""

    name: str
    path: Path
    enabled: bool = True

    @property
    def exists(self) -> bool:
        return self.path.exists() and self.path.is_dir()

    def health_check(self) -> bool:
        if not self.exists:
            return False
        try:
            os.access(self.path, os.R_OK | os.X_OK)
            return True
        except Exception:
            return False


DRIVES = [
    DriveConfig(name="Library", path=Path(os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"))),
    DriveConfig(name="WIN_LIBRARY", path=Path(os.environ.get("NX_DRIVE_WIN_LIBRARY", "/mnt/WIN_LIBRARY"))),
    DriveConfig(name="NXYME_CORE", path=Path(os.environ.get("NX_DRIVE_NXYME_CORE", "/mnt/NXYME_CORE"))),
    DriveConfig(name="NXYME_IMAGES", path=Path(os.environ.get("NX_DRIVE_NXYME_IMAGES", "/mnt/NXYME_IMAGES"))),
    DriveConfig(name="backup", path=Path(os.environ.get("NX_DRIVE_BACKUP", "/mnt/backup"))),
]

WATCHED_DIRECTORIES = [
    os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
    os.environ.get("NX_DRIVE_WIN_LIBRARY", "/mnt/WIN_LIBRARY"),
    os.environ.get("NX_DRIVE_NXYME_CORE", "/mnt/NXYME_CORE"),
    os.environ.get("NX_DRIVE_NXYME_IMAGES", "/mnt/NXYME_IMAGES"),
]


@dataclass
class ConfigSchema:
    """Schema for watched directory configuration."""

    drives: List[DriveConfig]
    watched_dirs: List[str]

    @classmethod
    def from_env(cls) -> "ConfigSchema":
        watched = (
            os.environ.get("NX_WATCHED_DIRS", "").split(":")
            if os.environ.get("NX_WATCHED_DIRS")
            else WATCHED_DIRECTORIES
        )
        return cls(drives=DRIVES, watched_dirs=watched)


def list_drives() -> List[DriveConfig]:
    """List all configured drives."""
    return DRIVES


def list_mounted_drives() -> List[DriveConfig]:
    """List only currently mounted/accessible drives."""
    return [d for d in DRIVES if d.exists]


def health_check_drives() -> dict:
    """Run health check on all configured drives."""
    results = {}
    for drive in DRIVES:
        results[drive.name] = {
            "path": str(drive.path),
            "exists": drive.exists,
            "healthy": drive.health_check(),
        }
    return results


def get_drive(name: str) -> Optional[DriveConfig]:
    """Get drive config by name."""
    for drive in DRIVES:
        if drive.name == name:
            return drive
    return None
