#!/usr/bin/env python3
"""
bridge_daemon.py — ONNX embedding daemon (384-dim all-MiniLM-L6-v2).

Reads JSON-L from stdin:
  {"type": "embed", "text": "...", "id": "..."}

Writes JSON-L to stdout:
  {"type": "embed_result", "vector": [...], "dim": 384, "latency_us": N, "id": "..."}
  {"type": "error", "message": "...", "id": "..."}

Usage:
  python3 bridge_daemon.py
  echo '{"type":"embed","text":"hello world","id":"1"}' | python3 bridge_daemon.py
"""

import json
import os
import signal
import sys
import time
from typing import Optional

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

PROJECT_ROOT = os.environ.get(
    "NX_PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
ONNX_MODEL_PATH = os.path.join(PROJECT_ROOT, "data/memory/models/embedding.onnx")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIM = 384


class BridgeDaemon:
    """ONNX embedding daemon with JSON-L stdin/stdout protocol."""

    def __init__(self, model_path: str = ONNX_MODEL_PATH):
        self.model_path = model_path
        self.session: Optional[ort.InferenceSession] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.running = True
        self._load_model()

    def _load_model(self):
        """Load ONNX model and tokenizer."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"ONNX model not found at {self.model_path}. "
                f"Set NX_PROJECT_ROOT or check path."
            )
        self.session = ort.InferenceSession(self.model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        # Warm up: run a dummy embedding to load model into memory
        _ = self._embed_raw("warmup")

    def _embed_raw(self, text: str) -> np.ndarray:
        """Tokenize and embed, returning raw numpy vector."""
        tokens = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            return_tensors="np",
            max_length=128,
        )
        inputs = {inp.name: tokens[inp.name] for inp in self.session.get_inputs()}
        # all-MiniLM-L6-v2 ONNX typically outputs two tensors;
        # the second (index 1) is the pooled embedding
        outputs = self.session.run(None, inputs)
        embedding = outputs[1] if len(outputs) > 1 else outputs[0]
        # Normalize to unit vector for cosine similarity
        norm = np.linalg.norm(embedding, axis=1, keepdims=True)
        embedding = embedding / (norm + 1e-12)
        return embedding[0]

    def embed(self, text: str) -> tuple[list[float], int]:
        """Embed text, return (vector, latency_us)."""
        start = time.perf_counter()
        vec = self._embed_raw(text)
        elapsed_us = int((time.perf_counter() - start) * 1_000_000)
        return vec.tolist(), elapsed_us

    def handle_request(self, req: dict) -> dict:
        """Process a single JSON-L request."""
        req_type = req.get("type", "")
        req_id = req.get("id", "0")

        if req_type == "embed":
            text = req.get("text", "")
            if not text:
                return {
                    "type": "error",
                    "message": "Missing 'text' field",
                    "id": req_id,
                }
            vector, latency_us = self.embed(text)
            return {
                "type": "embed_result",
                "vector": vector,
                "dim": EXPECTED_DIM,
                "latency_us": latency_us,
                "id": req_id,
            }
        elif req_type == "status":
            return {
                "type": "status_result",
                "running": True,
                "model": MODEL_NAME,
                "dim": EXPECTED_DIM,
                "onnx": self.model_path,
                "id": req_id,
            }
        else:
            return {
                "type": "error",
                "message": f"Unknown request type: {req_type}",
                "id": req_id,
            }

    def run(self):
        """Main loop — read JSON-L lines from stdin, write to stdout."""
        # Signal ready on stderr (not stdout which is for protocol)
        print("bridge_daemon ready", file=sys.stderr, flush=True)

        for line in sys.stdin:
            if not self.running:
                break
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                result = self.handle_request(req)
                print(json.dumps(result), flush=True)
            except json.JSONDecodeError as e:
                error = {"type": "error", "message": f"JSON parse error: {e}"}
                print(json.dumps(error), flush=True)
            except Exception as e:
                error = {"type": "error", "message": str(e)}
                print(json.dumps(error), flush=True)

    def shutdown(self):
        """Graceful shutdown."""
        self.running = False


def main():
    daemon = BridgeDaemon()

    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...", file=sys.stderr)
        daemon.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.shutdown()
    except Exception as e:
        print(json.dumps({"type": "fatal", "message": str(e)}), flush=True)
        daemon.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
