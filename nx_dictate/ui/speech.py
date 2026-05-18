"""Edge TTS voice feedback — speaks status changes aloud.

Ported from CATALYST jarvis/engine/mouth.py pattern.
Free, no API key, British male voice (Jarvis-like).
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import threading

logger = logging.getLogger(__name__)

_VOICE = "en-GB-RyanNeural"  # British male, Jarvis-like
_RATE = "+0%"
_VOLUME = "+0%"


def _speak(text: str) -> None:
    """Fire-and-forget TTS using Edge TTS. Saves to temp file, plays via paplay."""
    try:
        import edge_tts

        async def _gen_audio() -> str:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await edge_tts.Communicate(text, _VOICE, rate=_RATE, volume=_VOLUME).save(tmp_path)
            return tmp_path

        tmp_path = asyncio.run(_gen_audio())
        try:
            subprocess.run(
                ["paplay", tmp_path],
                capture_output=True,
                timeout=10,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        logger.debug("TTS unavailable: %s", e)


def say(text: str) -> None:
    """Thread-safe, fire-and-forget TTS. Returns immediately."""
    threading.Thread(target=_speak, args=(text,), daemon=True).start()


# Status phrases for voice feedback
PHRASES = {
    "ready": "Ready",
    "listening": "Listening",
    "processing": "Processing",
    "injected": "Done",
    "error": "Error",
    "wake": "Yes?",
    "sleep": "Sleeping",
    "sending": "Sending",
    "routed": "Thinking",
}
