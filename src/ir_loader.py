"""IR Loader — Load impulse responses for convolution reverb"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class IRLoader:
    def __init__(self, ir_dir: str = "data/impulse_responses"):
        self.ir_dir = Path(ir_dir)
        self.ir_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[float]] = {}

    def load(self, ir_name: str) -> Optional[List[float]]:
        if ir_name in self._cache:
            return self._cache[ir_name]
        path = self.ir_dir / ir_name
        if not path.exists():
            for ext in [".wav", ".flac", ".mp3"]:
                path = self.ir_dir / f"{ir_name}{ext}"
                if path.exists():
                    break
        if not path.exists():
            logger.error(f"IRLoader: {ir_name} not found")
            return None
        try:
            import soundfile as sf

            data, sr = sf.read(str(path))
            if len(data.shape) > 1:
                data = data[:, 0]
            self._cache[ir_name] = data.tolist()
            return self._cache[ir_name]
        except Exception as e:
            logger.error(f"IRLoader: Failed to load: {e}")
            return None

    def list_irs(self) -> List[str]:
        return [f.name for f in self.ir_dir.glob("*") if f.suffix in (".wav", ".flac", ".mp3")]

    def convolve(self, audio: List[float], ir_name: str) -> List[float]:
        try:
            import numpy as np

            ir = self.load(ir_name)
            if ir is None:
                return audio
            return np.convolve(audio, ir)[: len(audio)].tolist()
        except ImportError:
            return audio
