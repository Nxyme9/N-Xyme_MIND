"""Audio Analyzer — BPM, key, energy analysis"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    def __init__(self):
        self._cache = {}

    def analyze(self, audio_path: str) -> Dict:
        try:
            import librosa

            y, sr = librosa.load(audio_path, sr=22050)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            energy = float(librosa.feature.rms(y=y).mean())
            spectral_centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
            return {
                "bpm": round(float(tempo), 1),
                "energy": round(energy, 4),
                "spectral_centroid": round(spectral_centroid, 1),
                "duration": round(len(y) / sr, 2),
                "sample_rate": sr,
            }
        except ImportError:
            return {"error": "librosa not installed"}
        except Exception as e:
            return {"error": str(e)}
