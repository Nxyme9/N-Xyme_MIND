"""Subtitle Generator — Create SRT/VTT subtitles"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    def generate_srt(self, segments: List[Dict]) -> str:
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
        return "\n".join(lines)

    def generate_vtt(self, segments: List[Dict]) -> str:
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            lines.append(f"{start} --> {end}\n{seg['text']}\n")
        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
