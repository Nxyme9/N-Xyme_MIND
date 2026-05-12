# N-Xyme Dictate - Main Entry Point
# Unified dictation system with UI, hotkey, and text injection

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import argparse
import time
import uuid
import math
import struct
import array
import wave
from io import BytesIO
import subprocess
from pathlib import Path
from typing import Optional
from aiohttp import web
import logging.handlers

# =============================================================================
# File Logging Setup with Rotation
# =============================================================================
LOG_DIR = Path.home() / ".local" / "share" / "nx_dictate" / "logs"
LOG_FILE = LOG_DIR / "dictate.log"

# Create log directory if it doesn't exist (user-writable)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure file handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
))

# Configure console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
))

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger("nxyme_dictate")


class DictationHTTPServer:
    def __init__(self, dictation_system, host="127.0.0.1", port=8765):
        self._dictation = dictation_system
        self._host = host
        self._port = port
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._setup_routes()
        self._last_result: Optional[dict] = None

    def _setup_routes(self):
        self._app.router.add_get("/", self.handle_index)
        self._app.router.add_get("/health", self.handle_health)
        self._app.router.add_post("/start", self.handle_start)
        self._app.router.add_post("/stop", self.handle_stop)
        self._app.router.add_get("/status", self.handle_status)
        self._app.router.add_get("/result", self.handle_result)
        self._app.router.add_post("/transcribe", self.handle_transcribe)
        self._app.router.add_get("/stream", self.handle_stream)

    async def handle_index(self, request):
        return web.json_response({
            "service": "N-Xyme Dictate",
            "version": "1.0.0",
            "endpoints": ["/health", "/start", "/stop", "/status", "/result", "/transcribe"],
        })

    async def handle_transcribe(self, request):
        try:
            import base64
            import numpy as np

            data = await request.json()
            audio_base64 = data.get("audio")

            if not audio_base64:
                return web.json_response({"error": "No audio data"}, status=400)

            audio_bytes = base64.b64decode(audio_base64)
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            if hasattr(self._dictation, '_preprocess_audio'):
                audio = self._dictation._preprocess_audio(audio)

            result = self._dictation._engine.transcribe(audio)

            return web.json_response({
                "text": result,
                "id": str(uuid.uuid4()) if 'uuid' in globals() else str(time.time()),
            })
        except Exception as e:
            logger.error(f"Transcribe error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_stream(self, request):
        async def event_generator():
            import uuid
            while True:
                await asyncio.sleep(1)
                yield f"data: {uuid.uuid4().hex[:8]}\n\n"

        return web.StreamResponse(
            event_generator(),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async def handle_health(self, request):
        gpu_status = "unknown"
        gpu_mem = 0
        try:
            import torch
            if torch.cuda.is_available():
                gpu_status = "cuda"
                gpu_mem = torch.cuda.get_device_properties(0).total_memory // (1024**2)
        except Exception:
            pass

        model_status = "unknown"
        if self._dictation and self._dictation._engine:
            model_status = getattr(self._dictation._engine, '_config', {}).model if hasattr(self._dictation._engine, '_config') else "loaded"
            if hasattr(self._dictation._engine, '_resolved_device'):
                gpu_status = self._dictation._engine._resolved_device

        return web.json_response(
            {
                "status": "healthy",
                "state": self._dictation._state if self._dictation else "unknown",
                "gpu": gpu_status,
                "gpu_memory_mb": gpu_mem,
                "model": model_status,
            }
        )

    async def handle_start(self, request):
        try:
            data = await request.json() if request.can_read_body else {}
            device = data.get("device", 1)

            if self._dictation._state in ("idle", "ready"):
                self._dictation._audio_device_index = device
                self._dictation._start_recording()

            return web.json_response(
                {"status": "started", "state": self._dictation._state}
            )
        except Exception as e:
            logger.error(f"Start error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_stop(self, request):
        try:
            if self._dictation._state == "recording":
                self._dictation._stop_recording()

            return web.json_response(
                {"status": "stopped", "state": self._dictation._state}
            )
        except Exception as e:
            logger.error(f"Stop error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_status(self, request):
        return web.json_response(
            {
                "state": self._dictation._state,
                "is_recording": self._dictation._is_recording,
                "last_result": self._dictation._last_transcription,
                "live_partial": self._dictation._live_partial,
            }
        )

    async def handle_result(self, request):
        return web.json_response(self._dictation._last_transcription or {"text": ""})

    async def start(self):
        """Start HTTP server with port reuse and graceful error handling."""
        import socket

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        # Enable port reuse to avoid "Address already in use" errors
        # This allows restarting quickly after a crash
        loop = asyncio.get_event_loop()

        # Create a socket with SO_REUSEADDR
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Check if port is already in use (before trying to bind)
        try:
            server_socket.bind((self._host, self._port))
            server_socket.close()  # Close it - aiohttp will rebind
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.warning(f"Port {self._port} is in use, attempting to reuse...")
            else:
                raise

        try:
            self._site = web.TCPSite(
                self._runner,
                self._host,
                self._port,
                reuse_address=True,  # Enable SO_REUSEADDR via aiohttp
            )
            await self._site.start()
            logger.info(f"HTTP control server started on {self._host}:{self._port}")
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(
                    f"Port {self._port} already in use. "
                    f"Try killing stale processes: lsof -i :{self._port}"
                )
                raise RuntimeError(
                    f"Port {self._port} is already in use. "
                    "Run: lsof -i :8765 | grep python | awk '{print $2}' | xargs kill"
                ) from e
            raise

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()

    def set_result(self, result: dict):
        self._last_result = result


class DictationSystem:
    def __init__(self):
        self._app = None
        self._engine = None
        self._audio = None
        self._hotkey = None
        self._ui = None
        self._injector = None
        self._training = None
        self._state = "idle"
        self._is_recording = False
        self._last_audio_time = 0.0
        self._http_server = None
        self._last_transcription: Optional[dict] = None
        self._live_partial: Optional[str] = None
        self._last_typed_text = ""
        self._saved_window = None  # Save window before recording steals focus

    def initialize(self, args) -> bool:
        logger.info("Initializing N-Xyme Dictate...")

        from .core.engine import (
            get_engine,
            DictationConfig,
            auto_select_model,
            get_gpu_vram_gb,
        )
        from .core.audio import AudioPipeline, AudioConfig
        from .core.hotkey import create_default_hotkey
        from .training import get_onboarding
        from .history import get_history

        self._training = get_onboarding()
        self._history = get_history()
        self._history_enabled = args.history if hasattr(args, "history") else True
        self._output_file = args.output if hasattr(args, "output") else None

        vram = get_gpu_vram_gb()

        language = args.language if hasattr(args, "language") else "auto"

        vocabulary = None
        if hasattr(args, "vocabulary") and args.vocabulary:
            vocabulary = args.vocabulary

        if args.model:
            model = args.model
        else:
            model = auto_select_model(vram)
        logger.info(f"GPU: {vram:.1f}GB VRAM, model: {model}")

        config = DictationConfig(
            model=model,
            device="auto",
            language=language,
            vocabulary=vocabulary,
        )
        self._engine = get_engine(config)
        if not self._engine.load():
            logger.error("Failed to load whisper engine")
            return False
        logger.info(
            f"Engine loaded on {getattr(self._engine, '_resolved_device', 'unknown')}"
        )

        device_index = args.device

        import sounddevice as sd
        from nx_dictate.core.audio import get_default_input_device

        # Handle device string like "auto" vs actual device index
        if device_index is None or not isinstance(device_index, int):
            # Use system default device instead of hardcoded device 19
            device_index = get_default_input_device()
            if device_index is None:
                logger.warning("No default input device found, using device 0")
                device_index = 0
        device_info = sd.query_devices(device_index)
        sample_rate = int(device_info.get('default_samplerate', 44100))
        logger.info(f"Using device {device_index} at {sample_rate}Hz")

        audio_config = AudioConfig(
            sample_rate=sample_rate,
            channels=1,
            device_index=device_index,
        )
        self._audio = AudioPipeline(audio_config)
        self._audio_device_index = device_index

        # Hotkey
        self._hotkey = create_default_hotkey(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            on_next_language=self._on_language_switch,
        )

        # Text injection
        from .injection import get_backend, copy_and_paste
        from .text_processor import process_text, PersonalDictionary, SnippetsManager
        from .audio_processing import preprocess_audio
        from .realtime import RealtimeTranscriber
        from .noise_suppression import create_noise_suppressor
        from .commands import create_command_recognizer
        from .metrics import MetricsCollector

        self._copy_and_paste = copy_and_paste
        self._process_text = process_text
        self._preprocess_audio = preprocess_audio
        self._noise_suppressor = create_noise_suppressor()
        self._command_recognizer = create_command_recognizer()
        self._metrics = MetricsCollector()
        logger.info(f"Text injection: {get_backend()}")

        # Personal dictionary and snippets
        data_dir = Path.home() / ".config" / "nx_dictate"
        dictionary = PersonalDictionary(str(data_dir / "dictionary.json"))
        snippets = SnippetsManager(str(data_dir / "snippets.json"))
        filler_enabled = not (hasattr(args, "no_filler") and args.no_filler)
        self._text_processor_kwargs = {
            "dictionary": dictionary,
            "snippets": snippets,
            "enable_fillers": filler_enabled,
        }
        logger.info(f"Personal dictionary: {len(dictionary.get_all())} words, Snippets: {len(snippets.get_all())}, Fillers: {filler_enabled}")

        # Real-time transcription (if enabled)
        self._realtime_enabled = args.realtime if hasattr(args, "realtime") else False
        self._noise_enabled = args.no_noise if hasattr(args, "no_noise") else True
        if hasattr(args, "fast") and args.fast:
            self._noise_enabled = False
            logger.info("Fast mode: noise suppression disabled")
        self._fast_mode = hasattr(args, "fast") and args.fast
        self._realtime_transcriber = None
        self._languages = (
            args.languages.split(",")
            if hasattr(args, "languages") and args.languages
            else ["en"]
        )
        self._current_lang_index = 0
        if self._realtime_enabled:
            self._realtime_transcriber = RealtimeTranscriber(
                whisper_client=self._engine._client,
                chunk_duration_ms=500,
                on_partial=self._on_partial_result,
                on_final=self._on_final_result,
            )
            logger.info(
                f"Real-time transcription enabled with languages: {self._languages}"
            )

        # Only use _stream_transcribe if NOT using RealtimeTranscriber (prevents double typing)
        # When --realtime is passed, use RealtimeTranscriber only
        # Otherwise, use _stream_transcribe as fallback
        self._live_streaming = not self._realtime_enabled

        # UI (optional)
        if not args.no_ui:
            from .ui import create_ui

            self._ui = create_ui(
                on_toggle=self._toggle_dictation,
                on_quit=self.shutdown,
            )
            if self._ui:
                self._ui.update_state("idle")
                if hasattr(self._ui, "_tray"):
                    self._ui._tray.set_callback(
                        "device_changed", self._on_device_changed
                    )
                    self._ui._tray.set_callback("show_settings", self._show_settings)
                    self._ui._tray.set_callback("toggle", self._toggle_dictation)

        # Audio startup verification
        self._verify_audio()

        logger.info("N-Xyme Dictate initialized")
        return True

    def _verify_audio(self):
        # Skip audio verification to avoid segfault
        logger.info(
            "Audio verification skipped (using device {})".format(
                self._audio_device_index
            )
        )

    def _on_hotkey_press(self):
        if self._state in ("idle", "ready"):
            self._start_recording()

    def _on_hotkey_release(self):
        if self._state == "recording":
            self._stop_recording()

    def _on_device_changed(self, device_index: int):
        if self._is_recording:
            logger.warning("Device change ignored during recording")
            return
        self._audio.stop()
        self._audio_device_index = device_index
        self._training.profile.audio_device_index = device_index
        self._training._save_profile()

        from .core.audio import AudioConfig, AudioPipeline

        new_config = AudioConfig(
            sample_rate=16000, channels=1, device_index=device_index
        )
        self._audio = AudioPipeline(new_config)
        logger.info(f"Device changed to {device_index}, audio restarted")

    def _start_recording(self):
        # CRITICAL: Save the focused window BEFORE recording steals focus
        self._saved_window = None
        try:
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                self._saved_window = result.stdout.strip()
                logger.debug(f"Saved window for later: {self._saved_window}")
        except Exception as e:
            logger.debug(f"Could not save window: {e}")
        
        if self._is_recording:
            return

        self._audio.start(callback=self._on_audio_chunk)
        self._is_recording = True
        self._state = "recording"
        self._last_audio_time = time.time()

        if self._live_streaming:
            self._streaming_active = True
            self._last_transcribed = ""
            self._streaming_thread = threading.Thread(
                target=self._stream_transcribe,
                daemon=True,
            )
            self._streaming_thread.start()

        if self._ui:
            self._ui.update_state("recording")
        self._play_beep("start")
        logger.info(f"Recording started (mic: {self._audio_device_index})")

    def _on_audio_chunk(self, audio_chunk):
        if self._realtime_enabled and self._realtime_transcriber:
            self._realtime_transcriber.add_chunk(audio_chunk)

    def _stream_transcribe(self):
        import numpy as np

        chunk_duration = 0.01
        sample_rate = 16000
        chunk_samples = int(chunk_duration * sample_rate)
        min_samples = int(0.01 * sample_rate)

        silence_threshold = 0.15
        min_phrase_samples = int(0.3 * sample_rate)

        audio_buffer = []
        last_speech_time = time.time()
        last_output_text = ""

        client = self._engine._client

        while self._streaming_active and self._is_recording:
            time.sleep(chunk_duration)
            if not self._streaming_active or not self._is_recording:
                break

            audio = self._audio._buffer.read() if self._audio._buffer else np.array([])
            if hasattr(self._audio, 'resample_to_16khz'):
                audio = self._audio.resample_to_16khz(audio)
            if len(audio) < min_samples:
                continue

            audio_buffer.append(audio)

            rms = (
                np.sqrt(np.mean(audio[-chunk_samples:] ** 2))
                if len(audio) >= chunk_samples
                else 0
            )
            if rms > 0.01:
                last_speech_time = time.time()

            silence_elapsed = time.time() - last_speech_time
            total_buffer = (
                np.concatenate(audio_buffer) if audio_buffer else np.array([])
            )

            if (
                silence_elapsed > silence_threshold
                and len(total_buffer) >= min_phrase_samples
            ):
                try:
                    transcribe_start = time.time()
                    result = client.transcribe(
                        total_buffer,
                        beam_size=1,
                        temperature=0.0,
                        language="en",
                        without_timestamps=True,
                        log_prob_threshold=-1.0,
                        compression_ratio_threshold=1.5,
                        no_speech_threshold=0.3,
                    )
                    if isinstance(result, tuple) and len(result) >= 1:
                        segments = result[0]
                        if hasattr(segments, '__iter__'):
                            result = "".join([getattr(s, 'text', str(s)) for s in segments])
                    elif hasattr(result, '__iter__') and not isinstance(result, str):
                        try:
                            result = "".join([getattr(r, 'text', str(r)) for r in result])
                        except Exception:
                            result = str(result)

                    if result and isinstance(result, str) and result.strip():
                        text = result.strip()
                        if text and text != last_output_text and len(text) > 2:
                            processed = self._process_text(text, **self._text_processor_kwargs)
                            result = self._command_recognizer.process(processed)
                            if len(result) == 3:
                                processed, commands, special_action = result
                                from .injection import (
                                    type_text_direct,
                                    execute_special_action,
                                )

                                if not type_text_direct(processed + " "):
                                    self._copy_and_paste(processed + " ")
                                if special_action:
                                    execute_special_action(special_action)
                            else:
                                processed, commands = result
                                from .injection import type_text_direct

                                if not type_text_direct(processed + " "):
                                    self._copy_and_paste(processed + " ")

                            last_output_text = text
                            self._live_partial = (
                                processed if "processed" in dir() else text
                            )

                    audio_buffer = []
                    last_speech_time = time.time()

                except Exception:
                    audio_buffer = []
                    pass

    def _stop_recording(self):
        if not self._is_recording:
            return

        self._streaming_active = False
        time.sleep(0.1)

        audio_data, overflow = self._audio.stop()
        self._is_recording = False

        if overflow:
            logger.warning("Recording exceeded max duration - some audio may be lost")

        self._play_beep("stop")

        import numpy as np

        rms = float(np.sqrt(np.mean(audio_data**2))) if len(audio_data) > 0 else 0.0
        min_samples = 800
        min_rms = 0.001

        if len(audio_data) < min_samples or rms < min_rms:
            logger.info(
                f"Audio too short/quiet ({len(audio_data)} samples, RMS={rms:.4f}) - skipping"
            )
            self._state = "idle"
            if self._ui:
                self._ui.update_state("idle")
            return

        self._state = "processing"
        if self._ui:
            self._ui.update_state("processing")

        self._play_beep("stop")
        logger.info("Recording stopped, transcribing...")

        threading.Thread(
            target=self._transcribe_audio,
            args=(audio_data,),
            daemon=True,
        ).start()

    def _transcribe_audio(self, audio_data):
        try:
            if hasattr(self._audio, 'resample_to_16khz'):
                audio_data = self._audio.resample_to_16khz(audio_data)
            if self._noise_enabled and self._noise_suppressor:
                audio_data = self._noise_suppressor.suppress(audio_data)
            audio_data = self._preprocess_audio(audio_data)

            result = self._engine.transcribe(audio_data)

            if result and isinstance(result, str) and result.strip():
                logger.info(f"Transcribed: {result[:50]}...")

                # Type text LIVE as it's transcribed - no copy/paste!
                from .injection import type_text_direct

                if not type_text_direct(result):
                    processed = self._process_text(result, **self._text_processor_kwargs)
                    self._copy_and_paste(processed)

                # Store result for HTTP API polling
                self._last_transcription = {
                    "text": result,
                    "processed": self._process_text(result, **self._text_processor_kwargs),
                    "timestamp": time.time(),
                }
                if self._http_server:
                    self._http_server.set_result(self._last_transcription)

                processed = self._process_text(result, **self._text_processor_kwargs)

                processed, commands = self._command_recognizer.process(processed)

                word_count = len(result.split())

                if self._history_enabled:
                    self._history.add(
                        text=processed,
                        language=getattr(self._engine._config, "language", None),
                        model=getattr(self._engine, "model_name", None),
                        word_count=word_count,
                    )

                if self._output_file:
                    with open(self._output_file, "a") as f:
                        f.write(f"{processed}\n")

                self._training.record_transcription(word_count)

                if self._ui:
                    self._ui.notify_text(result)

                if self._training.profile.sound_enabled:
                    self._play_completion_sound()

            self._state = "idle"
            if self._ui:
                self._ui.update_state("idle")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self._state = "error"
            if self._ui:
                self._ui.update_state("error")
            self._state = "idle"
            if self._ui:
                self._ui.update_state("idle")

    def _play_beep(self, event: str):
        freq = 880 if event == "start" else 440
        duration_ms = 80
        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000)
        samples = [
            int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
            for i in range(num_samples)
        ]
        try:
            wav_data = BytesIO()
            with wave.open(wav_data, "w") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(array.array('h', samples).tobytes())
            wav_data.seek(0)
        except Exception:
            return

        for cmd in [
            ["canberra-uuid", "-f", "-i", "dialog-information"],
            ["paplay", "-"],
            ["aplay", "-q"],
        ]:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=wav_data.getvalue(), timeout=1)
                if proc.returncode == 0:
                    return
            except Exception:
                continue

    def _play_completion_sound(self):
        for cmd in [
            ["canberra-uuid", "-f", "-i", "dialog-information"],
        ]:
            try:
                subprocess_run(cmd, timeout=2, capture_output=True)
                return
            except Exception:
                continue

        complete_oga = "/usr/share/sounds/freedesktop/stereo/complete.oga"
        if os.path.exists(complete_oga):
            try:
                subprocess_run(["paplay", complete_oga], timeout=2, capture_output=True)
                return
            except Exception:
                pass

    def _toggle_dictation(self):
        if self._state in ("idle", "ready"):
            self._start_recording()
        elif self._state == "recording":
            self._stop_recording()

    def _show_settings(self):
        if self._ui:
            self._ui.show_settings()

    def _on_language_switch(self):
        if not self._languages or len(self._languages) <= 1:
            return
        self._current_lang_index = (self._current_lang_index + 1) % len(self._languages)
        new_lang = self._languages[self._current_lang_index]
        self._engine._config.language = new_lang
        logger.info(f"Language switched to: {new_lang}")
        if self._ui:
            self._ui.notify_text(f"Language: {new_lang}", partial=True)

    def _on_partial_result(self, result):
        """Handle partial transcription result - display only, DON'T type (prevents endless typing)."""
        if not result:
            return
        text = result.text if hasattr(result, 'text') else str(result)
        if not text:
            return

        logger.debug(f"Partial: {text[:50]}...")

        # ONLY display/update UI - NEVER type during speech
        # Typing here causes endless loop of text appearing
        if self._ui:
            self._ui.notify_text(text, partial=True)

        # Store for potential final typing (don't type now!)
        self._live_partial = text
        self._last_typed_text = text

    def _on_final_result(self, result):
        """Handle final transcription result - type text immediately."""
        if not result:
            return
        text = result.text if hasattr(result, 'text') else str(result)
        if not text:
            return

        logger.info(f"Final: {text[:50]}...")

        if text and not text.startswith("["):
            processed = self._process_text(text, **self._text_processor_kwargs)

            # Type text - either direct or via clipboard paste
            from .injection import type_text_direct
            if not type_text_direct(processed + " "):
                self._copy_and_paste(processed)

            # CRITICAL: Restore focus to the original window AFTER typing
            if self._saved_window:
                try:
                    import subprocess
                    # Small delay to let typing complete
                    time.sleep(0.2)
                    # Restore and raise the original window
                    subprocess.run(
                        ["xdotool", "windowactivate", self._saved_window],
                        capture_output=True, timeout=2
                    )
                    subprocess.run(
                        ["xdotool", "windowraise", self._saved_window],
                        capture_output=True, timeout=2
                    )
                    logger.debug(f"Restored focus to window {self._saved_window}")
                except Exception as e:
                    logger.debug(f"Could not restore window: {e}")
                finally:
                    self._saved_window = None

            self._play_completion_sound()

    def run(self):
        if self._http_server:
            import threading
            import asyncio

            def run_server():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._http_server.start())
                    loop.run_forever()
                except Exception as e:
                    logger.error(f"HTTP server error: {e}")
                finally:
                    loop.close()

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            logger.info("HTTP server thread started")

        if self._ui:
            self._ui.run()
        else:
            logger.info(f"N-Xyme Dictate running... (Mode: {self._hotkey.mode})")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

    def shutdown(self):
        logger.info("Shutting down...")
        if self._http_server:
            asyncio.run(self._http_server.stop())
        if self._audio:
            self._audio.stop()
        if self._hotkey:
            self._hotkey.stop()
        if self._engine:
            self._engine.unload()
        if self._ui:
            self._ui.quit()
        logger.info("Shutdown complete")


def subprocess_run(*args, **kwargs):
    import subprocess

    return subprocess.run(*args, **kwargs)


def main(
    host: str = "127.0.0.1",
    port: int = 8765,
    hotkey: bool = False,
    injection: bool = False,
    model: str = None,
    device: str = "auto",
    **kwargs,
):
    """
    Main entry point for N-Xyme Dictate.
    
    Can be called programmatically with keyword arguments or via CLI.
    When called from CLI (direct execution), parses sys.argv.
    When called programmatically, uses provided parameters.
    """
    import argparse
    
    # When called directly as module (__main__), parse CLI args
    # When called programmatically, use passed parameters
    _direct_call = kwargs.pop("_direct_call", False)
    
    if _direct_call or (host != "127.0.0.1" or port != 8765 or hotkey or injection or model or device != "auto"):
        # Called programmatically with parameters - create args namespace
        class Args:
            pass
        args = Args()
        args.host = host
        args.port = port
        args.http_port = port
        args.hotkey = hotkey
        args.injection = injection
        args.model = model
        args.device = device
        args.config = None
        args.no_ui = True  # Headless when called via run_dictate
        args.verbose = kwargs.get("verbose", False)
        args.language = kwargs.get("language", "auto")
        args.vocabulary = kwargs.get("vocabulary", None)
        args.output = kwargs.get("output", None)
        args.daemon = kwargs.get("daemon", False)
        args.history = kwargs.get("history", True)
        args.realtime = kwargs.get("realtime", False)
        args.no_noise = kwargs.get("no_noise", False)
        args.fast = kwargs.get("fast", False)
        args.languages = kwargs.get("languages", "en")
        args.no_ui = True
        args.config_dict = {}
    else:
        # Called via CLI - parse arguments
        parser = argparse.ArgumentParser(description="N-Xyme Dictate")
        parser.add_argument(
            "--config",
            "-c",
            default=None,
            help="Path to config file (YAML/JSON)",
        )
        parser.add_argument(
            "--model",
            "-m",
            default=None,
            help="Whisper model (tiny, base, small, medium, large-v3-turbo)",
        )
        parser.add_argument(
            "--device", "-d", type=int, default=None, help="Audio device index"
        )
        parser.add_argument(
            "--no-ui", action="store_true", help="Run without UI (CLI only)"
        )
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
        parser.add_argument(
            "--language",
            "-l",
            default="auto",
            help="Language code (auto, en, de, fr, etc.)",
        )
        parser.add_argument(
            "--hotkey",
            default=None,
            help="Keyboard shortcut for toggle (e.g., 'ctrl+alt+d', 'ctrl+shift+space')",
        )
        parser.add_argument(
            "--vocabulary",
            "-V",
            nargs="+",
            default=None,
            help="Custom vocabulary/keywords (space separated)",
        )
        parser.add_argument(
            "--output",
            "-o",
            default=None,
            help="Save transcription to file",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run as daemon (background service)",
        )
        parser.add_argument(
            "--history",
            action="store_true",
            default=True,
            help="Enable transcription history (default: enabled)",
        )
        parser.add_argument(
            "--realtime",
            action="store_true",
            default=False,
            help="Enable real-time partial results streaming",
        )
        parser.add_argument(
            "--no-noise",
            action="store_true",
            default=False,
            help="Disable noise suppression",
        )
        parser.add_argument(
            "--fast",
            action="store_true",
            default=False,
            help="Ultra-fast mode: no noise suppression + faster decoding",
        )
        parser.add_argument(
            "--no-filler",
            action="store_true",
            default=False,
            help="Disable automatic filler word removal",
        )
        parser.add_argument(
            "--whisper",
            action="store_true",
            default=False,
            help="Whisper mode: lower sensitivity threshold for quiet speech",
        )
        parser.add_argument(
            "--languages",
            default="en",
            help="Comma-separated language codes (e.g., en,de,fr)",
        )
        parser.add_argument(
            "--http-port",
            type=int,
            default=8765,
            help="Port for HTTP control server",
        )
        args = parser.parse_args()

        config = {}
        if args.config:
            import yaml

            try:
                with open(args.config) as f:
                    if args.config.endswith(".json"):
                        import json

                        config = json.load(f)
                    else:
                        config = yaml.safe_load(f)
                logger.info(f"Loaded config from {args.config}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return 1

        args.config_dict = config

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load .env configuration if available
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info(f"Loaded config from {env_file}")
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env")

    system = DictationSystem()
    if not system.initialize(args):
        logger.error("Initialization failed")
        return 1

    # Start HTTP control server
    http_port = args.http_port if hasattr(args, "http_port") else 8765
    system._http_server = DictationHTTPServer(system, port=http_port)

    system.run()
    system.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
