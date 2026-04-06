#!/usr/bin/env python3
"""
Session Import Pipeline — Import OpenCode sessions into MIND memory system.

Reads sessions from OpenCode SQLite DB, extracts content, chunks, embeds,
and stores in existing MIND infrastructure (ChromaDB + SQLite + knowledge graph).

Usage:
    python scripts/import-sessions.py [--dry-run] [--limit N] [--force]
"""

import argparse
import json
import logging
import os
import sqlite3
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

OPENCODE_DB = Path(
    os.environ.get(
        "OPENCODE_DB", str(Path.home() / ".local/share/opencode/opencode.db")
    )
)
MEMORY_DB = Path(
    os.environ.get(
        "NX_MIND_DB_PATH",
        str(Path(__file__).parent.parent / "context/memory/mind_from_mind.db"),
    )
)
EMBED_DIM = 768
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"
BATCH_SIZE = 100

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory.chunker import chunk_text
from memory.knowledge_graph import KnowledgeGraph


def get_opencode_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(OPENCODE_DB))


def get_memory_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def get_project_id() -> Optional[str]:
    """Find the project ID for N-Xyme_MIND."""
    conn = get_opencode_connection()
    cursor = conn.execute(
        "SELECT id FROM project WHERE worktree LIKE ? LIMIT 1",
        ("%N-Xyme_MIND%",),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
    """Find the project ID for N-Xyme_MIND."""
    cursor = conn.execute(
        "SELECT id FROM project WHERE worktree LIKE ? LIMIT 1",
        ("%N-Xyme_MIND%",),
    )
    cursor = conn.execute(
        "SELECT id FROM project WHERE worktree LIKE ? LIMIT 1",
        ("%N-Xyme_MIND%",),
        ("%N-Xyme_MIND%",),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_main_sessions(project_id: str) -> list[dict]:
    """Get all main sessions (not subagent sessions) for the project."""
    conn = get_opencode_connection()
    cursor = conn.execute(
        """
        SELECT id, title, time_created, time_updated, summary_additions, 
               summary_deletions, summary_files, summary_diffs
        FROM session 
        WHERE project_id = ? AND parent_id IS NULL
        ORDER BY time_created DESC
        """,
        (project_id,),
    )
    sessions = [
        dict(
            zip(
                [
                    "id",
                    "title",
                    "time_created",
                    "time_updated",
                    "summary_additions",
                    "summary_deletions",
                    "summary_files",
                    "summary_diffs",
                ],
                row,
            )
        )
        for row in cursor.fetchall()
    ]
    conn.close()
    return sessions


def get_session_messages(session_id: str, batch_size: int = BATCH_SIZE) -> list[dict]:
    """Get messages for a session in batches."""
    conn = get_opencode_connection()
    cursor = conn.execute(
        """
        SELECT id, time_created, data FROM message 
        WHERE session_id = ? 
        ORDER BY time_created ASC
        """,
        (session_id,),
    )
    messages = []
    for row in cursor.fetchall():
        msg_id, time_created, data = row
        try:
            data_json = json.loads(data)
            messages.append(
                {
                    "id": msg_id,
                    "time_created": time_created,
                    "data": data_json,
                }
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse message data for {msg_id}")
    conn.close()
    return messages


def extract_key_content(messages: list[dict]) -> str:
    """Extract key content from messages.

    Extracts:
    - User requests (role='user')
    - Tool calls
    - Summary diffs (code changes)
    - Assistant responses
    """
    parts = []

    for msg in messages:
        data = msg.get("data", {})
        role = data.get("role", "")

        if role == "user":
            agent = data.get("agent", "")
            time_info = data.get("time", {})
            parts.append(f"## User Request (via {agent})")

            summary = data.get("summary", {})
            diffs = summary.get("diffs", [])
            if diffs:
                for diff in diffs[:3]:
                    file_path = diff.get("file", "unknown")
                    before = diff.get("before", "")[:500]
                    after = diff.get("after", "")[:500]
                    parts.append(f"### Diff: {file_path}")
                    if before:
                        parts.append(f"```python\n{before}\n```")
                    if after:
                        parts.append(f"```python\n{after}\n```")

        elif role == "assistant":
            agent = data.get("agent", data.get("mode", ""))
            path = data.get("path", {})
            cwd = path.get("cwd", "")
            model = data.get("modelID", data.get("model", {}).get("modelID", "unknown"))
            tokens = data.get("tokens", {})
            total_tokens = tokens.get("total", 0)
            finish = data.get("finish", "")

            parts.append(f"## Assistant ({agent}, {model}, {total_tokens} tokens)")
            if cwd:
                parts.append(f"Working directory: {cwd}")
            if finish:
                parts.append(f"Finish reason: {finish}")

            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls[:5]:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", "")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            pass
                    parts.append(f"### Tool Call: {name}")
                    parts.append(f"```json\n{json.dumps(args, indent=2)[:500]}\n```")

    return "\n\n".join(parts)
    """Extract key content from messages.

    Extracts:
    - User requests (role='user')
    - Tool calls (function calls)
    - Important assistant responses (decisions, code)
    - Code changes (if present in data)
    """
    parts = []

    for msg in messages:
        data = msg.get("data", {})
        role = data.get("role", "")
        content = data.get("content", "")

        if role == "user" and content:
            parts.append(f"## User Request\n{content}")

        elif role == "assistant":
            tool_calls = data.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", "")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            pass
                    parts.append(
                        f"## Tool Call: {name}\n{json.dumps(args, indent=2)[:500]}"
                    )

            if content:
                if len(content) > 200:
                    parts.append(f"## Assistant Response\n{content[:1000]}...")
                else:
                    parts.append(f"## Assistant Response\n{content}")

            text = data.get("text", "")
            if text and text != content:
                if len(text) > 200:
                    parts.append(f"## Text Response\n{text[:1000]}...")
                else:
                    parts.append(f"## Text Response\n{text}")

        elif role == "tool":
            content_id = data.get("content", "")
            if content_id:
                parts.append(f"## Tool Result\n[Tool output: {content_id[:500]}]")

    return "\n\n".join(parts)


def check_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def embed_via_ollama(text: str) -> Optional[list[float]]:
    """Generate embedding via Ollama."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": OLLAMA_MODEL, "prompt": text[:8192]},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if embedding and len(embedding) == EMBED_DIM:
                return embedding
    except Exception as e:
        logger.debug(f"Ollama embedding failed: {e}")
    return None


def save_memory(memory_id: str, content: str, session_id: str, metadata: dict) -> bool:
    """Save memory to SQLite and embed."""
    conn = get_memory_connection()
    now = datetime.utcnow().isoformat()

    try:
        conn.execute(
            """INSERT OR REPLACE INTO memories 
               (id, kind, scope, thread_id, content, created_at, updated_at, meta_json, text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                "session",
                "global",
                session_id,
                content,
                now,
                now,
                json.dumps(metadata),
                content[:1000],
            ),
        )
        conn.commit()
        conn.close()

        embedding = embed_via_ollama(content)
        if embedding:
            vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)
            conn = get_memory_connection()
            conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec) VALUES (?, ?, ?, ?)",
                (memory_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
            )
            conn.commit()
            conn.close()
            return True
        else:
            logger.warning(f"Failed to embed memory {memory_id}")
            return False

    except Exception as e:
        logger.error(f"Failed to save memory {memory_id}: {e}")
        return False


def is_session_imported(session_id: str) -> bool:
    """Check if session has already been imported."""
    conn = get_memory_connection()
    cursor = conn.execute(
        "SELECT 1 FROM memories WHERE thread_id = ? AND kind = 'session' LIMIT 1",
        (session_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def import_session(session_id: str, dry_run: bool = False) -> tuple[int, int]:
    """Import a single session: chunk, embed, store.

    Returns: (chunks_count, success_count)
    """
    if is_session_imported(session_id):
        logger.debug(f"Session {session_id} already imported, skipping")
        return (0, 0)

    messages = get_session_messages(session_id)
    if not messages:
        logger.warning(f"No messages for session {session_id}")
        return (0, 0)

    content = extract_key_content(messages)
    if not content.strip():
        logger.warning(f"No extractable content for session {session_id}")
        return (0, 0)

    session_conn = get_opencode_connection()
    cursor = session_conn.execute(
        "SELECT title, summary_additions, summary_deletions, summary_files FROM session WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    session_conn.close()

    title = row[0] if row else "Unknown"
    summary_additions = row[1] if row else 0
    summary_deletions = row[2] if row else 0
    summary_files = row[3] if row else 0

    metadata = {
        "session_id": session_id,
        "title": title,
        "message_count": len(messages),
        "summary_additions": summary_additions,
        "summary_deletions": summary_deletions,
        "summary_files": summary_files,
        "source": "opencode_session",
    }

    chunks = chunk_text(content, f"session:{session_id}")
    success_count = 0

    for chunk in chunks:
        chunk_text_val = chunk["text"]
        memory_id = f"session_{session_id}_chunk_{chunk['chunk_index']}"

        if not dry_run:
            if save_memory(memory_id, chunk_text_val, session_id, metadata):
                success_count += 1
        else:
            success_count += 1

    return (len(chunks), success_count)


def update_knowledge_graph(sessions_imported: list[dict]) -> dict:
    """Add session entities to knowledge graph."""
    graph = KnowledgeGraph()

    for session in sessions_imported:
        session_id = session["session_id"]
        title = session.get("title", "Unknown")

        graph.add_entity(
            f"session:{session_id}",
            "concept",
            {"title": title, "source": "imported_session"},
        )

        if "python" in title.lower():
            graph.add_relationship(f"session:{session_id}", "Python", "relates_to")

    return graph.save()


def main():
    parser = argparse.ArgumentParser(description="Import OpenCode sessions to MIND")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of sessions to import"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-import already imported sessions"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not OPENCODE_DB.exists():
        logger.error(f"OpenCode DB not found at {OPENCODE_DB}")
        sys.exit(1)

    if not check_ollama_available():
        logger.warning("Ollama not available - embeddings will fail")

    project_id = get_project_id()
    if not project_id:
        logger.error("Could not find N-Xyme_MIND project")
        sys.exit(1)

    sessions = get_main_sessions(project_id)
    logger.info(f"Found {len(sessions)} main sessions")

    if args.force:
        sessions_to_import = sessions[: args.limit] if args.limit > 0 else sessions
    else:
        sessions_to_import = [s for s in sessions if not is_session_imported(s["id"])]
        if args.limit > 0:
            sessions_to_import = sessions_to_import[: args.limit]

    logger.info(f"Importing {len(sessions_to_import)} sessions")

    total_chunks = 0
    total_success = 0
    imported_sessions = []

    for i, session in enumerate(sessions_to_import):
        session_id = session["id"]

        chunks, success = import_session(session_id, dry_run=args.dry_run)
        total_chunks += chunks
        total_success += success

        if success > 0:
            imported_sessions.append(
                {
                    "session_id": session_id,
                    "title": session.get("title", "Unknown"),
                }
            )

        if (i + 1) % 10 == 0:
            logger.info(
                f"Progress: {i + 1}/{len(sessions_to_import)} sessions, {total_chunks} chunks"
            )

    if imported_sessions and not args.dry_run:
        kg_result = update_knowledge_graph(imported_sessions)
        logger.info(f"Knowledge graph updated: {kg_result}")

    logger.info(
        f"Import complete: {len(imported_sessions)} sessions, {total_chunks} chunks, {total_success} stored"
    )

    if args.dry_run:
        logger.info("Dry run - no data was saved")


if __name__ == "__main__":
    main()
