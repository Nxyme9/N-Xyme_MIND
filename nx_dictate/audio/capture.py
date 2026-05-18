"""Audio capture using sounddevice."""

import queue
from typing import Optional

import numpy as np
import sounddevice as sd

from nx_dictate.config import AudioConfig


class AudioCapture:
    """Captures audio from microphone using sounddevice."""

    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._running = False

    @property
    def device_index(self) -> Optional[int]:
        return self.config.device_index

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = sd.query_devices()
        inputs = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                inputs.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return inputs

    def start(self) -> None:
        """Start audio capture stream."""
        self._queue = queue.Queue()
        self._running = True
        chunk_size = int(self.config.sample_rate * self.config.chunk_duration)

        self._stream = sd.InputStream(
            device=self.config.device_index,
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            blocksize=chunk_size,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop audio capture stream."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get next audio chunk from queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Sounddevice callback — pushes chunks to queue."""
        if status:
            pass
        if self._running:
            audio_data = indata.copy().flatten()
            self._queue.put(audio_data)

    def get_full_recording(self) -> np.ndarray:
        """Get all buffered audio as single array."""
        chunks = []
        while True:
            chunk = self.get_chunk(timeout=0.1)
            if chunk is None:
                break
            chunks.append(chunk)
        if chunks:
            return np.concatenate(chunks)
        return np.array([], dtype=np.float32)
