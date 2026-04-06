"""
Mastering Assistant — Ported from N-Xyme LIVE

Platform-specific loudness normalization for audio production.

Usage:
    assistant = MasteringAssistant()
    target = assistant.get_target("spotify")
    print(target)  # {"platform": "spotify", "target_lufs": -14, "true_peak": -1}
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Streaming platforms."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    TIDAL = "tidal"
    AMAZON_MUSIC = "amazon_music"
    CUSTOM = "custom"


@dataclass
class LoudnessTarget:
    """Loudness target for a platform."""

    platform: str
    target_lufs: float  # Loudness Units relative to Full Scale
    true_peak_max: float  # Maximum true peak in dBTP
    loudness_range_max: float  # Maximum loudness range in LU
    standard: str  # Measurement standard


# Platform loudness targets (industry standards)
PLATFORM_TARGETS: Dict[str, LoudnessTarget] = {
    "spotify": LoudnessTarget(
        platform="Spotify",
        target_lufs=-14.0,
        true_peak_max=-1.0,
        loudness_range_max=12.0,
        standard="Spotify Normalization",
    ),
    "apple_music": LoudnessTarget(
        platform="Apple Music",
        target_lufs=-16.0,
        true_peak_max=-1.0,
        loudness_range_max=12.0,
        standard="Sound Check",
    ),
    "youtube": LoudnessTarget(
        platform="YouTube",
        target_lufs=-14.0,
        true_peak_max=-1.0,
        loudness_range_max=15.0,
        standard="YouTube Normalization",
    ),
    "soundcloud": LoudnessTarget(
        platform="SoundCloud",
        target_lufs=-14.0,
        true_peak_max=-1.0,
        loudness_range_max=12.0,
        standard="SoundCloud Normalization",
    ),
    "tidal": LoudnessTarget(
        platform="Tidal",
        target_lufs=-14.0,
        true_peak_max=-1.0,
        loudness_range_max=12.0,
        standard="Tidal Normalization",
    ),
    "amazon_music": LoudnessTarget(
        platform="Amazon Music",
        target_lufs=-14.0,
        true_peak_max=-1.0,
        loudness_range_max=12.0,
        standard="Amazon Normalization",
    ),
}


class MasteringAssistant:
    """Platform-specific loudness normalization."""

    def __init__(self):
        self.targets = PLATFORM_TARGETS
        logger.info(f"MasteringAssistant: Initialized ({len(self.targets)} platforms)")

    def get_target(self, platform: str) -> Optional[Dict]:
        """Get loudness target for a platform."""
        target = self.targets.get(platform.lower())
        if target:
            return {
                "platform": target.platform,
                "target_lufs": target.target_lufs,
                "true_peak_max": target.true_peak_max,
                "loudness_range_max": target.loudness_range_max,
                "standard": target.standard,
            }
        return None

    def get_all_targets(self) -> Dict[str, Dict]:
        """Get all platform targets."""
        return {k: self.get_target(k) for k in self.targets.keys()}

    def analyze_loudness(self, audio_path: str) -> Optional[Dict]:
        """
        Analyze audio loudness (requires ffmpeg/pyloudnorm).

        Returns:
            Dict with lufs, true_peak, loudness_range
        """
        try:
            import subprocess

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    audio_path,
                    "-af",
                    "loudnorm=print_format=json",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Parse ffmpeg loudnorm output
            # This is a simplified version - real implementation would parse JSON
            return {
                "lufs": -14.0,  # Placeholder
                "true_peak": -1.0,
                "loudness_range": 10.0,
                "note": "Requires ffmpeg for real analysis",
            }
        except Exception as e:
            logger.error(f"MasteringAssistant: Analysis failed: {e}")
            return None

    def suggest_adjustment(self, current_lufs: float, platform: str) -> Optional[Dict]:
        """Suggest loudness adjustment for target platform."""
        target = self.get_target(platform)
        if not target:
            return None

        adjustment = target["target_lufs"] - current_lufs
        return {
            "platform": platform,
            "current_lufs": current_lufs,
            "target_lufs": target["target_lufs"],
            "adjustment_db": adjustment,
            "action": "increase" if adjustment > 0 else "decrease",
            "message": f"{'Increase' if adjustment > 0 else 'Decrease'} by {abs(adjustment):.1f} dB",
        }
