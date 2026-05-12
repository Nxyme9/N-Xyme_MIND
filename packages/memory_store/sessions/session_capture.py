"""Real-time session capture for OpenCode transcripts."""
import os
import json
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CaptureResult:
    success: bool
    file_path: str
    thread_id: Optional[str] = None
    messages_count: int = 0
    memories_count: int = 0
    error: Optional[str] = None

class SessionCapture:
    """
    Captures a transcript JSONL file and writes to mind_from_mind.db.
    Reuses parser logic from migrate_opencode_transcripts.py but works
    on a single file at a time.
    """

    TRANSCRIPT_DIRS = [
        os.path.expanduser("~/.claude/transcripts/"),
        os.path.expanduser("~/Documents/opencode_transcripts/transcripts/"),
    ]
    DB_PATH = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'context', 'memory', 'mind_from_mind.db'
    )

    def __init__(self):
        self._conn = None
        self._embedding_engine = None

    def _get_conn(self):
        if self._conn is None:
            import sqlite3
            self._conn = sqlite3.connect(self.DB_PATH)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _get_embedding_engine(self):
        if self._embedding_engine is None:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from packages.memory_store.stores.vector_store import EmbeddingEngine
            self._embedding_engine = EmbeddingEngine()
        return self._embedding_engine

    def capture_file(self, file_path: str) -> CaptureResult:
        """
        Parse a transcript file and write to DB.
        Returns CaptureResult with success status and counts.
        """
        try:
            if not os.path.exists(file_path):
                return CaptureResult(success=False, file_path=file_path,
                                     error=f"File not found: {file_path}")

            records = list(self._parse_file(file_path))
            if not records:
                return CaptureResult(success=False, file_path=file_path,
                                     error="Empty or invalid transcript")

            first = records[0]
            title = first.get("content", "Untitled Session")[:200]
            if len(first.get("content", "")) > 200:
                title = first["content"][:197] + "..."

            thread_id = self._upsert_thread(title, file_path)

            messages = self._extract_messages(records)
            msg_count = self._upsert_messages(thread_id, messages)

            memories = self._generate_memories(messages, thread_id)
            mem_count = self._store_memories(thread_id, memories)

            self._log_outcome(file_path, thread_id, msg_count, mem_count)

            return CaptureResult(
                success=True, file_path=file_path,
                thread_id=thread_id, messages_count=msg_count,
                memories_count=mem_count
            )
        except Exception as e:
            logger.error(f"Failed to capture {file_path}: {e}")
            return CaptureResult(success=False, file_path=file_path, error=str(e))

    def _parse_file(self, path) -> Generator[dict, None, None]:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _upsert_thread(self, title: str, file_path: str) -> str:
        import sqlite3
        conn = self._get_conn()

        thread_id = os.path.basename(file_path).replace('.jsonl', '')
        created_at = datetime.now().isoformat()
        meta_json = json.dumps({"source": "opencode_transcript", "path": file_path})

        conn.execute("""
            INSERT OR REPLACE INTO threads (id, title, created_at, updated_at, meta_json)
            VALUES (?, ?, ?, ?, ?)
        """, (thread_id, title[:500], created_at, created_at, meta_json))
        conn.commit()

        return thread_id

    def _upsert_messages(self, thread_id: str, messages: list[dict]) -> int:
        import sqlite3
        conn = self._get_conn()
        count = 0
        for msg in messages:
            msg_id = msg.get("id", f"msg_{self._content_hash(msg['content'])}_{count}")
            content_hash = self._content_hash(msg["content"])
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO messages
                    (id, thread_id, role, content, created_at, meta_json, mode, model)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg_id,
                    thread_id, msg["role"], msg["content"],
                    msg.get("timestamp", datetime.now().isoformat()),
                    msg.get("meta_json", "{}"),
                    msg.get("mode", ""),
                    msg.get("model", ""),
                ))
                count += 1
            except Exception:
                continue
        conn.commit()
        return count

    def _extract_messages(self, records: list[dict]) -> list[dict]:
        messages = []
        for rec in records:
            role = rec.get("role", "user")
            content = rec.get("content", "")
            if not content:
                continue
            messages.append({
                "role": role,
                "content": content,
                "timestamp": rec.get("timestamp", datetime.now().isoformat()),
                "meta": rec.get("meta", {})
            })
        return messages

    def _generate_memories(self, messages: list[dict], thread_id: str) -> list[dict]:
        """Generate semantic memories from message content."""
        chunks = []
        current = ""
        for msg in messages:
            text = f"[{msg['role']}]: {msg['content']}"
            if len(current) + len(text) > 500:
                if current:
                    chunks.append(current)
                current = text
            else:
                current += "\n" + text
        if current:
            chunks.append(current)

        return [
            {
                "content": chunk,
                "kind": "episodic",
                "scope": "session",
                "thread_id": thread_id,
                "tags": [],
                "meta": {}
            }
            for chunk in chunks if chunk.strip()
        ]

    def _store_memories(self, thread_id: str, memories: list[dict]) -> int:
        import sqlite3
        if not memories:
            return 0

        conn = self._get_conn()
        engine = self._get_embedding_engine()
        created_at = datetime.now().isoformat()
        count = 0

        texts = [m["content"] for m in memories]
        vectors = engine.batch_embed(texts)

        import struct
        for i, mem in enumerate(memories):
            content = mem["content"]
            memory_id = f"mem_{self._content_hash(content)}_{thread_id[:8]}"
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO memories
                    (id, kind, scope, thread_id, content, created_at, updated_at,
                     meta_json, tier, tags, score, archived)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    memory_id,
                    mem["kind"], mem["scope"], thread_id, content,
                    created_at, created_at,
                    json.dumps(mem.get("meta", {})),
                    "long_term",
                    json.dumps(mem.get("tags", [])),
                    0.0,
                ))

                vec_blob = struct.pack(f'<{len(vectors[i])}f', *vectors[i])
                conn.execute("""
                    INSERT OR IGNORE INTO memory_embeddings
                    (memory_id, model, dim, vec)
                    VALUES (?, ?, ?, ?)
                """, (memory_id, "n-xyme-embed-768", len(vectors[i]), vec_blob))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store memory: {e}")
                continue
        conn.commit()
        return count

    def _log_outcome(self, file_path: str, thread_id: str, msg_count: int, mem_count: int):
        try:
            import sys
            import time
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from packages.learning_engine.outcome_logger import DelegationOutcome, OutcomeLogger

            outcome = DelegationOutcome(
                task_id=f"capture_{os.path.basename(file_path)[:32]}",
                task_description=f"capture session: {os.path.basename(file_path)}",
                task_type="implementation",
                agent="session_capture",
                level=2,
                success=True,
                latency_ms=0,
                tokens_used=mem_count,
                context={
                    "file_path": file_path,
                    "thread_id": thread_id,
                    "messages_count": msg_count,
                    "memories_count": mem_count,
                },
            )
            logger_outcome = OutcomeLogger(
                db_path=str(Path(__file__).parent.parent.parent.parent / ".sisyphus" / "outcomes.db")
            )
            outcome_id = logger_outcome.log(outcome)
            logger.debug(f"Learning outcome recorded: id={outcome_id}")
        except Exception as e:
            logger.warning(f"Failed to log learning outcome: {e}")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


class TranscriptWatcher:
    """
    Watches transcript directories for new/changed files.
    Polls periodically and triggers SessionCapture on changes.
    """

    def __init__(self, capture: SessionCapture, poll_interval: float = 30.0):
        self.capture = capture
        self.poll_interval = poll_interval
        self._seen_files: dict[str, float] = {}
        self._running = False

    def scan_initial(self):
        """Scan all known files and record their mtimes."""
        for directory in SessionCapture.TRANSCRIPT_DIRS:
            if not os.path.exists(directory):
                continue
            for root, _, files in os.walk(directory):
                for fname in files:
                    if fname.endswith('.jsonl'):
                        path = os.path.join(root, fname)
                        try:
                            self._seen_files[path] = os.path.getmtime(path)
                        except OSError:
                            continue

    def check_and_capture(self) -> list[CaptureResult]:
        """Check for new/changed files and capture them. Returns list of results."""
        results = []
        for directory in SessionCapture.TRANSCRIPT_DIRS:
            if not os.path.exists(directory):
                continue
            for root, _, files in os.walk(directory):
                for fname in files:
                    if not fname.endswith('.jsonl'):
                        continue
                    path = os.path.join(root, fname)
                    try:
                        mtime = os.path.getmtime(path)
                    except OSError:
                        continue

                    is_new = path not in self._seen_files
                    changed = path in self._seen_files and mtime > self._seen_files[path]

                    if is_new or changed:
                        result = self.capture.capture_file(path)
                        results.append(result)
                        self._seen_files[path] = mtime
        return results

    def watch(self, duration: Optional[float] = None, callback=None):
        """
        Start watching. Runs for `duration` seconds (None = forever).
        Calls `callback(results)` after each poll cycle if provided.
        """
        self._running = True
        start = time.time()
        self.scan_initial()

        while self._running:
            results = self.check_and_capture()
            if results and callback:
                callback(results)

            if duration and (time.time() - start) >= duration:
                break
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False