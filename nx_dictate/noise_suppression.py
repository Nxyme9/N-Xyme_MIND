from __future__ import annotations
import logging
import numpy as np

logger = logging.getLogger("nxyme_dictate.noise_suppression")

RNNOISE_AVAILABLE = False
_rnnoise = None


def _try_import_rnnoise():
    global RNNOISE_AVAILABLE, _rnnoise
    if RNNOISE_AVAILABLE:
        return True
    try:
        import rnnoise

        _rnnoise = rnnoise
        RNNOISE_AVAILABLE = True
        logger.info("RNNoise loaded successfully")
        return True
    except ImportError:
        logger.debug("RNNoise not available, using spectral subtraction")
        return False


class NoiseSuppressor:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._rnnoise = None
        self._using_rnnoise = _try_import_rnnoise()
        if self._using_rnnoise:
            try:
                self._rnnoise = _rnnoise.Denoiser(frame_size=480)
            except Exception as e:
                logger.warning(f"RNNoise init failed: {e}, using fallback")
                self._using_rnnoise = False

    def suppress(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio

        if self._using_rnnoise and self._rnnoise:
            try:
                return self._rnnoise.process(audio)
            except Exception as e:
                logger.warning(f"RNNoise processing failed: {e}")

        return self._spectral_subtraction(audio)

    def _spectral_subtraction(self, audio: np.ndarray) -> np.ndarray:
        frame_size = 512
        hop_size = 256
        noise_estimate_frames = 10

        padded = np.zeros(len(audio) + frame_size)
        padded[: len(audio)] = audio

        noise_profile = np.zeros(frame_size // 2 + 1)
        frame_count = 0

        for start in range(0, len(padded) - frame_size, hop_size):
            frame = padded[start : start + frame_size]
            windowed = frame * np.hanning(frame_size)
            spectrum = np.fft.rfft(windowed)
            magnitude = np.abs(spectrum)

            if frame_count < noise_estimate_frames:
                noise_profile = 0.9 * noise_profile + 0.1 * magnitude
                frame_count += 1

            cleaned = np.maximum(magnitude - noise_profile * 1.5, 0.01)
            cleaned_spectrum = cleaned * np.exp(1j * np.angle(spectrum))
            cleaned_frame = np.fft.irfft(cleaned_spectrum)
            padded[start : start + frame_size] += cleaned_frame * 0.5

        result = padded[: len(audio)]
        return np.clip(result, -1.0, 1.0).astype(np.float32)


def create_noise_suppressor(sample_rate: int = 16000) -> NoiseSuppressor:
    return NoiseSuppressor(sample_rate)
