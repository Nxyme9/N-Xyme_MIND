from __future__ import annotations
import asyncio
import logging
import socket
import threading
from typing import Optional, Callable

logger = logging.getLogger("nxyme_dictate.network_audio")


class NetworkAudioReceiver:
    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_audio_callback: Optional[Callable[[bytes], None]] = None
        self._format = "s16le"
        self._sample_rate = 16000
        self._channels = 1

    def set_callback(self, callback: Callable[[bytes], None]):
        self._on_audio_callback = callback

    def start(self) -> bool:
        if self._running:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._host, self._port))
            self._socket.settimeout(1.0)

            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            logger.info(f"Network audio receiver started on {self._host}:{self._port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start network audio receiver: {e}")
            return False

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def _run_loop(self):
        buffer = b""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                if data:
                    if data.startswith(b"HEADER:"):
                        header = data.decode().split(":")[1:]
                        if len(header) >= 3:
                            self._sample_rate = int(header[0])
                            self._channels = int(header[1])
                            self._format = header[2]
                        continue
                    elif data == b"END":
                        if buffer and self._on_audio_callback:
                            self._on_audio_callback(buffer)
                        buffer = b""
                    else:
                        buffer += data

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"Network audio error: {e}")
                break

    def is_running(self) -> bool:
        return self._running


class NetworkAudioClient:
    def __init__(self, host: str, port: int = 9000):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._opus_encoder = None
        self._use_opus = False

    def _init_opus(self):
        try:
            import opuslib

            self._opus_encoder = opuslib.Encoder(48000, 1, opuslib.APPLICATION_VOIP)
            self._use_opus = True
            logger.info("Opus codec initialized for network audio")
        except ImportError:
            logger.debug("Opus not available, using PCM")

    def connect(self) -> bool:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._init_opus()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self._host}:{self._port}: {e}")
            return False

    def send_audio(self, audio_data: bytes, sample_rate: int = 16000, channels: int = 1):
        if not self._socket:
            return False
        try:
            header = f"HEADER:{sample_rate}:{channels}:s16le\n".encode()
            self._socket.sendto(header, (self._host, self._port))

            if self._use_opus and self._opus_encoder and sample_rate != 48000:
                import numpy as np

                pcm_data = np.frombuffer(audio_data, dtype=np.int16)
                pcm_48k = self._resample(pcm_data, sample_rate, 48000)
                encoded = self._opus_encoder.encode(pcm_48k.tobytes(), 960, 60)
                self._socket.sendto(encoded, (self._host, self._port))
            else:
                self._socket.sendto(audio_data, (self._host, self._port))
            return True
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            return False

    def _resample(self, data, from_rate, to_rate):
        import numpy as np

        if from_rate == to_rate:
            return data
        ratio = to_rate / from_rate
        new_len = int(len(data) * ratio)
        indices = np.linspace(0, len(data) - 1, new_len)
        return np.interp(indices, np.arange(len(data)), data).astype(np.int16)

    def send_end(self):
        if self._socket:
            try:
                self._socket.sendto(b"END", (self._host, self._port))
            except Exception:
                pass

    def close(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
