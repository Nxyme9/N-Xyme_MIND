"""Pitch Detector — Detect pitch for autotune"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class PitchDetector:
    def detect(self, audio_path: str) -> Dict:
        try:
            import librosa

            y, sr = librosa.load(audio_path, sr=22050)
            f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=50, fmax=2000, sr=sr)
            pitches = []
            for i, (freq, prob) in enumerate(zip(f0, voiced_probs)):
                if freq and prob > 0.5:
                    note_num = 12 * (librosa.hz_to_midi(freq) / 12)
                    note_idx = int(note_num) % 12
                    octave = int(note_num / 12)
                    pitches.append(
                        {
                            "time": round(i * 512 / sr, 3),
                            "freq": round(float(freq), 1),
                            "note": NOTES[note_idx],
                            "octave": octave,
                            "confidence": round(float(prob), 3),
                        }
                    )
            return {"pitches": pitches[:100], "total": len(pitches)}
        except ImportError:
            return {"error": "librosa not installed"}
