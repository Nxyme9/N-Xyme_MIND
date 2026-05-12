#!/usr/bin/env python3
"""Minimal dictation - hold to record, release to paste."""

import sounddevice as sd
import faster_whisper
import subprocess
import time
import threading
import sys

# Config
MODEL = "tiny"
DEVICE = 15  # Webcam mic
SAMPLE_RATE = 16000
RECORDING = False
AUDIO_BUFFER = []


def paste_text(text):
    """Paste text to active window."""
    if not text.strip():
        return
    # Copy to clipboard
    subprocess.run(["wl-copy"], input=text.encode(), check=False)
    # Paste with Ctrl+Shift+V
    subprocess.run(["wtype", "-k", "C+V"], check=False)
    time.sleep(0.1)
    # Send Enter (button 276)
    subprocess.run(["ydotool", "key", "28:1", "28:0"], check=False)


def record_audio(indata, frames, time_info, status):
    global AUDIO_BUFFER
    if RECORDING:
        AUDIO_BUFFER.append(indata.copy())


def on_press(event):
    global RECORDING, AUDIO_BUFFER
    if event.code == 275:  # Mouse back button
        print("🎤 Recording...")
        RECORDING = True
        AUDIO_BUFFER = []


def on_release(event):
    global RECORDING
    if event.code == 275:
        RECORDING = False
        print("⏹️ Transcribing...")
        # Combine audio
        import numpy as np

        audio = (
            np.concatenate(AUDIO_BUFFER)
            if AUDIO_BUFFER
            else np.zeros(SAMPLE_RATE, dtype=np.float32)
        )

        # Transcribe
        model = faster_whisper.WhisperModel(
            MODEL, device="cuda", compute_type="float16"
        )
        segments, _ = model.transcribe(audio, language="en")
        text = " ".join([s.text for s in segments])

        if text.strip():
            print(f"📝: {text}")
            paste_text(text)
        else:
            print("❌ No text")


# Hotkey listener
print("🚀 Starting dictation...")
print("Hold mouse button 275 to record, release to paste.")
print("Button 276 sends Enter after paste.")

# Start audio stream
stream = sd.InputStream(
    device=DEVICE,
    channels=1,
    samplerate=SAMPLE_RATE,
    blocksize=1024,
    callback=record_audio,
)

import evdev

mouse = [d for d in evdev.input_devices() if "mouse" in d.name.lower()]
if mouse:
    ec = evdev.InputDevice(mouse[0].path)
    for event in ec.read_loop():
        if event.value == 1:  # Press
            on_press(event)
        elif event.value == 0:  # Release
            on_release(event)
