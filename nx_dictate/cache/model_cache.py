#!/usr/bin/env python3
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import pickle
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nxyme-model-cache")

CACHE_DIR = Path.home() / ".cache" / "nxyme-dictate"
MODEL_KEYS = {
    "deepdml/faster-whisper-large-v3-turbo-ct2": "large-v3-turbo-ct2",
    "large-v3-turbo": "large-v3-turbo",
    "medium": "medium",
    "small": "small",
    "tiny": "tiny",
}


def get_cache_path(model_name: str) -> Path:
    key = MODEL_KEYS.get(model_name, model_name.replace("/", "-"))
    return CACHE_DIR / f"model-{key}.pkl"


def save_cache(model_name: str, whisper_client) -> bool:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_cache_path(model_name)

    try:
        with open(cache_path, "wb") as f:
            pickle.dump(whisper_client, f)
        logger.info(f"Model cached: {cache_path}")
        return True
    except Exception as e:
        logger.error(f"Cache save failed: {e}")
        return False


def load_cache(model_name: str):
    cache_path = get_cache_path(model_name)

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "rb") as f:
            client = pickle.load(f)
        logger.info(f"Model loaded from cache: {cache_path}")
        return client
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return None


def warmup_model(whisper_client, device=1, sample_rate=16000, seconds=2):
    import sounddevice as sd
    import numpy as np

    logger.info("Warming up model...")

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()
    audio = audio.flatten()

    result = whisper_client.transcribe(audio)
    logger.info(f'Warmup complete: "{result}"')
    return result


def preload_model(
    model_name="deepdml/faster-whisper-large-v3-turbo-ct2",
    device="cuda",
    compute_type="float16",
    warmup=True,
    device_idx=1,
):
    from nx_engine.engine.whisper import WhisperClient

    logger.info(f"Loading model: {model_name}")

    cached = load_cache(model_name)
    if cached:
        logger.info("Using cached model")
        if warmup:
            warmup_model(cached, device=device_idx)
        return cached

    client = WhisperClient(model=model_name, device=device, compute_type=compute_type)

    if warmup:
        warmup_model(client, device=device_idx)

    save_cache(model_name, client)

    return client


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Cache Manager")
    parser.add_argument("--model", default="deepdml/faster-whisper-large-v3-turbo-ct2")
    parser.add_argument("--warmup", action="store_true", default=True)
    args = parser.parse_args()

    client = preload_model(args.model, warmup=args.warmup)
    print("Model ready!")
