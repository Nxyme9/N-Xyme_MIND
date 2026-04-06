"""Video Playback — Video playback integration"""

import logging, subprocess
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class VideoPlayback:
    def play(self, video_path: str, player: str = "default") -> Dict:
        try:
            import os

            if player == "default":
                os.startfile(video_path)
            elif player == "vlc":
                subprocess.Popen(["vlc", video_path])
            elif player == "mpv":
                subprocess.Popen(["mpv", video_path])
            return {"success": True, "path": video_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_info(self, video_path: str) -> Dict:
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            import json

            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}
