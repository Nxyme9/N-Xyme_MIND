#!/usr/bin/env python3
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import argparse
import logging
import time
import numpy as np
import threading
import sounddevice as sd
from nx_engine.engine.whisper import WhisperClient
from nx_engine.dictate.injection import copy_and_paste

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [Dictate] %(levelname)s: %(message)s"
)
logger = logging.getLogger("nxyme-dictate-daemon")

EVDEV_AVAILABLE = True
try:
    import evdev
except ImportError:
    EVDEV_AVAILABLE = False


class DictateDaemon:
    def __init__(self, device=1, model="large-v3-turbo"):
        self.device = device
        self.model = model
        self.sample_rate = 16000
        self.is_recording = False
        self.audio_buffer = []
        self.whisper = None
        self.mouse_device = None
        self.running = False

    def init_whisper(self):
        logger.info(f"Loading Whisper {self.model} on CUDA...")
        self.whisper = WhisperClient(
            model=self.model, device="cuda", compute_type="float16"
        )
        logger.info("Whisper ready")

    def init_mouse(self):
        if not EVDEV_AVAILABLE:
            logger.warning("evdev not available")
            return False

        record_code = evdev.ecodes.BTN_SIDE  # 275

        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
                caps = d.capabilities()
                if 0x01 in caps and record_code in caps[0x01]:
                    self.mouse_device = d
                    logger.info(f"Mouse listener: {d.name} ({path})")
                    return True
                d.close()
            except:
                pass
        logger.warning("No mouse with side button found")
        return False

    def start(self):
        self.init_whisper()
        if not self.init_mouse():
            logger.warning("Running without mouse buttons")

        self.running = True
        logger.info("=== N-Xyme Dictate Daemon Running ===")
        logger.info("Hold mouse button 275 to record, release to transcribe")
        logger.info("Button 276 sends Enter after paste")

        if self.mouse_device:
            self._mouse_loop()
        else:
            while self.running:
                time.sleep(1)

    def _mouse_loop(self):
        try:
            for event in self.mouse_device.read_loop():
                if not self.running:
                    break
                if event.type != evdev.ecodes.EV_KEY:
                    continue

                if event.code == 275:  # Side button - record
                    if event.value == 1:
                        self._start_recording()
                    else:
                        self._stop_recording()
                elif event.code == 276:  # Extra - send enter
                    if event.value == 1:
                        self._send_enter()

        except OSError as e:
            logger.error(f"Mouse error: {e}")

    def _start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.audio_buffer = []
        logger.info("Recording...")

        def callback(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_buffer.append(indata[:, 0].copy())

        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        self.stream.start()

    def _stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.stream.stop()
        self.stream.close()

        audio = np.concatenate(self.audio_buffer) if self.audio_buffer else np.array([])

        if len(audio) < 1600:  # Less than 100ms
            logger.warning("Audio too short")
            return

        rms = np.sqrt(np.mean(audio**2))
        if rms < 0.001:
            logger.warning(f"Audio too quiet (RMS: {rms:.4f})")
            return

        logger.info(f"Transcribing ({len(audio)} samples, RMS: {rms:.4f})...")

        result = self.whisper.transcribe(audio)

        if result:
            logger.info(f"Result: {result}")
            copy_and_paste(result)
        else:
            logger.warning("No text transcribed")

    def _send_enter(self):
        import subprocess

        for cmd in [["wtype", "-k", "Return"], ["ydotool", "key", "28:1", "28:0"]]:
            try:
                subprocess.run(cmd, check=True, timeout=1)
                logger.info("Enter sent")
                return
            except:
                pass
        logger.warning("Failed to send Enter")

    def stop(self):
        self.running = False
        if hasattr(self, "stream"):
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
        logger.info("Stopped")


def main():
    parser = argparse.ArgumentParser(description="N-Xyme Dictate Daemon")
    parser.add_argument("-d", "--device", type=int, default=1, help="Audio device")
    parser.add_argument("-m", "--model", default="large-v3-turbo", help="Whisper model")
    args = parser.parse_args()

    daemon = DictateDaemon(device=args.device, model=args.model)
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
