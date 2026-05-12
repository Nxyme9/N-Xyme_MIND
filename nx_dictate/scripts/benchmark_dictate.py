#!/usr/bin/env python3
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import time
import numpy as np
import sounddevice as sd
from nx_engine.engine.whisper import WhisperClient

MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3-turbo",
    "deepdml/faster-whisper-large-v3-turbo-ct2",
]

COMPUTE_TYPES = ["int8", "float16"]


def record_audio(seconds=3, device=1):
    audio = sd.rec(
        int(seconds * 16000),
        samplerate=16000,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()
    return audio.flatten()


def benchmark_model(model, compute_type, audio):
    try:
        start = time.time()
        whisper = WhisperClient(model=model, device="cuda", compute_type=compute_type)
        load_time = time.time() - start

        start = time.time()
        result = whisper.transcribe(audio, beam_size=5)
        transcribe_time = time.time() - start

        return {
            "model": model,
            "compute": compute_type,
            "load_time": load_time,
            "transcribe_time": transcribe_time,
            "result": result,
            "success": True,
        }
    except Exception as e:
        return {
            "model": model,
            "compute": compute_type,
            "error": str(e),
            "success": False,
        }


def main():
    print("=== N-Xyme Dictate Benchmark ===")
    print("Recording test audio...")
    audio = record_audio()
    print(f"Audio: {len(audio)} samples, RMS: {np.sqrt(np.mean(audio**2)):.4f}\n")

    print(f"{'Model':<50} {'Compute':<8} {'Load':<8} {'Transcribe':<10} {'Status'}")
    print("-" * 90)

    for model in MODELS:
        for compute in COMPUTE_TYPES:
            result = benchmark_model(model, compute, audio)
            if result["success"]:
                status = "✓"
                print(
                    f"{result['model']:<50} {result['compute']:<8} {result['load_time']:.1f}s {result['transcribe_time']:.2f}s {status}"
                )
            else:
                status = "✗"
                print(f"{model:<50} {compute:<8} - - {status}")
            print()


if __name__ == "__main__":
    main()
