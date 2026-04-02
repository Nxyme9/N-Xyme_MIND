"""Lyric Alignment — Align lyrics to audio timing"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class LyricAlignment:
    def align(self, lyrics: List[str], timestamps: List[float]) -> List[Dict]:
        if len(lyrics) != len(timestamps):
            logger.warning(
                f"LyricAlignment: Mismatch ({len(lyrics)} lyrics, {len(timestamps)} timestamps)"
            )
            min_len = min(len(lyrics), len(timestamps))
            lyrics = lyrics[:min_len]
            timestamps = timestamps[:min_len]
        aligned = []
        for i, (text, time) in enumerate(zip(lyrics, timestamps)):
            aligned.append(
                {
                    "index": i,
                    "text": text,
                    "time": round(time, 3),
                    "duration": round(timestamps[i + 1] - time, 3)
                    if i + 1 < len(timestamps)
                    else 2.0,
                }
            )
        return aligned

    def auto_align(self, lyrics: List[str], audio_path: str) -> List[Dict]:
        try:
            from whisper_transcription import WhisperTranscription

            whisper = WhisperTranscription()
            result = whisper.transcribe(audio_path)
            segments = [{"text": s.text, "time": s.start} for s in result.segments]
            return self.align(lyrics, [s["time"] for s in segments])
        except Exception as e:
            logger.error(f"LyricAlignment: Auto-align failed: {e}")
            return []
