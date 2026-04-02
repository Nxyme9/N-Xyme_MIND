"""Key Detector — Musical key detection"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class KeyDetector:
    def detect(self, audio_path: str) -> Dict:
        try:
            import librosa

            y, sr = librosa.load(audio_path, sr=22050)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            key_idx = int(chroma.mean(axis=1).argmax())
            mode = (
                "major" if chroma[key_idx].mean() > chroma[(key_idx + 3) % 12].mean() else "minor"
            )
            return {
                "key": KEYS[key_idx],
                "mode": mode,
                "confidence": round(float(chroma[key_idx].mean()), 3),
                "full_key": f"{KEYS[key_idx]} {mode}",
            }
        except ImportError:
            return {"error": "librosa not installed"}
