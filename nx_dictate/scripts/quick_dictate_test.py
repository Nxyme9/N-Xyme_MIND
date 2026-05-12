#!/usr/bin/env python3
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import numpy as np
import sounddevice as sd
import time
from nx_engine.engine.whisper import WhisperClient

DEVICE = 1
SAMPLE_RATE = 16000
RECORD_SECONDS = 3
MODEL = "tiny"

print("=== N-Xyme Dictate Quick Test ===")
print(f"Device: {DEVICE} (Webcam C920)")
print(f"Recording: {RECORD_SECONDS}s")
print("Press Enter to start recording...")

input()

print("Recording...")
audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=DEVICE,
)
sd.wait()
audio = audio.flatten()
rms = np.sqrt(np.mean(audio**2))
print(f"Captured: {len(audio)} samples, RMS: {rms:.4f}")

if rms < 0.001:
    print("Audio too quiet! Check mic.")
    exit(1)

print("Transcribing with CUDA...")
client = WhisperClient(model=MODEL, device="cuda", compute_type="float16")
result = client.transcribe(audio)
print(f"Result: {result}")

if result:
    print("\nPasting to active window...")
    import subprocess

    subprocess.run(["wl-copy", result], check=True)
    time.sleep(0.1)
    subprocess.run(["wtype", "-k", "C+V"], check=True)
    time.sleep(0.1)
    subprocess.run(["ydotool", "key", "28:1", "28:0"], check=True)
    print("Done!")
else:
    print("No text transcribed.")
