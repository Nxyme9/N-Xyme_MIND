"""Audio processing: Voice Activity Detection (VAD) + normalization."""

import numpy as np

from nx_dictate.config import AudioConfig


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """Normalize audio to target dB level."""
    if len(audio) == 0:
        return audio

    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-10:
        return audio

    target_rms = 10 ** (target_db / 20.0)
    gain = target_rms / rms
    normalized = audio * gain
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def compute_rms(audio: np.ndarray, window_size: int = 1600) -> np.ndarray:
    """Compute RMS energy over sliding window."""
    if len(audio) == 0:
        return np.array([])

    padded = np.pad(audio ** 2, (window_size // 2, window_size // 2), mode="edge")
    cumsum = np.cumsum(padded)
    window_sum = cumsum[window_size:] - cumsum[:-window_size]
    return np.sqrt(window_sum / window_size)


def vad_split(
    audio: np.ndarray,
    config: AudioConfig,
) -> list[np.ndarray]:
    """Split audio into speech segments using VAD.

    Returns list of speech segments (silence removed).
    """
    if len(audio) == 0:
        return []

    window_size = int(config.sample_rate * config.chunk_duration)
    rms = compute_rms(audio, window_size)
    threshold = config.silence_threshold

    segments = []
    current_segment = []
    silence_counter = 0
    silence_window = int(config.silence_duration / config.chunk_duration)

    for i, energy in enumerate(rms):
        if energy > threshold:
            if silence_counter > 0 and current_segment:
                segments.append(np.concatenate(current_segment))
                current_segment = []
            silence_counter = 0
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, len(audio))
            current_segment.append(audio[start_idx:end_idx])
        else:
            silence_counter += 1
            if current_segment:
                start_idx = i * window_size
                end_idx = min((i + 1) * window_size, len(audio))
                current_segment.append(audio[start_idx:end_idx])

            if silence_counter >= silence_window and current_segment:
                segments.append(np.concatenate(current_segment))
                current_segment = []
                silence_counter = 0

    if current_segment:
        segments.append(np.concatenate(current_segment))

    return segments


def is_speech(
    audio_chunk: np.ndarray,
    threshold: float = 0.01,
) -> bool:
    """Check if audio chunk contains speech (simple energy-based VAD)."""
    if len(audio_chunk) == 0:
        return False
    rms = np.sqrt(np.mean(audio_chunk ** 2))
    return rms > threshold


def trim_silence(
    audio: np.ndarray,
    threshold: float = 0.01,
    padding_ms: int = 200,
    sample_rate: int = 16000,
) -> np.ndarray:
    """Trim leading and trailing silence, with padding."""
    if len(audio) == 0:
        return audio

    rms = np.abs(audio)
    speech_mask = rms > threshold
    speech_indices = np.where(speech_mask)[0]

    if len(speech_indices) == 0:
        return audio

    start = max(0, speech_indices[0] - int(padding_ms * sample_rate / 1000))
    end = min(len(audio), speech_indices[-1] + int(padding_ms * sample_rate / 1000))

    return audio[start:end]
