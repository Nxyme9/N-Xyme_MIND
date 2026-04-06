"""Spectrum Analyzer — Frequency spectrum analysis"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SpectrumAnalyzer:
    def analyze(self, audio_path: str, num_bands: int = 10) -> Dict:
        try:
            import numpy as np
            import librosa

            y, sr = librosa.load(audio_path, sr=22050)
            S = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            band_edges = np.logspace(np.log10(20), np.log10(sr / 2), num_bands + 1)
            bands = []
            for i in range(num_bands):
                mask = (freqs >= band_edges[i]) & (freqs < band_edges[i + 1])
                energy = float(S[mask].mean()) if mask.any() else 0
                bands.append(
                    {
                        "low_hz": round(band_edges[i], 0),
                        "high_hz": round(band_edges[i + 1], 0),
                        "energy": round(energy, 4),
                    }
                )
            return {"bands": bands, "sample_rate": sr, "total_energy": round(float(S.mean()), 4)}
        except ImportError:
            return {"error": "librosa/numpy not installed"}
