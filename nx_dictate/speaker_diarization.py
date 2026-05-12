from __future__ import annotations
import logging

logger = logging.getLogger("nxyme_dictate.punctuation")

PYANNOTE_AVAILABLE = False
try:
    from pyannote.audio import Pipeline

    PYANNOTE_AVAILABLE = True
except ImportError:
    pass


class SpeakerDiarizer:
    def __init__(self, min_speakers: int = 1, max_speakers: int = 4):
        self._min_speakers = min_speakers
        self._max_speakers = max_speakers
        self._pipeline = None
        self._initialized = False
        self._init_diarizer()

    def _init_diarizer(self):
        if not PYANNOTE_AVAILABLE:
            logger.warning("PyAnnote not available, speaker diarization disabled")
            return

        try:
            from huggingface_hub import hf_hub_download

            config_path = hf_hub_download(
                repo_id="pyannote/speaker-diarization-3.0",
                filename="config.yaml",
            )
            self._pipeline = Pipeline.from_pretrained(config_path)
            self._initialized = True
            logger.info("Speaker diarization initialized")
        except Exception as e:
            logger.warning(f"Failed to init diarization: {e}")

    def diarize(self, audio_path: str) -> list[dict]:
        if not self._initialized:
            return []

        try:
            diarization = self._pipeline(audio_path)
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(
                    {
                        "speaker": speaker,
                        "start": turn.start,
                        "end": turn.end,
                    }
                )
            return segments
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []

    def is_available(self) -> bool:
        return self._initialized


class PunctuationEnhancer:
    def __init__(self, model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"):
        self._model_name = model_name
        self._pipeline = None
        self._initialized = False

    def initialize(self):
        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "text2text-generation",
                model=self._model_name,
                device="cuda",
            )
            self._initialized = True
            logger.info(f"Punctuation enhancer initialized: {self._model_name}")
        except Exception as e:
            logger.warning(f"Punctuation enhancer init failed: {e}")

    def enhance(self, text: str) -> str:
        if not self._initialized or not text:
            return text

        if text.endswith((".", "!", "?")):
            return text

        try:
            prompt = f"Add proper punctuation to this text: {text}"
            result = self._pipeline(prompt, max_new_tokens=50)
            if result and result[0].get("generated_text"):
                return result[0]["generated_text"]
        except Exception as e:
            logger.debug(f"Punctuation enhancement failed: {e}")

        return text


def create_diarizer(min_speakers: int = 1, max_speakers: int = 4) -> SpeakerDiarizer:
    return SpeakerDiarizer(min_speakers, max_speakers)


def create_punctuation_enhancer(model_name: str = None) -> PunctuationEnhancer:
    return PunctuationEnhancer(model_name or "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
