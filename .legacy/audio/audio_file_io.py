"""Audio File IO — Read/write audio files"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AudioFileIO:
    @staticmethod
    def read(path: str) -> Optional[Dict]:
        try:
            import soundfile as sf

            data, sr = sf.read(path)
            return {
                "data": data.tolist() if hasattr(data, "tolist") else data,
                "sample_rate": sr,
                "channels": 1 if len(data.shape) == 1 else data.shape[1],
            }
        except ImportError:
            return {"error": "soundfile not installed"}

    @staticmethod
    def write(path: str, data: List[float], sample_rate: int = 44100):
        try:
            import soundfile as sf
            import numpy as np

            sf.write(path, np.array(data), sample_rate)
        except ImportError:
            logger.error("soundfile not installed")

    @staticmethod
    def convert(input_path: str, output_path: str, format: str = "wav"):
        try:
            import subprocess

            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, output_path], capture_output=True, timeout=60
            )
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
