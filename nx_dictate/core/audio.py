# N-Xyme Dictate - Audio Pipeline
# Integrated with existing nx_engine whisper

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger("nxyme_dictate.dictate.audio")

# Try to import TEN VAD for better performance
TEN_VAD_AVAILABLE = False
try:
    import ten_vad

    TEN_VAD_AVAILABLE = True
    logger.info("TEN VAD available for lower latency voice detection")
except ImportError:
    pass

# Try to import fast-vad for ultra-fast VAD
FAST_VAD_AVAILABLE = False
try:
    import fast_vad

    FAST_VAD_AVAILABLE = True
    logger.info("fast-vad available (721x realtime, Rust-powered)")
except ImportError:
    pass

# Try to import FireRedVAD (97.57% F1 SOTA)
FIRERED_VAD_AVAILABLE = False
try:
    import fireredvad

    FIRERED_VAD_AVAILABLE = True
    logger.info("FireRedVAD available (97.57% F1 SOTA)")
except ImportError:
    pass

SAMPLE_RATE: int = 16000
CHANNELS: int = 1
DTYPE: str = "float32"


@dataclass
class AudioConfig:
    """Audio pipeline configuration."""

    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    dtype: str = DTYPE
    chunk_seconds: float = 0.5
    max_recording_seconds: int = 60
    device_index: Optional[int] = None
    noise_gate: float = 0.001
    noise_reduction: bool = True
    enable_agc: bool = True


class RingBuffer:
    """Thread-safe ring buffer for audio capture."""

    def __init__(self, max_samples: int):
        self._buffer = np.zeros(max_samples, dtype=np.float32)
        self._index = 0
        self._lock = threading.Lock()
        self._max_samples = max_samples
        self._filled = 0
        self._overflowed = False

    def write(self, data: np.ndarray) -> None:
        with self._lock:
            available = self._max_samples - self._filled
            if len(data) > available:
                self._buffer = np.roll(self._buffer, -len(data))
                self._buffer[-len(data) :] = data
                self._filled = self._max_samples
                self._overflowed = True
            else:
                start = self._filled
                self._buffer[start : start + len(data)] = data
                self._filled += len(data)

    def read(self, samples: Optional[int] = None) -> np.ndarray:
        with self._lock:
            if samples is None or samples >= self._filled:
                return self._buffer[: self._filled].copy()
            return self._buffer[self._filled - samples : self._filled].copy()

    def clear(self) -> None:
        with self._lock:
            self._buffer.fill(0)
            self._filled = 0

    @property
    def filled_samples(self) -> int:
        with self._lock:
            return self._filled

    @property
    def is_overflowed(self) -> bool:
        with self._lock:
            return self._overflowed


def apply_noise_gate(audio: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """True energy-based noise gate: silence below threshold, pass through above."""
    if len(audio) == 0:
        return audio
    rms = np.sqrt(np.mean(audio**2))
    if rms < threshold:
        return np.zeros_like(audio)
    return audio


class EnergyVAD:
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.02,
        min_speech_duration: float = 0.2,
        min_silence_duration: float = 0.5,
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_samples = int(min_speech_duration * sample_rate)
        self.min_silence_samples = int(min_silence_duration * sample_rate)
        self._speech_buffer = []
        self._speech_started = False
        self._silence_count = 0

    def is_speech(self, audio: np.ndarray) -> bool:
        if len(audio) == 0:
            return False
        rms = np.sqrt(np.mean(audio**2))
        return rms > self.threshold

    def process(self, audio: np.ndarray) -> list[tuple[int, int]]:
        results = []
        if len(audio) == 0:
            return results

        is_speech = self.is_speech(audio)
        chunk_samples = len(audio)

        if is_speech:
            self._speech_buffer.append(audio)
            self._silence_count = 0
            if not self._speech_started:
                self._speech_started = True
        else:
            self._silence_count += chunk_samples
            if self._speech_started and self._silence_count >= self.min_silence_samples:
                if self._speech_buffer:
                    total_samples = sum(len(chunk) for chunk in self._speech_buffer)
                    if total_samples >= self.min_speech_samples:
                        results.append((0, total_samples))
                    self._speech_buffer = []
                self._speech_started = False
                self._silence_count = 0

        return results

    def reset(self) -> None:
        self._speech_buffer = []
        self._speech_started = False
        self._silence_count = 0

    def get_current_speech_length(self) -> int:
        return sum(len(chunk) for chunk in self._speech_buffer)


class FastVADWrapper:
    def __init__(self, sample_rate: int = 16000, mode: int = None):
        self.sample_rate = sample_rate
        if FAST_VAD_AVAILABLE:
            if mode is None:
                self._vad = fast_vad.VAD(sample_rate)
            else:
                self._vad = fast_vad.VAD.with_config(
                    sample_rate,
                    mode=mode,
                    threshold_probability=0.7,
                    min_speech_ms=100,
                    min_silence_ms=300,
                )
            self._vad_streaming = fast_vad.VadStateful(sample_rate)
        else:
            self._vad = None
            self._vad_streaming = None

    def is_speech(self, audio: np.ndarray) -> bool:
        if not self._vad:
            return False
        if len(audio) < 512:
            return False
        try:
            return bool(self._vad(audio))
        except Exception:
            return False

    def is_speech_streaming(self, frame: np.ndarray) -> bool:
        if not self._vad_streaming:
            return False
        if len(frame) < 512:
            return False
        try:
            return bool(self._vad_streaming.process_frame(frame))
        except Exception:
            return False

    def reset(self) -> None:
        if self._vad_streaming:
            self._vad_streaming.reset_state()

    @property
    def available(self) -> bool:
        return FAST_VAD_AVAILABLE and self._vad is not None


class FireRedVADWrapper:
    def __init__(
        self, sample_rate: int = 16000, use_gpu: bool = False, threshold: float = 0.4
    ):
        self.sample_rate = sample_rate
        self._use_gpu = use_gpu
        self._threshold = threshold
        self._stream_vad = None
        self._vad = None
        self._initialized = False

        if FIRERED_VAD_AVAILABLE:
            try:
                import os
                # Compute project root: nx_dictate/core/audio.py -> N-Xyme_MIND
                nx_dictate_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                project_root = os.path.dirname(nx_dictate_dir)
                model_base = os.path.join(project_root, "pretrained_models", "FireRedVAD")
                if not os.path.exists(model_base):
                    logger.warning(f"FireRedVAD model dir not found: {model_base}")
                else:
                    logger.info(f"Loading FireRedVAD from {model_base}...")
                    stream_config = fireredvad.FireRedStreamVadConfig(
                        use_gpu=use_gpu,
                        smooth_window_size=5,
                        speech_threshold=threshold,
                        pad_start_frame=5,
                        min_speech_frame=8,
                        max_speech_frame=2000,
                        min_silence_frame=20,
                    )
                    self._stream_vad = fireredvad.FireRedStreamVad.from_pretrained(
                        f"{model_base}/Stream-VAD",
                        stream_config,
                    )
                    self._initialized = True
                    logger.info("FireRedVAD (Stream) loaded - 97.57% F1")
            except Exception as e:
                logger.warning(f"FireRedVAD init failed: {type(e).__name__}: {e}")

    def is_speech(self, audio: np.ndarray) -> bool:
        if not self._initialized or not self._vad:
            return False
        if len(audio) < 400:
            return False
        try:
            result = self._vad.detect(audio)
            return bool(result.get("timestamps", []))
        except Exception:
            return False

    def is_speech_streaming(self, frame: np.ndarray) -> bool:
        if not self._initialized or not self._stream_vad:
            return False
        if len(frame) < 400:
            return False
        try:
            result = self._stream_vad.detect_frame(frame)
            return bool(result.is_speech_start) or bool(result.is_speech)
        except Exception:
            return False

    def reset(self) -> None:
        if self._stream_vad:
            self._stream_vad.reset()

    @property
    def available(self) -> bool:
        return FIRERED_VAD_AVAILABLE and self._initialized


class AudioPipeline:
    """Real-time audio capture using sounddevice."""

    def __init__(self, config: Optional[AudioConfig] = None):
        self._config = config or AudioConfig()
        self._stream: Optional[object] = None
        self._buffer: Optional[RingBuffer] = None
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        self._preview_callback: Optional[Callable[[str], None]] = None
        self._is_recording = False
        self._audio_queue: queue.Queue = queue.Queue(maxsize=50)
        self._target_sample_rate = 16000
        self._resampler = None
        self._vad = EnergyVAD(
            sample_rate=16000,
            threshold=config.noise_gate if config else 0.02,
        )
        self._vad_enabled = True
        self._ten_vad = None
        self._fast_vad = (
            FastVADWrapper(16000) if FAST_VAD_AVAILABLE else None
        )
        self._firered_vad = (
            FireRedVADWrapper(16000)
            if FIRERED_VAD_AVAILABLE
            else None
        )
        if self._fast_vad and self._fast_vad.available:
            logger.info("fast-vad initialized (721x realtime)")
        if self._firered_vad and self._firered_vad.available:
            logger.info("FireRedVAD initialized (97.57% F1)")
        
        # TEN VAD requires libc++ - only attempt if library is loadable
        self._ten_vad = None
        if TEN_VAD_AVAILABLE:
            try:
                import ctypes
                # Try to find libc++ - it's not always available as .so.1
                import os
                libcxx_paths = [
                    "/usr/lib/libc++.so",
                    "/usr/lib/x86_64-linux-gnu/libc++.so.1",
                    "libc++.so.1",
                ]
                loaded = False
                for lib_path in libcxx_paths:
                    try:
                        ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                        loaded = True
                        break
                    except (OSError, FileNotFoundError):
                        continue
                if not loaded:
                    # libc++ not available - disable TEN VAD gracefully
                    logger.warning("libc++.so.1 not found - TEN VAD disabled")
                else:
                    self._ten_vad = ten_vad.TenVad()
                    logger.info("TEN VAD initialized for low-latency voice detection")
            except Exception as e:
                logger.warning(f"TEN VAD init failed: {e}")
                self._ten_vad = None

    def resample_to_16khz(self, audio: np.ndarray, from_rate: int = None) -> np.ndarray:
        if from_rate is None:
            from_rate = self._config.sample_rate
        if from_rate == 16000 or len(audio) == 0:
            return audio
        try:
            from scipy import signal
            num_samples = int(len(audio) * 16000 / from_rate)
            if num_samples < 1:
                return audio
            return signal.resample(audio, num_samples)
        except (ImportError, Exception):
            if len(audio) < 100:
                return audio
            ratio = from_rate / 16000
            indices = np.arange(0, len(audio), ratio)
            return audio[np.clip(indices.astype(int), 0, len(audio) - 1)]

    @property
    def vad(self) -> EnergyVAD:
        return self._vad

    @property
    def fast_vad(self) -> Optional[FastVADWrapper]:
        return self._fast_vad

    @property
    def firered_vad(self) -> Optional[FireRedVADWrapper]:
        return self._firered_vad

    def enable_vad(self, enabled: bool) -> None:
        self._vad_enabled = enabled
        if not enabled:
            self._vad.reset()

    def is_speech_detected(self) -> bool:
        if not self._vad_enabled:
            return False
        return self._vad.get_current_speech_length() > 0

    def process_ten_vad(self, audio: np.ndarray) -> bool:
        if not self._ten_vad:
            return False
        try:
            result = self._ten_vad.process(audio)
            return (
                result.get("is_speech", False)
                if isinstance(result, dict)
                else bool(result)
            )
        except Exception:
            return False

    def set_preview_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        self._preview_callback = callback

    @property
    def config(self) -> AudioConfig:
        return self._config

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def queue_usage(self) -> int:
        return self._audio_queue.qsize()

    @property
    def available_devices(self) -> list[dict]:
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            if isinstance(devices, dict):
                return [devices]
            return [d for d in devices if d.get("max_input_channels", 0) > 0]
        except Exception as e:
            logger.warning(f"Failed to query devices: {e}")
            return []

    def get_default_device(self) -> Optional[int]:
        try:
            import sounddevice as sd

            default = sd.query_devices(kind="input")
            if default:
                return default.get("default_input_device")
        except Exception:
            pass
        return None

    def start(
        self,
        callback: Optional[Callable[[np.ndarray], None]] = None,
    ) -> bool:
        """Start audio capture."""
        if self._is_recording:
            return True

        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed")
            return False

        self._callback = callback

        chunk_samples = int(self._config.chunk_seconds * self._config.sample_rate)
        max_samples = int(self._config.max_recording_seconds * self._config.sample_rate)
        self._buffer = RingBuffer(max_samples)

        try:
            self._stream = sd.InputStream(
                device=self._config.device_index,
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype=self._config.dtype,
                blocksize=chunk_samples,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._is_recording = True
            logger.info(f"Audio capture started: {self._config.sample_rate}Hz")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio: {e}")
            return False

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: object,
    ) -> None:
        if status:
            logger.warning(f"Audio status: {status}")

        audio = indata[:, 0].astype(np.float32)

        # Apply noise gate
        if self._config.noise_reduction:
            audio = apply_noise_gate(audio, self._config.noise_gate)

        if self._buffer:
            self._buffer.write(audio)

        try:
            self._audio_queue.put_nowait(audio)
        except queue.Full:
            pass

        if self._callback:
            try:
                self._callback(audio)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def stop(self) -> tuple[np.ndarray, bool]:
        if not self._is_recording:
            return np.array([], dtype=np.float32), False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._is_recording = False
        overflow = False

        if self._buffer:
            overflow = self._buffer.is_overflowed
            audio = self._buffer.read()
            self._buffer.clear()
            return audio, overflow
        return np.array([], dtype=np.float32), False

    def get_audio_chunks(self) -> list[np.ndarray]:
        chunks = []
        while True:
            try:
                chunk = self._audio_queue.get_nowait()
                chunks.append(chunk)
            except queue.Empty:
                break
        return chunks

    def get_current_level(self) -> float:
        """Get current audio level (0-1 RMS)."""
        if not self._is_recording or not self._buffer:
            return 0.0
        sample_rate = self._config.sample_rate or SAMPLE_RATE
        samples_100ms = int(sample_rate * 0.1)
        audio = self._buffer.read(samples_100ms)
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio**2))
        return min(rms * 3, 1.0)

    def get_level_visualization(self, bars: int = 20) -> str:
        level = self.get_current_level()
        filled = int(level * bars)
        return "[" + "=" * filled + "-" * (bars - filled) + "]"

    def get_peak_level(self) -> float:
        if not self._is_recording or not self._buffer:
            return 0.0
        audio = self._buffer.read()
        if len(audio) == 0:
            return 0.0
        return float(np.abs(audio).max())


def list_audio_devices() -> list[dict]:
    """List all available audio input devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        if isinstance(devices, dict):
            return [devices]
        return [d for d in devices if d.get("max_input_channels", 0) > 0]
    except Exception as e:
        logger.warning(f"Failed to list devices: {e}")
        return []


def get_default_input_device() -> Optional[int]:
    """Get default input device index."""
    try:
        import sounddevice as sd
        default = sd.query_devices(kind="input")
        if default:
            return default.get("index")
    except Exception:
        pass
    return None


class ContinuousTranscriber:
    def __init__(
        self,
        vad: EnergyVAD,
        audio_queue: queue.Queue,
        sample_rate: int = 16000,
        min_speech_samples: int = 3200,
    ):
        self._vad = vad
        self._queue = audio_queue
        self._sample_rate = sample_rate
        self._min_speech_samples = min_speech_samples
        self._speech_chunks: list[np.ndarray] = []
        self._is_speaking = False
        self._last_speech_time = 0.0
        self._adaptive_threshold = 0.02
        self._noise_floor_samples = []
        self._calibrated = False

    def calibrate(self, ambient_audio: np.ndarray):
        if len(ambient_audio) > 0:
            rms = np.sqrt(np.mean(ambient_audio**2))
            self._noise_floor_samples.append(rms)
            if len(self._noise_floor_samples) >= 10:
                self._adaptive_threshold = np.median(self._noise_floor_samples) * 2.5
                self._vad.threshold = max(self._adaptive_threshold, 0.005)
                self._calibrated = True

    def process(self, audio_chunk: np.ndarray) -> tuple[list[np.ndarray], bool]:
        if not self._calibrated and len(audio_chunk) > 0:
            rms = np.sqrt(np.mean(audio_chunk**2))
            if rms < 0.01:
                self.calibrate(audio_chunk)

        is_speech = self._vad.is_speech(audio_chunk)

        if is_speech:
            self._speech_chunks.append(audio_chunk)
            self._is_speaking = True
            self._last_speech_time = time.time()
        elif self._is_speaking:
            silence_duration = time.time() - self._last_speech_time
            if silence_duration > 0.5:
                if self._get_total_samples() >= self._min_speech_samples:
                    result = self._speech_chunks.copy()
                    self._speech_chunks = []
                    self._is_speaking = False
                    return result, True
        return [], False

    def _get_total_samples(self) -> int:
        return sum(len(c) for c in self._speech_chunks)

    def reset(self) -> None:
        self._speech_chunks = []
        self._is_speaking = False
