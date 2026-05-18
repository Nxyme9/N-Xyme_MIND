#!/usr/bin/env python3
"""
jarvis_bridge.py — End-to-end Jarvis voice pipeline.

Connects nx_dictate transcription → agent system → TTS response.

Flow:
  nx_dictate transcribes voice → writes to FIFO pipe
  jarvis_bridge reads from FIFO
    → sends text to llama-server (rosetta-v13) for understanding
    → routes to agent system via MCP
    → generates response
    → speaks via espeak-ng TTS

Usage:
  python3 jarvis_bridge.py                    # foreground
  systemctl --user start jarvis-bridge         # systemd

Modes:
  --fifo PATH     Read from FIFO (default: /tmp/jarvis_fifo)
  --llama URL     llama-server URL (default: http://127.0.0.1:8088)
  --tts           Enable text-to-speech output (default: True)
  --no-tts        Disable TTS (debug mode)
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Ensure piper-tts is importable
_extra_paths = [
    "/home/nxyme/N-Xyme_CODE/venv/lib/python3.14/site-packages",
    "/home/nxyme/.local/lib/python3.14/site-packages",
]
for _p in _extra_paths:
    if _p not in sys.path:
        sys.path.insert(0, _p)
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────

FIFO_PATH = "/tmp/jarvis_fifo"
LLAMA_URL = "http://127.0.0.1:8088"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Logging ─────────────────────────────────────────────────────────────

def setup_logging():
    log_dir = PROJECT_ROOT / "data" / "memory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "jarvis_bridge.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [JARVIS] %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("jarvis")

logger = setup_logging()


# ── FIFO Setup ──────────────────────────────────────────────────────────

def ensure_fifo(path: str):
    """Create FIFO pipe if it doesn't exist."""
    if not os.path.exists(path):
        os.mkfifo(path)
        logger.info(f"FIFO created at {path}")
    else:
        logger.info(f"FIFO exists at {path}")


# ── Audio / TTS ─────────────────────────────────────────────────────────

PIPER_MODEL = str(PROJECT_ROOT / "data" / "voices" / "en_US-amy-medium.onnx")
_PIPER_VOICE = None

def _get_piper_voice():
    """Lazy-load Piper voice model."""
    global _PIPER_VOICE
    if _PIPER_VOICE is None and os.path.exists(PIPER_MODEL):
        try:
            from piper import PiperVoice
            _PIPER_VOICE = PiperVoice.load(PIPER_MODEL, use_cuda=False)
            logger.info(f"Piper voice loaded: en_US-amy-medium ({os.path.getsize(PIPER_MODEL) >> 20}MB)")
        except Exception as e:
            logger.warning(f"Piper load failed: {e}")
    return _PIPER_VOICE

def speak(text: str):
    """Speak text via Piper neural TTS — natural voice, CPU realtime."""
    if not text:
        return
    try:
        voice = _get_piper_voice()
        if voice is not None:
            # Synthesize via neural TTS (generator of AudioChunks)
            chunks = list(voice.synthesize(text))
            if chunks:
                rate = chunks[0].sample_rate
                for chunk in chunks:
                    audio_bytes = chunk.audio_int16_bytes
                    if audio_bytes:
                        play = subprocess.Popen(
                            ["paplay", "--raw", f"--rate={rate}",
                             "--channels=1", "--format=s16le"],
                            stdin=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                        )
                        play.communicate(input=audio_bytes, timeout=30)
                logger.info(f"🔊 Piper TTS: {text[:60]}...")
            else:
                logger.warning("Piper produced no audio")
        else:
            # Fallback to espeak-ng
            logger.warning("Piper unavailable, using espeak fallback")
            subprocess.run(
                ["espeak-ng", "-v", "en-us", "-s", "150", "-p", "50", text],
                capture_output=True, timeout=30,
            )
            logger.info(f"🔊 espeak TTS: {text[:60]}...")
    except Exception as e:
        logger.warning(f"TTS failed: {e}")


# ── llama-server (rosetta) query ────────────────────────────────────────

def query_llama(text: str) -> str:
    """Send text to the agent pipeline for a real response."""
    try:
        import urllib.request

        # Craft a prompt that makes the response feel like the System Architect
        payload = json.dumps({
            "messages": [
                {"role": "system", "content":
                 "You are the System Architect of N-Xyme MIND — a full-stack agent OS running "
                 "on an RTX 3080 Ti (80 SMs, 12 GB GDDR6X), Mojo 1.0.0b1 engine, "
                 "rosetta-v13 model (494M params, 896-dim), and Whisper large-v3 on GPU. "
                 "You talk directly, no fluff, with technical precision and a bit of fire. "
                 "Keep responses brief — 2-3 sentences max for voice."},
                {"role": "user", "content": text},
            ],
            "temperature": 0.8,
            "max_tokens": 256,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{LLAMA_URL}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"llama-server query failed: {e}")
        return f"System error: {e}"


# ── Agent system query ──────────────────────────────────────────────────

def query_agent(text: str) -> str:
    """Send text to agent system and get a spoken response."""
    # 1. Log to session file
    try:
        session_file = PROJECT_ROOT / "data" / "sessions" / "jarvis.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "type": "message",
            "role": "user",
            "agent": "Jarvis",
            "content": text,
            "timestamp": time.time(),
        }

        with open(session_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(f"Written to session: {text[:60]}...")
    except Exception as e:
        logger.warning(f"Session write failed: {e}")

    # 2. Get actual response from llama-server (rosetta-v13)
    response = query_llama(text)

    # 3. Log response to session
    try:
        response_entry = {
            "type": "message",
            "role": "assistant",
            "agent": "System Architect",
            "content": response,
            "timestamp": time.time(),
        }
        with open(session_file, "a") as f:
            f.write(json.dumps(response_entry) + "\n")
    except Exception:
        pass

    return response


# ── Main FIFO reader ────────────────────────────────────────────────────

def fifo_reader(tts_enabled: bool, fifo_path: str = FIFO_PATH, llama_url: str = LLAMA_URL):
    """Read from FIFO and process transcriptions."""
    logger.info(f"Listening on FIFO: {fifo_path}")
    logger.info(f"TTS: {'enabled' if tts_enabled else 'disabled'}")

    while True:
        try:
            with open(fifo_path, "r") as fifo:
                for line in fifo:
                    line = line.strip()
                    if not line:
                        continue

                    logger.info(f"▶ Received: {line[:80]}...")

                    # Process — get response from agent/LLM
                    response = query_agent(line)

                    if response:
                        logger.info(f"◀ Response: {response[:80]}...")

                        if tts_enabled:
                            speak(response)
                        else:
                            print(f"  [{response[:120]}]")

        except FileNotFoundError:
            logger.warning(f"FIFO {FIFO_PATH} not found, recreating...")
            ensure_fifo(FIFO_PATH)
            time.sleep(2)

        except Exception as e:
            logger.error(f"FIFO error: {e}")
            time.sleep(5)


# ── Health check endpoint (Unix socket) ─────────────────────────────────

def health_server(fifo_path: str = FIFO_PATH, llama_url: str = LLAMA_URL):
    """Unix socket health check for systemd."""
    sock_path = "/tmp/jarvis_bridge.sock"
    try:
        os.unlink(sock_path)
    except OSError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)
    os.chmod(sock_path, 0o666)

    while True:
        try:
            conn, _ = server.accept()
            data = conn.recv(1024)
            if data:
                health = {
                    "status": "running",
                    "fifo": fifo_path,
                    "llama": llama_url,
                    "pid": os.getpid(),
                    "tts": True,
                }
                conn.sendall(json.dumps(health).encode())
            conn.close()
        except Exception:
            pass


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Jarvis Bridge — Voice → Agent → TTS")
    parser.add_argument("--fifo", default=FIFO_PATH, help=f"FIFO path (default: {FIFO_PATH})")
    parser.add_argument("--llama", default=LLAMA_URL, help=f"llama-server URL (default: {LLAMA_URL})")
    parser.add_argument("--tts", action="store_true", default=True, help="Enable TTS")
    parser.add_argument("--no-tts", action="store_true", help="Disable TTS")
    parser.add_argument("--health", action="store_true", help="Check health and exit")
    args = parser.parse_args()

    tts_enabled = args.tts and not args.no_tts
    # Use args directly instead of globals to avoid scoping issues

    if args.health:
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{args.llama}/v1/models", timeout=5)
            print(f"llama-server: OK ({resp.status})")
        except Exception as e:
            print(f"llama-server: ERROR ({e})")
        print(f"FIFO: {'EXISTS' if os.path.exists(args.fifo) else 'NOT FOUND'}")
        return

    # Start health server in background
    threading.Thread(target=health_server, args=[args.fifo, args.llama], daemon=True).start()

    # Ensure FIFO
    ensure_fifo(args.fifo)

    # Listen
    fifo_reader(tts_enabled, args.fifo, args.llama)


if __name__ == "__main__":
    main()
