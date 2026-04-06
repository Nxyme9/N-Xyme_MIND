"""Video Processor — Video processing utilities"""

import logging, subprocess
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class VideoProcessor:
    def trim(self, input_path: str, start: float, end: float, output_path: str) -> Dict:
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(start),
                "-i",
                input_path,
                "-t",
                str(end - start),
                "-c",
                "copy",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            return {"success": True, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def resize(self, input_path: str, width: int, height: int, output_path: str) -> Dict:
        try:
            cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"scale={width}:{height}", output_path]
            subprocess.run(cmd, capture_output=True, timeout=120)
            return {"success": True, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_audio(self, video_path: str, output_path: str) -> Dict:
        try:
            cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", output_path]
            subprocess.run(cmd, capture_output=True, timeout=60)
            return {"success": True, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_info(self, video_path: str) -> Dict:
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            import json

            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}
