"""Waveform — Generate waveform display data"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class WaveformGenerator:
    def generate(self, audio_path: str, num_points: int = 1000) -> Dict:
        try:
            import soundfile as sf
            import numpy as np

            data, sr = sf.read(audio_path)
            if len(data.shape) > 1:
                data = data[:, 0]
            chunk_size = len(data) // num_points
            peaks = []
            for i in range(num_points):
                chunk = data[i * chunk_size : (i + 1) * chunk_size]
                peaks.append(round(float(np.max(np.abs(chunk))), 4))
            return {
                "peaks": peaks,
                "sample_rate": sr,
                "duration": len(data) / sr,
                "num_points": num_points,
            }
        except ImportError:
            return {"error": "soundfile/numpy not installed"}
