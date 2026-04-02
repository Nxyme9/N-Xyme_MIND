"""
Simple Dictation Tool - Uses existing faster-whisper for STT.
No admin, no Store, no internet needed.

Hold RIGHT CTRL to talk, release to transcribe.
Text gets typed into whatever window is focused.
"""

import sys
import os
import time
import tempfile
import subprocess
import threading

sys.path.insert(0, r"D:\01_CODING\00_N-Xyme_CATALYST")

import numpy as np
import sounddevice as sd

# === CONFIG ===
SAMPLE_RATE = 16000
HOTKEY = "right ctrl"  # Hold to talk
DEVICE_ID = 1  # Your C920 mic (from audio_config)

print("Loading Whisper model (takes a few seconds)...")
from faster_whisper import WhisperModel

model = WhisperModel("distil-small.en", device="cpu", compute_type="int8")
print("Model loaded!")

audio_buffer = []
is_recording = False


def audio_callback(indata, frames, time_info, status):
    """Collect audio while recording."""
    if is_recording:
        audio_buffer.extend(indata[:, 0].tolist())


def transcribe():
    """Transcribe collected audio and type it."""
    global audio_buffer
    if len(audio_buffer) < SAMPLE_RATE * 0.5:  # Too short
        audio_buffer = []
        return

    audio = np.array(audio_buffer, dtype=np.float32)
    audio_buffer = []

    print("Transcribing...", end="", flush=True)
    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
    )

    text = " ".join(seg.text for seg in segments).strip()
    print(f"\rTranscribed: {text}")

    if text:
        # Copy to clipboard and paste (fastest method)
        import subprocess

        subprocess.run(
            [
                "powershell",
                "-Command",
                f"Set-Clipboard -Value '{text.replace(chr(39), chr(39) + chr(39))}'",
            ],
            capture_output=True,
        )
        # Send Ctrl+V to paste
        import ctypes

        VK_V = 0x56
        VK_CONTROL = 0x11
        KEYDOWN = 0x0000
        KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYDOWN, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, KEYDOWN, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
        print("Pasted!")


def listen_for_hotkey():
    """Monitor for hotkey press/release."""
    global is_recording
    import ctypes

    VK_RCONTROL = 0xA3
    was_pressed = False

    print(f"\n{'=' * 50}")
    print(f"  DICTATION READY")
    print(f"  Hold RIGHT CTRL to speak")
    print(f"  Release to transcribe & paste")
    print(f"  Press ESC to quit")
    print(f"{'=' * 50}\n")

    while True:
        # Check ESC
        if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
            print("\nExiting...")
            return

        # Check Right Ctrl
        pressed = ctypes.windll.user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000

        if pressed and not was_pressed:
            # Started holding
            is_recording = True
            audio_buffer.clear()
            print("[LISTENING...]", end="", flush=True)

        elif not pressed and was_pressed:
            # Released
            is_recording = False
            print("\r", end="", flush=True)
            threading.Thread(target=transcribe, daemon=True).start()

        was_pressed = pressed
        time.sleep(0.05)


if __name__ == "__main__":
    # Start audio stream
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        device=DEVICE_ID,
        channels=1,
        dtype="float32",
        blocksize=int(SAMPLE_RATE * 0.1),
        callback=audio_callback,
    ):
        listen_for_hotkey()
