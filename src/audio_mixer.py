"""Audio Mixer — Mix multiple audio tracks"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AudioMixer:
    def mix(self, tracks: List[Dict]) -> Dict:
        """Mix multiple audio tracks. Each track: {path, volume (0-1), pan (-1 to 1)}"""
        try:
            import numpy as np
            import soundfile as sf

            mixed = None
            sample_rate = None
            for track in tracks:
                data, sr = sf.read(track["path"])
                if sample_rate is None:
                    sample_rate = sr
                volume = track.get("volume", 1.0)
                data = data * volume
                if mixed is None:
                    mixed = data
                else:
                    min_len = min(len(mixed), len(data))
                    mixed[:min_len] += data[:min_len]
            if mixed is not None:
                mixed = np.clip(mixed, -1.0, 1.0)
            return {
                "success": True,
                "sample_rate": sample_rate,
                "samples": len(mixed) if mixed is not None else 0,
            }
        except ImportError:
            return {"success": False, "error": "numpy/soundfile not installed"}
