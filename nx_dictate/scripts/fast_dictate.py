#!/usr/bin/env python3
"""Simple fast dictation - like Windows Voice Dictation."""

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

print("Loading tiny model...")
model = WhisperModel("tiny", device="cuda", compute_type="float16")
print("READY - Hold side button to dictat")


def record():
    print("Recording...")
    audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype="float32")
    sd.wait()
    audio = audio.flatten()

    print("Transcribing...")
    segments, _ = model.transcribe(audio, language="en")
    text = " ".join([s.text for s in segments])

    if text.strip():
        print(f"You said: {text}")
        # Copy to clipboard
        import subprocess

        subprocess.run(["wl-copy", text], capture_output=True)
        # Paste
        subprocess.run(
            ["ydotool", "key", "29:1", "46:1", "46:0", "29:0"], capture_output=True
        )
        print("Pasted!")


# Quick test
if __name__ == "__main__":
    record()
