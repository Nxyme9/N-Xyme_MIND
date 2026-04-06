"""Log Rotation — Rotate log files by size"""

import logging, os
from pathlib import Path

logger = logging.getLogger(__name__)


class LogRotator:
    def __init__(self, log_dir: str = "data/logs", max_size_mb: int = 10, max_files: int = 5):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size_mb * 1024 * 1024
        self.max_files = max_files

    def rotate(self, filename: str) -> bool:
        path = self.log_dir / filename
        if not path.exists():
            return False
        if path.stat().st_size < self.max_size:
            return False
        for i in range(self.max_files - 1, 0, -1):
            src = self.log_dir / f"{filename}.{i}"
            dst = self.log_dir / f"{filename}.{i + 1}"
            if src.exists():
                src.rename(dst)
        path.rename(self.log_dir / f"{filename}.1")
        logger.info(f"LogRotator: Rotated {filename}")
        return True
