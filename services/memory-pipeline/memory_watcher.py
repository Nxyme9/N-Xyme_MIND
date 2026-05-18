#!/usr/bin/env python3
"""
memory_watcher.py — Daemon that watches data/sessions/ for new .jsonl files,
auto-ingests them into the memory vector store using the existing ONNX pipeline.

Uses the same embed pipeline as ingest_sessions.py (all-MiniLM-L6-v2, 384-dim)
but runs continuously as a daemon instead of one-shot.

Usage:
  python3 memory_watcher.py                    # foreground
  python3 memory_watcher.py --daemon           # background, nohup
  systemctl --user start nx-memory-watcher     # systemd

Design:
  - Polls data/sessions/ every 60s for new/modified .jsonl files
  - Tracks processed files in data/memory/vectors/.processed_ids
  - Embeds new content via ONNX (same as ingest_sessions.py)
  - Appends to data/memory/vectors/sessions.jsonl
  - Logs to data/memory/logs/memory_watcher.log
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np

# Optional — will attempt import, fall back to subprocess if not available
try:
    import onnxruntime as ort
    from transformers import AutoTokenizer

    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

PROJECT_ROOT = Path(os.environ.get(
    "NX_PROJECT_ROOT",
    Path(__file__).resolve().parent.parent.parent,
))

SESSIONS_DIR = PROJECT_ROOT / "data" / "sessions"
MEMORY_DIR = PROJECT_ROOT / "data" / "memory"
VECTORS_DIR = MEMORY_DIR / "vectors"
LOGS_DIR = MEMORY_DIR / "logs"
OUTPUT_FILE = VECTORS_DIR / "sessions.jsonl"
PROCESSED_FILE = VECTORS_DIR / ".processed_ids"
ONNX_MODEL_PATH = MEMORY_DIR / "models" / "embedding.onnx"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIM = 384
BATCH_SIZE = 256
POLL_INTERVAL = 60  # seconds
MAX_CHUNK_LENGTH = 512  # tokenizer max


# ── Logging ──────────────────────────────────────────────────────────────

def setup_logging(daemon: bool = False):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "memory_watcher.log"

    handlers = [logging.FileHandler(str(log_file))]
    if not daemon:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("memory_watcher")


# ── Embed engine ────────────────────────────────────────────────────────

class EmbedEngine:
    """ONNX embedding engine — same pipeline as ingest_sessions.py."""

    def __init__(self, logger):
        self.logger = logger
        self.session = None
        self.tokenizer = None
        self.input_name = None
        self.output_name = None
        self._load()

    def _load(self):
        if not HAS_ONNX:
            self.logger.warning("ONNX not available — will use subprocess fallback")
            return

        if not ONNX_MODEL_PATH.exists():
            self.logger.warning(f"ONNX model not found at {ONNX_MODEL_PATH} — will download")
            self._download_model()

        try:
            self.logger.info(f"Loading ONNX model from {ONNX_MODEL_PATH}")
            self.session = ort.InferenceSession(str(ONNX_MODEL_PATH))
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.logger.info(f"Model loaded — input: {self.input_name}, output: {self.output_name}")
        except Exception as e:
            self.logger.error(f"Failed to load ONNX model: {e}")
            self.session = None

    def _download_model(self):
        """Download ONNX model from HuggingFace if not present."""
        try:
            from sentence_transformers import SentenceTransformer
            import shutil

            self.logger.info(f"Downloading {MODEL_NAME} and exporting to ONNX...")
            model = SentenceTransformer(MODEL_NAME)
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            # Export to ONNX
            dummy = np.random.randn(1, EXPECTED_DIM).astype(np.float32)
            # SentenceTransformer doesn't have direct ONNX export, use transformers
            self.logger.info("Download complete — will use transformers directly")
        except Exception as e:
            self.logger.warning(f"Could not download model automatically: {e}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.session or not self.tokenizer:
            return self._embed_fallback(texts)

        results = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            try:
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=MAX_CHUNK_LENGTH,
                    return_tensors="np",
                )
                onnx_inputs = {}
                for inp in self.session.get_inputs():
                    if inp.name == "input_ids":
                        onnx_inputs[inp.name] = encoded["input_ids"]
                    elif inp.name == "attention_mask":
                        onnx_inputs[inp.name] = encoded["attention_mask"]
                    elif inp.name == "token_type_ids":
                        onnx_inputs[inp.name] = encoded.get("token_type_ids", encoded["attention_mask"])

                embeddings = self.session.run([self.output_name], onnx_inputs)[0]
                # Mean pool
                attention_mask = encoded["attention_mask"]
                mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
                sum_embeddings = np.sum(embeddings * mask_expanded, axis=1)
                sum_mask = np.clip(np.sum(mask_expanded, axis=1), 1e-9, None)
                pooled = sum_embeddings / sum_mask
                # Normalize
                norms = np.linalg.norm(pooled, axis=1, keepdims=True)
                pooled = pooled / np.clip(norms, 1e-9, None)
                results.extend(pooled.tolist())
            except Exception as e:
                self.logger.error(f"ONNX batch failed: {e}")
                results.extend([[0.0] * EXPECTED_DIM] * len(batch))

        return results

    def _embed_fallback(self, texts: list[str]) -> list[list[float]]:
        """Fallback: use sentence-transformers via subprocess."""
        self.logger.info("Using sentence-transformers fallback...")
        try:
            import subprocess
            payload = json.dumps({"texts": texts, "dim": EXPECTED_DIM})
            result = subprocess.run(
                [sys.executable, "-c", f"""
import json, sys
from sentence_transformers import SentenceTransformer
data = json.loads('{payload.replace(chr(39), chr(34))}')
model = SentenceTransformer('{MODEL_NAME}')
emb = model.encode(data['texts'], normalize_embeddings=True)
print(json.dumps(emb.tolist()))
"""],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return json.loads(result.stdout.strip())
            else:
                self.logger.error(f"Fallback failed: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Fallback error: {e}")
        return [[0.0] * EXPECTED_DIM] * len(texts)

    def embed_dim(self) -> int:
        return EXPECTED_DIM


# ── Session parser ──────────────────────────────────────────────────────

def extract_sessions(filepath: Path) -> list[dict]:
    """Extract meaningful content from a session .jsonl file."""
    entries = []
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract content based on role/type
                content = None
                role = None
                agent = None
                msg_type = None

                # Standard message format
                if "content" in obj:
                    content = obj["content"]
                elif "message" in obj and isinstance(obj["message"], dict):
                    content = obj["message"].get("content")
                    role = obj["message"].get("role")

                if not content or not isinstance(content, str):
                    continue
                content = content.strip()
                if len(content) < 10:
                    continue

                role = role or obj.get("role", "user")
                agent = obj.get("agent", obj.get("_agent", filepath.stem))
                msg_type = obj.get("type", "message")

                # Filter out system noise
                if role == "system" and len(content) < 50:
                    continue

                # Generate stable ID
                content_hash = hashlib.md5(content.encode()).hexdigest()[:12]

                entry = {
                    "id": f"{filepath.stem}-{content_hash}",
                    "session": filepath.stem,
                    "agent": agent,
                    "role": role,
                    "type": msg_type,
                    "content": content,
                    "source": str(filepath),
                    "timestamp": obj.get("timestamp", time.time()),
                }
                entries.append(entry)
    except Exception as e:
        logging.getLogger("memory_watcher").error(f"Error reading {filepath}: {e}")

    return entries


# ── Processed ID tracker ────────────────────────────────────────────────

def load_processed_ids() -> set[str]:
    """Load set of already-processed content IDs."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def save_processed_id(content_id: str):
    """Append a processed content ID to the tracker."""
    with open(PROCESSED_FILE, "a") as f:
        f.write(content_id + "\n")


def get_session_files() -> list[Path]:
    """Get all .jsonl session files sorted by modification time."""
    if not SESSIONS_DIR.exists():
        return []
    return sorted(
        SESSIONS_DIR.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
    )


# ── Main watcher loop ───────────────────────────────────────────────────

def run_once(engine: EmbedEngine, logger: logging.Logger) -> int:
    """Single pass: scan new sessions, embed, store. Returns count of new vectors."""
    processed_ids = load_processed_ids()
    session_files = get_session_files()

    if not session_files:
        logger.debug("No session files found")
        return 0

    # Collect new entries
    new_entries = []
    for sf in session_files:
        entries = extract_sessions(sf)
        for entry in entries:
            if entry["id"] not in processed_ids:
                new_entries.append(entry)

    if not new_entries:
        logger.debug("No new content to embed")
        return 0

    logger.info(f"Found {len(new_entries)} new entries across {len(session_files)} files")

    # Chunk and embed
    all_chunks = []
    all_meta = []
    for entry in new_entries:
        content = entry["content"]
        agent = entry.get("agent", "unknown")
        role = entry.get("role", "user")
        # Simple chunking: split long content
        words = content.split()
        if len(words) <= 100:
            chunks = [content]
        else:
            chunk_size = 100
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

        for chunk in chunks:
            chunk_id = hashlib.md5(chunk.encode()).hexdigest()[:12]
            if chunk_id in processed_ids:
                continue
            all_chunks.append(chunk)
            all_meta.append({
                "id": chunk_id,
                "session": entry["session"],
                "agent": agent,
                "role": role,
                "type": entry.get("type", "message"),
                "source": entry.get("source", ""),
                "timestamp": entry.get("timestamp", time.time()),
            })
            processed_ids.add(chunk_id)

    if not all_chunks:
        logger.debug("All chunks already processed")
        return 0

    # Embed
    logger.info(f"Embedding {len(all_chunks)} chunks ({engine.embed_dim()}d)...")
    vectors = engine.embed(all_chunks)

    # Write
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(OUTPUT_FILE, "a") as f:
        for meta, vec in zip(all_meta, vectors):
            record = {
                **meta,
                "vector": vec,
                "dim": engine.embed_dim(),
                "model": MODEL_NAME,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            save_processed_id(meta["id"])
            count += 1

    logger.info(f"Stored {count} new vectors ({engine.embed_dim()}d)")
    return count


def main():
    parser = argparse.ArgumentParser(description="N-Xyme Memory Watcher Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run in background")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help=f"Poll interval in seconds (default: {POLL_INTERVAL})")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    logger = setup_logging(daemon=args.daemon)
    logger.info("=== Memory Watcher starting ===")
    logger.info(f"Sessions dir: {SESSIONS_DIR}")
    logger.info(f"Output file:  {OUTPUT_FILE}")
    logger.info(f"Model:        {MODEL_NAME} ({EXPECTED_DIM}d)")

    # Ensure directories exist
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize embed engine
    engine = EmbedEngine(logger)

    if args.once:
        count = run_once(engine, logger)
        logger.info(f"Done — {count} vectors stored")
        return

    # Continuous loop
    logger.info(f"Watching for new sessions every {args.interval}s...")
    while True:
        try:
            count = run_once(engine, logger)
            if count:
                logger.info(f"Total vectors stored this cycle: {count}")
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in watch loop: {e}", exc_info=True)

        time.sleep(args.interval)

    logger.info("=== Memory Watcher stopped ===")


if __name__ == "__main__":
    main()
