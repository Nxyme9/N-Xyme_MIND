"""Video Transitions — Video transition effects"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class VideoTransitions:
    def create_transition(
        self, video1: str, video2: str, output: str, transition: str = "fade", duration: float = 1.0
    ) -> Dict:
        try:
            import subprocess

            if transition == "fade":
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video1,
                    "-i",
                    video2,
                    "-filter_complex",
                    f"[0:v]fade=t=out:st=0:d={duration}[v0];[1:v]fade=t=in:st=0:d={duration}[v1];[v0][v1]concat=n=2:v=1:a=0",
                    "-c:v",
                    "libx264",
                    output,
                ]
            elif transition == "crossfade":
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video1,
                    "-i",
                    video2,
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset=0",
                    "-c:v",
                    "libx264",
                    output,
                ]
            else:
                return {"success": False, "error": f"Unknown transition: {transition}"}
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return {"success": True, "output": output}
            return {"success": False, "error": result.stderr[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}
