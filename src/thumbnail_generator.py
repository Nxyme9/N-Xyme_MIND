"""Thumbnail Generator — Create video thumbnails"""

import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    def generate(self, video_path: str, output_path: str = None, time_seconds: float = 1.0) -> Dict:
        try:
            import subprocess

            if output_path is None:
                output_path = str(Path(video_path).with_suffix(".jpg"))
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(time_seconds),
                "-i",
                video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"success": True, "output": output_path}
            return {"success": False, "error": result.stderr[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}
