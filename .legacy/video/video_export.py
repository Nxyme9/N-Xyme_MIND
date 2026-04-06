"""Video Export — FFmpeg video rendering"""

import logging, subprocess
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class VideoExporter:
    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        images_dir: str,
        audio_path: str,
        output_name: str = "output.mp4",
        fps: int = 30,
        resolution: str = "1920x1080",
    ) -> Dict:
        try:
            output_path = self.output_dir / output_name
            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                f"{images_dir}/%04d.png",
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-s",
                resolution,
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": str(output_path),
                    "size_mb": output_path.stat().st_size / (1024 * 1024),
                }
            return {"success": False, "error": result.stderr[:500]}
        except Exception as e:
            return {"success": False, "error": str(e)}
