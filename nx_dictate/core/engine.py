# N-Xyme Dictate - Engine Wrapper
# Uses existing nx_engine whisper integration + local GGML support

from __future__ import annotations

import ctypes
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np

logger = logging.getLogger("nxyme_dictate.dictate.engine")

# Local GGML models directory
LOCAL_GGML_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/whisper")

# Check if pywhispercpp is available for local GGML models
PYWHISPERCPP_AVAILABLE = False
try:
    import pywhispercpp
    PYWHISPERCPP_AVAILABLE = True
    logger.info("pywhispercpp available - will use local GGML models")
except ImportError:
    logger.info("pywhispercpp not available - using faster-whisper")

if TYPE_CHECKING:
    from nx_engine.engine.whisper import WhisperClient as _WhisperClient

# =============================================================================
# CUDA + cuBLAS Compatibility Setup - Must happen BEFORE ctranslate2 import!
# =============================================================================
# CTranslate2 (faster-whisper backend) is compiled against cuBLAS 12,
# but systems with CUDA 13+ only have cuBLAS 13. We preload cuBLAS 13
# with RTLD_GLOBAL so ctranslate2 can find it.

_CUBLAS_PRELOAD_DONE = False


def _setup_cublas_preload() -> bool:
    """Preload cuBLAS 13 with RTLD_GLOBAL for ctranslate2 compatibility.

    ctranslate2 dynamically loads cuBLAS at runtime. We preload cuBLAS 13
    with RTLD_GLOBAL before ctranslate2 imports, so symbol resolution works.
    """
    cuda_paths = [
        "/opt/cuda/lib64",
        "/usr/local/cuda/lib64",
        os.path.expanduser("~/cuda/lib64"),
    ]

    # cuBLAS versions
    needed = ["libcublas.so.12", "libcublas.so.11"]
    available = ["libcublas.so.13", "libcublas.so.12.0.0", "libcublas.so"]

    for path in cuda_paths:
        if not os.path.exists(path):
            continue

        # Check if cuBLAS 12 is available (no patch needed)
        for lib in needed:
            lib_path = os.path.join(path, lib)
            if os.path.exists(lib_path):
                try:
                    ctypes.CDLL(lib_path)  # Test loading
                    return True  # Works directly
                except OSError:
                    pass

        # Try to preload cuBLAS 13 as cuBLAS 12
        for lib in available:
            lib_path = os.path.join(path, lib)
            if os.path.exists(lib_path):
                try:
                    # RTLD_GLOBAL | RTLD_NOW = 256 | 2
                    ctypes.CDLL(lib_path, mode=256 | 2)
                    logger.info(f"cuBLAS preload: {lib_path}")
                    return True
                except OSError:
                    pass

    return False


# Apply BEFORE importing whisper
_CUBLAS_PRELOAD_DONE = _setup_cublas_preload()

# noqa: E402 - Must be after cuBLAS preload setup
from nx_engine.engine.whisper import WhisperClient as _WhisperClient  # type: ignore[misc]

# Model configurations
WHISPER_MODELS = {
    "tiny": {"params": "39M", "vram_gb": 1, "rtf": 10},
    "base": {"params": "74M", "vram_gb": 1, "rtf": 7},
    "small": {"params": "244M", "vram_gb": 2, "rtf": 4},
    "medium": {"params": "769M", "vram_gb": 5, "rtf": 2},
    "large-v3-turbo": {"params": "809M", "vram_gb": 6, "rtf": 3},
}

DEFAULT_MODEL = "large-v3-turbo"


def find_local_ggml_model(model_name: str) -> Optional[Path]:
    """Find local GGML model matching the requested model name.
    
    Looks in LOCAL_GGML_DIR for ggml-*.bin files and matches to model names.
    """
    if not PYWHISPERCPP_AVAILABLE:
        return None
        
    if not LOCAL_GGML_DIR.exists():
        logger.debug(f"Local GGML dir not found: {LOCAL_GGML_DIR}")
        return None
    
    # Map model names to GGML files
    model_map = {
        "tiny": "ggml-tiny.bin",
        "base": "ggml-base.bin", 
        "small": "ggml-small.bin",
        "medium": "ggml-medium.bin",
        "large-v3-turbo": "ggml-large-v3-turbo.bin",
        "large-v3": "ggml-large-v3.bin",
    }
    
    ggml_file = model_map.get(model_name)
    if not ggml_file:
        return None
    
    model_path = LOCAL_GGML_DIR / ggml_file
    if model_path.exists():
        logger.info(f"Found local GGML model: {model_path}")
        return model_path
    
    return None


@dataclass
class DictationConfig:
    model: str = DEFAULT_MODEL
    device: str = "auto"
    compute_type: str = "float16"
    language: Optional[str] = None
    beam_size: int = 1
    temperature: float = 0.2
    compression_ratio_threshold: float = 2.0
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.9
    initial_prompt: Optional[str] = None
    vocabulary: Optional[list[str]] = None
    languages: Optional[list[str]] = None


SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
}


def get_gpu_vram_gb() -> float:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / 1e9
    except Exception:
        pass
    return 0.0


def get_available_vram_gb() -> float:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.mem_get_info()[0] / 1e9
    except Exception:
        pass
    return 0.0


def check_cuda_available() -> bool:
    """Check if CUDA is available."""
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def check_cublas_available() -> bool:
    """Check if cuBLAS is available (required for GPU compute)."""
    # Common cuBLAS library names
    cublas_libs = [
        "libcublas.so.12",
        "libcublas.so.11",
        "libcublas.so",
    ]

    for lib in cublas_libs:
        try:
            ctypes.CDLL(lib)
            return True
        except OSError:
            continue
    return False


def auto_select_model(vram_gb: Optional[float] = None, headroom_gb: float = 2.0) -> str:
    if vram_gb is None:
        vram_gb = get_available_vram_gb()

    usable = vram_gb - headroom_gb

    if usable >= 8:
        return "large-v3-turbo"
    elif usable >= 4:
        return "medium"
    elif usable >= 2:
        return "small"
    elif usable >= 1:
        return "base"
    else:
        return "tiny"


class DictationEngine:
    """Dictation engine using existing nx_engine whisper."""

    def __init__(self, config: Optional[DictationConfig] = None):
        self._config = config or DictationConfig()
        self._client: Optional[_WhisperClient] = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_name(self) -> str:
        return self._config.model

    def load(self) -> bool:
        if self._loaded:
            return True

        device = self._config.device
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        compute_type = self._config.compute_type

        # Only use GGML if no GPU available - faster-whisper is much faster with GPU
        if PYWHISPERCPP_AVAILABLE and device == "cpu":
            ggml_path = find_local_ggml_model(self._config.model)
            if ggml_path:
                try:
                    logger.info(f"Loading LOCAL GGML (CPU mode): {ggml_path}")
                    from pywhispercpp.model import Model
                    self._ggml_client = Model(str(ggml_path))
                    self._loaded = True
                    self._using_ggml = True
                    self._resolved_device = "cpu"
                    logger.info(f"GGML model loaded: {self._config.model}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load GGML: {e}, falling back to faster-whisper")

        try:
            logger.info(f"Loading whisper: {self._config.model} on {device}")

            # GPU load failed? Try CPU fallback
            if device == "cuda" and hasattr(self, '_gpu_failed'):
                logger.warning("GPU failed, retrying with CPU")
                device = "cpu"
                compute_type = "int8"
                self._config.compute_type = compute_type

            language = self._config.language
            if language == "auto" or language is None:
                language = None

            from faster_whisper import WhisperModel
            self._client = WhisperModel(
                self._config.model,
                device=device,
                compute_type=compute_type,
            )
            self._loaded = True
            self._using_ggml = False
            self._resolved_device = device
            logger.info(f"Model loaded: {self._config.model}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def transcribe(
        self,
        audio: np.ndarray,
    ) -> str:
        if not self._loaded:
            if not self.load():
                return "[Failed to load model]"

        # Handle GGML (local) transcription
        if getattr(self, "_using_ggml", False) and hasattr(self, "_ggml_client"):
            try:
                # GGML/Whisper.cpp uses int16 PCM at 16kHz
                audio_int16 = (audio * 32767).astype("int16")
                segments = self._ggml_client.transcribe(audio_int16)
                text = "".join([seg.text for seg in segments])
                return text
            except Exception as e:
                logger.error(f"GGML transcription failed: {e}")
                return f"[GGML Error: {e}]"

        # Standard faster-whisper transcription
        try:
            prompt = self._config.initial_prompt
            if self._config.vocabulary:
                prompt = (prompt + " " if prompt else "") + " ".join(
                    self._config.vocabulary
                )

            result = self._client.transcribe(
                audio,
                initial_prompt=prompt,
                beam_size=self._config.beam_size,
                vad_filter=False,
            )
            if isinstance(result, tuple) and len(result) >= 1:
                segments = result[0]
                if hasattr(segments, '__iter__'):
                    return "".join([getattr(s, 'text', str(s)) for s in segments])
            if hasattr(result, 'text'):
                return result.text
            if hasattr(result, '__iter__') and not isinstance(result, str):
                return "".join([getattr(r, 'text', str(r)) for r in result])
            return str(result)
        except Exception as e:
            error_str = str(e).lower()

            # Detect GPU failure - retry with CPU
            if ("cuda" in error_str or "gpu" in error_str) and getattr(self, '_resolved_device', '') == 'cuda':
                if not getattr(self, '_cpu_fallback_done', False):
                    logger.warning(f"GPU error: {e} - falling back to CPU")
                    self._cpu_fallback_done = True
                    self._resolved_device = 'cpu'
                    return self.transcribe(audio)

            if (
                "cublas" in error_str or "cuda" in error_str
            ) and self._resolved_device == "cuda":
                if not getattr(self, "_cpu_fallback_done", False):
                    logger.warning(f"GPU error: {e} - retrying with CPU...")
                    self._cpu_fallback_done = True
                    self._reinit_cpu()
                    return self.transcribe(audio)

            logger.error(f"Transcription failed: {e}")
            return f"[Error: {e}]"

    def transcribe_streaming(
        self,
        audio_chunks: list[np.ndarray],
    ) -> str:
        if not audio_chunks:
            return ""

        combined = np.concatenate(audio_chunks)
        return self.transcribe(combined)

    def _reinit_cpu(self) -> None:
        """Reinitialize the engine in CPU mode."""
        logger.info("Reinitializing whisper engine in CPU mode...")
        self._client = None
        self._loaded = False
        language = self._config.language
        if language == "auto" or language is None:
            language = None

        self._client = _WhisperClient(
            model=self._config.model,
            device="cpu",
            compute_type="int8",
            language=language,
        )
        self._loaded = True
        logger.info("CPU mode engine ready")

    def unload(self) -> None:
        """Unload model."""
        self._client = None
        self._loaded = False
        logger.info("Model unloaded")


# Singleton for convenience
_engine: Optional[DictationEngine] = None


def get_engine(config: Optional[DictationConfig] = None) -> DictationEngine:
    """Get or create dictation engine."""
    global _engine
    if _engine is None:
        _engine = DictationEngine(config)
    return _engine
