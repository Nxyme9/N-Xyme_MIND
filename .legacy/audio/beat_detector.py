"""Beat Detector — BPM detection algorithm"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class BeatDetector:
    def detect(self, audio_path: str) -> Dict:
        try:
            import librosa

            y, sr = librosa.load(audio_path, sr=22050)
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            return {
                "bpm": round(float(tempo), 1),
                "beat_count": len(beat_times),
                "beat_times": beat_times.tolist()[:20],
                "avg_beat_interval": round(float(beat_times[1] - beat_times[0]), 3)
                if len(beat_times) > 1
                else 0,
            }
        except ImportError:
            return {"error": "librosa not installed"}
