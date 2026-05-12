#!/usr/bin/env python3
"""Quick Whisper transcription test."""
from faster_whisper import WhisperModel
import sys

# Use tiny for speed
model = WhisperModel("tiny", device="cuda", compute_type="int8_float16")
print("✅ Whisper model loaded")

# If we have an audio file, transcribe it
if len(sys.argv) > 1:
    audio = sys.argv[1]
    print(f"Transcribing: {audio}")
    segments, info = model.transcribe(audio, beam_size=1)
    print(f"Language: {info.language} ({info.language_probability:.2f})")
    for seg in segments:
        print(f"[{seg.start:.1s}-{seg.end:.1s}] {seg.text}")
else:
    print("Usage: python test_whisper.py <audio_file>")
