from __future__ import annotations
import numpy as np
import logging

logger = logging.getLogger("nxyme_dictate.audio_processing")


def normalize_audio(audio: np.ndarray, target_level: float = 0.5) -> np.ndarray:
    if len(audio) == 0:
        return audio
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio * (target_level / peak)
    return audio


def apply_highpass_filter(
    audio: np.ndarray, sample_rate: int = 16000, cutoff: int = 80
) -> np.ndarray:
    if len(audio) < 3:
        return audio
    alpha = cutoff / (sample_rate + cutoff)
    filtered = np.zeros_like(audio)
    filtered[0] = audio[0]
    for i in range(1, len(audio)):
        filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
    return filtered


def apply_lowpass_filter(
    audio: np.ndarray, sample_rate: int = 16000, cutoff: int = 8000
) -> np.ndarray:
    if len(audio) < 3:
        return audio
    alpha = (sample_rate - cutoff) / (sample_rate + cutoff)
    filtered = np.zeros_like(audio)
    filtered[0] = audio[0]
    for i in range(1, len(audio)):
        filtered[i] = (1 - alpha) * audio[i] + alpha * filtered[i - 1]
    return filtered


def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
    if len(audio) == 0:
        return audio
    return audio - np.mean(audio)


def apply_agc(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    if len(audio) == 0:
        return audio
    rms = np.sqrt(np.mean(audio**2))
    if rms > 0:
        current_db = 20 * np.log10(rms)
        gain_db = target_db - current_db
        gain_linear = 10 ** (gain_db / 20)
        audio = audio * gain_linear
    return audio


def preprocess_audio(
    audio: np.ndarray,
    sample_rate: int = 16000,
    normalize: bool = True,
    remove_dc: bool = True,
    highpass: bool = True,
    agc: bool = True,
) -> np.ndarray:
    if len(audio) == 0:
        return audio

    if remove_dc:
        audio = remove_dc_offset(audio)

    if highpass:
        audio = apply_highpass_filter(audio, sample_rate)

    if normalize:
        audio = normalize_audio(audio, target_level=0.5)

    if agc:
        audio = apply_agc(audio, target_db=-20.0)

    audio = np.clip(audio, -1.0, 1.0)

    return audio
