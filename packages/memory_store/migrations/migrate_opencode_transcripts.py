#!/usr/bin/env python3
"""
Migrate OpenCode transcript JSONL files to mind_from_mind.db.

Reads from:
- /home/nxyme/.claude/transcripts/
- /home/nxyme/Documents/opencode_transcripts/transcripts/

Writes to:
- context/memory/mind_from_mind.db (threads, messages, memories, memory_embeddings)

Idempotent via INSERT OR REPLACE / INSERT OR IGNORE.
Logs learning outcome via learning_engine.record_outcome().

Usage:
    python migrate_opencode_transcripts.py              # full run
    python migrate_opencode_transcripts.py --dry-run      # parse-only, no DB write
    python migrate_opencode_transcripts.py --limit 10    # limit file count for testing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import struct
import time
import uuid
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Any, Generator, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TRANSCRIPT_DIRS = [
    "/home/nxyme/.claude/transcripts/",
    "/home/nxyme/Documents/opencode_transcripts/transcripts/",
]

_EMBED_DIM = 768

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _parse_jsonl(path: str) -> Generator[dict, None, None]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _detect_thread_id(records: List[dict]) -> Optional[str]:
    for rec in records:
        rec_type = rec.get("type", "")
        if rec_type in ("user", "assistant"):
            ts = rec.get("timestamp", "")
            if ts:
                return f"transcript_{ts.replace(':', '').replace('-', '').replace('.', '')[:14]}"
    return None


class TranscriptParser:
    def __init__(self):
        pass

    def parse_file(self, path: str) -> Generator[dict, None, None]:
        yield from _parse_jsonl(path)

    def detect_thread_id(self, records: List[dict]) -> Optional[str]:
        return _detect_thread_id(records)

    def extract_messages(self, records: List[dict]) -> List[dict]:
        messages = []
        for rec in records:
            rec_type = rec.get("type", "")
            if rec_type not in ("user", "assistant", "system"):
                continue
            role = rec.get("role", "user")
            if rec_type == "tool_result":
                role = "tool"
            elif rec_type == "tool_use":
                role = "assistant"
            content = rec.get("content", "")
            if not content or not isinstance(content, str):
                continue
            timestamp = rec.get("timestamp", datetime.now().isoformat())
            messages.append({
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content[:50000],
                "created_at": timestamp,
                "meta_json": json.dumps({
                    "type": rec_type,
                    "name": rec.get("name", ""),
                    "tool_name": rec.get("tool_name", ""),
                    "source": "transcript_migration",
                }),
                "mode": rec.get("mode", ""),
                "model": rec.get("model", ""),
            })
        return messages

    def generate_memories(self, messages: List[dict]) -> List[dict]:
        if not messages:
            return []
        thread_texts = []
        for msg in messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            snippet = content[:2000]
            thread_texts.append(f"[{role}] {snippet}")

        combined = "\n\n".join(thread_texts)

        session_summary = ""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            first_user = user_msgs[0].get("content", "")[:500]
            last_user = user_msgs[-1].get("content", "")[:500]
            session_summary = f"Session started with: {first_user[:300]}... | Ended with: {last_user[:300]}"

        tool_uses = [m for m in messages if m.get("role") == "assistant" and m.get("meta_json")]
        tool_summary = f"Tool uses in session: {len(tool_uses)}"

        memories = []
        if session_summary:
            memories.append({
                "content": session_summary,
                "kind": "episodic",
                "scope": "session",
                "tags": json.dumps(["transcript", "session_summary"]),
            })
        if tool_summary:
            memories.append({
                "content": tool_summary,
                "kind": "procedural",
                "scope": "session",
                "tags": json.dumps(["transcript", "tool_usage"]),
            })

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            if len(content) < 20:
                continue
            memories.append({
                "content": f"[{role}] {content[:3000]}",
                "kind": "episodic",
                "scope": "session",
                "tags": json.dumps(["transcript", role]),
            })

        return memories


class ThreadManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert(self, thread_id: str, title: str, created_at: str, metadata: Optional[dict] = None) -> int:
        meta = json.dumps(metadata or {})
        cur = self.conn.execute(
            """INSERT OR REPLACE INTO threads (id, title, created_at, updated_at, meta_json)
               VALUES (?, ?, ?, ?, ?)""",
            (thread_id, title[:500], created_at, datetime.now().isoformat(), meta),
        )
        return cur.rowcount


class MessageManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert_batch(self, thread_id: str, messages: List[dict]) -> int:
        inserted = 0
        for msg in messages:
            msg_id = msg["id"]
            content_hash = _content_hash(msg["content"])
            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO messages
                       (id, thread_id, role, content, created_at, meta_json, mode, model)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        msg_id,
                        thread_id,
                        msg["role"],
                        msg["content"],
                        msg["created_at"],
                        msg.get("meta_json", "{}"),
                        msg.get("mode", ""),
                        msg.get("model", ""),
                    ),
                )
                inserted += 1
            except Exception as e:
                logger.debug(f"Message insert skipped: {e}")
        return inserted


class MemoryIngestion:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from packages.memory_store.stores.vector_store import EmbeddingEngine
            self._engine = EmbeddingEngine()
        return self._engine

    def ingest_messages(self, thread_id: str, messages: List[dict], dry_run: bool = False) -> int:
        parser = TranscriptParser()
        memories = parser.generate_memories(messages)

        if dry_run:
            return len(memories)

        stored = 0
        for mem in memories:
            content = mem["content"]
            memory_id = f"mem_{_content_hash(content)}_{thread_id[:8]}"

            self.conn.execute(
                """INSERT OR IGNORE INTO memories
                   (id, kind, scope, thread_id, content, created_at, updated_at,
                    meta_json, tier, tags, score, archived)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, 0)""",
                (
                    memory_id,
                    mem["kind"],
                    mem["scope"],
                    thread_id,
                    content[:50000],
                    datetime.now().isoformat(),
                    json.dumps({"source": "transcript_migration"}),
                    "long_term",
                    mem.get("tags", "[]"),
                    0.5,
                ),
            )

            try:
                self._embed_and_store(memory_id, content)
                stored += 1
            except Exception as e:
                logger.debug(f"Memory embed failed for {memory_id}: {e}")
                stored += 1

        return stored

    def _embed_and_store(self, memory_id: str, content: str) -> None:
        try:
            engine = self._get_engine()
            vector = engine.embed_text(content[:2048])
        except Exception:
            vector = self._hash_fallback(content)

        vec_blob = struct.pack(f"<{_EMBED_DIM}f", *vector)
        self.conn.execute(
            """INSERT OR IGNORE INTO memory_embeddings (memory_id, model, dim, vec)
               VALUES (?, ?, ?, ?)""",
            (memory_id, "nomic-embed-text", _EMBED_DIM, vec_blob),
        )

    def _hash_fallback(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).digest()
        return [(h[i % len(h)] / 255.0) * 2 - 1 for i in range(_EMBED_DIM)]


def _find_transcript_files(dirs: List[str], limit: Optional[int] = None) -> List[str]:
    files = []
    for d in dirs:
        if os.path.isdir(d):
            pattern = os.path.join(d, "*.jsonl")
            files.extend(sorted(glob(pattern)))
    if limit:
        files = files[:limit]
    return files


def main(dry_run: bool = False, limit: Optional[int] = None) -> dict:
    start_time = time.time()

    print("=== N-Xyme Transcript Migration ===")
    print(f"Source directories: {TRANSCRIPT_DIRS}")

    transcript_files = _find_transcript_files(TRANSCRIPT_DIRS, limit)
    total_files = len(transcript_files)
    print(f"Total transcript files: {total_files}")

    if total_files == 0:
        print("Status: NO_FILES_FOUND")
        return {"success": True, "files": 0, "threads": 0, "messages": 0, "memories": 0}

    if dry_run:
        print("Mode: DRY RUN (no DB writes)")

    stats = {"files_processed": 0, "threads_upserted": 0, "messages_inserted": 0, "memories_generated": 0, "failures": 0}

    if not dry_run:
        conn = _get_db()
        thread_mgr = ThreadManager(conn)
        msg_mgr = MessageManager(conn)
        mem_ing = MemoryIngestion(conn)
    else:
        conn = None
        thread_mgr = None
        msg_mgr = None
        mem_ing = None

    parser = TranscriptParser()

    try:
        for idx, fpath in enumerate(transcript_files):
            fname = os.path.basename(fpath)
            if (idx + 1) % 100 == 0 or idx == 0:
                print(f"Processing: {idx + 1}/{total_files} — {fname}")

            try:
                records = list(parser.parse_file(fpath))
                if not records:
                    continue

                thread_id = _detect_thread_id(records)
                if not thread_id:
                    thread_id = f"transcript_{Path(fpath).stem[:16]}"

                messages = parser.extract_messages(records)
                if not messages:
                    continue

                created_at = messages[0].get("created_at", datetime.now().isoformat()) if messages else datetime.now().isoformat()
                title = messages[0].get("content", "")[:200] if messages else fname

                if conn:
                    thread_mgr.upsert(
                        thread_id=thread_id,
                        title=title,
                        created_at=created_at,
                        metadata={"source_file": fname, "source_path": fpath, "migrated_from": "opencode_transcripts"},
                    )
                    stats["threads_upserted"] += 1

                    msg_mgr.upsert_batch(thread_id, messages)
                    stats["messages_inserted"] += len(messages)

                    mem_count = mem_ing.ingest_messages(thread_id, messages, dry_run=False)
                    stats["memories_generated"] += mem_count

                else:
                    parser2 = TranscriptParser()
                    msgs_only = parser2.extract_messages(records)
                    stats["memories_generated"] += len(parser2.generate_memories(msgs_only))

                stats["files_processed"] += 1

            except Exception as e:
                stats["failures"] += 1
                logger.debug(f"Failed {fpath}: {e}")

            if conn and (idx + 1) % 50 == 0:
                conn.commit()

    finally:
        if conn:
            conn.commit()
            conn.close()

    elapsed = time.time() - start_time

    print(f"\n=== Results ===")
    print(f"Files processed:     {stats['files_processed']}/{total_files}")
    print(f"Threads upserted:   {stats['threads_upserted']}")
    print(f"Messages inserted:  {stats['messages_inserted']}")
    print(f"Memories generated: {stats['memories_generated']}")
    print(f"Failures:           {stats['failures']}")
    print(f"Duration:           {elapsed:.1f}s")

    try:
        from packages.learning_engine.outcome_logger import DelegationOutcome, OutcomeLogger

        outcome = DelegationOutcome(
            task_id=f"migrate_transcripts_{int(time.time())}",
            task_description=f"migrate {stats['files_processed']} transcript sessions",
            task_type="implementation",
            agent="migrate_transcripts",
            level=3,
            success=(stats["failures"] == 0),
            latency_ms=int(elapsed * 1000),
            tokens_used=0,
            context={
                "files_processed": stats["files_processed"],
                "threads_upserted": stats["threads_upserted"],
                "messages_inserted": stats["messages_inserted"],
                "memories_generated": stats["memories_generated"],
                "failures": stats["failures"],
            },
        )
        logger_outcome = OutcomeLogger(db_path=str(PROJECT_ROOT / ".sisyphus" / "outcomes.db"))
        outcome_id = logger_outcome.log(outcome)
        logger.info(f"Learning outcome recorded: id={outcome_id}")
    except Exception as e:
        logger.debug(f"Learning outcome not recorded: {e}")

    status = "SUCCESS" if stats["failures"] == 0 else "PARTIAL"
    print(f"Status: {status}")

    return {"success": stats["failures"] == 0, **stats, "elapsed_seconds": round(elapsed, 1)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate OpenCode transcripts to mind_from_mind.db")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    parser.add_argument("--limit", type=int, default=None, help="Limit files for testing")
    args = parser.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)