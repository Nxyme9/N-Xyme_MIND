from __future__ import annotations
import logging
import threading
import time
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger("nxyme_dictate.hotword")

POCKETSPHINX_AVAILABLE = False
try:
    import importlib.util

    if importlib.util.find_spec("pocketsphinx"):
        POCKETSPHINX_AVAILABLE = True
except ImportError:
    pass


class HotwordDetector:
    def __init__(
        self,
        keywords: list[str] = ["hey computer", "okay google"],
        threshold: float = 1e-40,
        sample_rate: int = 16000,
    ):
        self._keywords = keywords
        self._threshold = threshold
        self._sample_rate = sample_rate
        self._decoder = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_detected: Optional[Callable[[str], None]] = None
        self._last_detection_time = 0.0
        self._cooldown_seconds = 2.0
        self._initialized = False
        self._init_pocketsphinx()

    def _init_pocketsphinx(self):
        if not POCKETSPHINX_AVAILABLE:
            logger.warning("PocketSphinx not available, using energy-based fallback")
            return

        try:
            from pocketsphinx import Decoder

            kws_str = " | ".join(self._keywords)
            config = {
                "kws": kws_str,
                "threshold": self._threshold,
            }
            self._decoder = Decoder(**config)
            self._initialized = True
            logger.info(f"Hotword detector initialized with keywords: {self._keywords}")
        except Exception as e:
            logger.warning(f"Failed to init PocketSphinx: {e}")
            self._initialized = False

    def set_callback(self, callback: Callable[[str], None]):
        self._on_detected = callback

    def start(self, audio_callback: Callable[[np.ndarray], None]) -> bool:
        if self._running:
            return True
        self._running = True
        self._audio_callback = audio_callback
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info("Hotword detector started")
        return True

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Hotword detector stopped")

    def _detection_loop(self):
        buffer_size = self._sample_rate * 3
        audio_buffer = np.zeros(buffer_size, dtype=np.float32)
        buffer_index = 0

        while self._running:
            try:
                chunk = self._audio_callback()
                if chunk is None or len(chunk) == 0:
                    time.sleep(0.05)
                    continue

                available = buffer_size - buffer_index
                if len(chunk) > available:
                    audio_buffer = np.roll(audio_buffer, -len(chunk))
                    audio_buffer[-len(chunk) :] = chunk
                    buffer_index = buffer_size
                else:
                    audio_buffer[buffer_index : buffer_index + len(chunk)] = chunk
                    buffer_index += len(chunk)

                if buffer_index >= buffer_size:
                    buffer_index = 0

                    if self._initialized and self._decoder:
                        self._pocketsphinx_detect(audio_buffer)
                    else:
                        self._energy_detect(audio_buffer)

            except Exception as e:
                logger.error(f"Hotword detection error: {e}")
                time.sleep(0.1)

    def _pocketsphinx_detect(self, audio: np.ndarray):
        pcm_int16 = (audio * 32767).astype(np.int16)
        self._decoder.process_raw(pcm_int16.tobytes(), False, False)

        if self._decoder.hyp():
            hyp_str = self._decoder.hyp().hypstr
            now = time.time()
            if now - self._last_detection_time > self._cooldown_seconds:
                self._last_detection_time = now
                logger.info(f"Hotword detected: {hyp_str}")
                if self._on_detected:
                    self._on_detected(hyp_str)

    def _energy_detect(self, audio: np.ndarray):
        rms = np.sqrt(np.mean(audio**2))
        if rms > 0.15:
            now = time.time()
            if now - self._last_detection_time > self._cooldown_seconds:
                self._last_detection_time = now
                logger.info(f"Hotword energy spike detected: {rms:.3f}")
                if self._on_detected:
                    self._on_detected("energy_spike")

    def is_running(self) -> bool:
        return self._running


def create_hotword_detector(
    keywords: list[str] = None,
    on_detected: Callable[[str], None] = None,
) -> Optional[HotwordDetector]:
    if keywords is None:
        keywords = ["hey computer", "okay computer", "hey nxyme"]

    detector = HotwordDetector(keywords=keywords)
    if on_detected:
        detector.set_callback(on_detected)
    return detector
