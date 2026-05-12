from __future__ import annotations
import asyncio
import logging
import tempfile
import os

logger = logging.getLogger("nxyme_dictate.tts")

EDGE_TTS_AVAILABLE = False
try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass


class AudioFeedback:
    def __init__(self, voice: str = "en-US-AriaNeural"):
        self._voice = voice
        self._communicate = None

    async def _speak_async(self, text: str) -> bool:
        if not EDGE_TTS_AVAILABLE:
            return False
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            comm = edge_tts.Communicate(text, self._voice)
            await comm.save(tmp_path)
            for cmd in ["paplay", "aplay", "ffplay"]:
                if os.path.exists(tmp_path):
                    try:
                        import subprocess

                        proc = subprocess.Popen(
                            [cmd, tmp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        proc.wait(timeout=5)
                        os.unlink(tmp_path)
                        return True
                    except Exception:
                        pass
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    def speak(self, text: str) -> bool:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._speak_async(text))
                return True
            else:
                return loop.run_until_complete(self._speak_async(text))
        except Exception:
            return False


_AUDIO_FEEDBACK = None


def get_audio_feedback(voice: str = "en-US-AriaNeural") -> AudioFeedback:
    global _AUDIO_FEEDBACK
    if _AUDIO_FEEDBACK is None:
        _AUDIO_FEEDBACK = AudioFeedback(voice)
    return _AUDIO_FEEDBACK
