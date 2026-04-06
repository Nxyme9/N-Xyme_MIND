#!/usr/bin/env python3
"""
Unified Memory Synthesis Script
Pulls all scattered memory from 9 databases into a single consolidated dump.
Outputs to .context/unified-memory-dump.json
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / ".context" / "unified-memory-dump.json"


def db_path(rel):
    return str(ROOT / rel)


def query(db, sql, params=()):
    """Safe query that returns list of dicts."""
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return {"error": str(e)}


def count(db, table):
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        n = cur.fetchone()[0]
        conn.close()
        return n
    except:
        return 0


def synthesize():
    dump = {
        "synthesized_at": datetime.utcnow().isoformat(),
        "source_count": 9,
        "sources": {},
        "unified_memory": {
            "sessions": [],
            "memories": [],
            "preferences": [],
            "projects": [],
            "messages": [],
            "metrics": [],
            "migrations": [],
            "context_files": {},
            "sisyphus_state": {},
        },
        "statistics": {},
    }

    # ===== 1. mind_from_mind.db (Core Memory System) =====
    print("Synthesizing mind_from_mind.db...")
    mfm = db_path("context/memory/mind_from_mind.db")
    dump["sources"]["mind_from_mind"] = {
        "path": "context/memory/mind_from_mind.db",
        "size_mb": round(os.path.getsize(mfm) / 1024 / 1024, 1),
        "tables": {
            "memories": count(mfm, "memories"),
            "messages": count(mfm, "messages"),
            "threads": count(mfm, "threads"),
            "artifacts": count(mfm, "artifacts"),
            "ops": count(mfm, "ops"),
            "memory_embeddings": count(mfm, "memory_embeddings"),
        },
    }

    # Extract all memories
    memories = query(
        mfm,
        "SELECT id, kind, scope, thread_id, content, created_at, updated_at, meta_json, tags FROM memories ORDER BY created_at",
    )
    for m in memories:
        entry = {
            "id": m["id"],
            "kind": m["kind"],
            "scope": m["scope"],
            "content": m["content"][:500] if m["content"] else "",
            "created_at": m["created_at"],
            "tags": m.get("tags", ""),
        }
        if m["kind"] == "preference":
            dump["unified_memory"]["preferences"].append(entry)
        elif m["kind"] in ("note", "summary", "task", "project"):
            dump["unified_memory"]["memories"].append(entry)

    # Extract threads
    threads = query(
        mfm, "SELECT id, title, created_at, meta_json FROM threads ORDER BY created_at"
    )
    dump["unified_memory"]["memory_threads"] = threads

    # ===== 2. opencode-global.db (Global Session History) =====
    print("Synthesizing opencode-global.db...")
    og = db_path("context/opencode/opencode-global.db")
    dump["sources"]["opencode-global"] = {
        "path": "context/opencode/opencode-global.db",
        "size_gb": round(os.path.getsize(og) / 1024 / 1024 / 1024, 2),
        "tables": {
            "sessions": count(og, "session"),
            "messages": count(og, "message"),
            "projects": count(og, "project"),
        },
    }

    # Extract project summaries
    projects = query(
        og,
        """
        SELECT p.name, p.id,
               COUNT(DISTINCT s.id) as session_count,
               COUNT(m.id) as message_count
        FROM project p
        LEFT JOIN session s ON s.project_id = p.id
        LEFT JOIN message m ON m.session_id = s.id
        GROUP BY p.name
        ORDER BY session_count DESC
    """,
    )
    dump["unified_memory"]["projects"] = [
        {
            "name": p.get("name", "unnamed"),
            "sessions": p.get("session_count", 0),
            "messages": p.get("message_count", 0),
        }
        for p in projects
    ]

    # Extract recent sessions (last 50)
    recent_sessions = query(
        og,
        """
        SELECT s.id, s.title, s.created_at, s.updated_at, p.name as project,
               COUNT(m.id) as message_count
        FROM session s
        LEFT JOIN project p ON s.project_id = p.id
        LEFT JOIN message m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT 50
    """,
    )
    dump["unified_memory"]["sessions"] = recent_sessions

    # ===== 3. opencode.db (Local Project Sessions) =====
    print("Synthesizing opencode.db...")
    ol = db_path("context/opencode/opencode.db")
    dump["sources"]["opencode-local"] = {
        "path": "context/opencode/opencode.db",
        "size_mb": round(os.path.getsize(ol) / 1024 / 1024, 1),
        "tables": {
            "sessions": count(ol, "session"),
            "messages": count(ol, "message"),
            "projects": count(ol, "project"),
        },
    }

    local_sessions = query(
        ol,
        """
        SELECT s.id, s.title, s.created_at, s.updated_at, p.name as project,
               COUNT(m.id) as message_count
        FROM session s
        LEFT JOIN project p ON s.project_id = p.id
        LEFT JOIN message m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT 30
    """,
    )
    dump["unified_memory"]["local_sessions"] = local_sessions

    # ===== 4. memory_migration.db =====
    print("Synthesizing memory_migration.db...")
    mm = db_path("data/memory_migration.db")
    dump["sources"]["memory_migration"] = {
        "path": "data/memory_migration.db",
        "size_mb": round(os.path.getsize(mm) / 1024 / 1024, 1),
        "tables": {
            "migrations": count(mm, "migrations"),
            "migration_status": count(mm, "migration_status"),
            "transcript_index": count(mm, "transcript_index"),
        },
    }

    migrations = query(mm, "SELECT * FROM migrations ORDER BY created_at DESC LIMIT 50")
    dump["unified_memory"]["migrations"] = migrations

    # ===== 5. nxm_from_mind.db =====
    print("Synthesizing nxm_from_mind.db...")
    nxm = db_path("context/memory/nxm_from_mind.db")
    dump["sources"]["nxm_from_mind"] = {
        "path": "context/memory/nxm_from_mind.db",
        "size_kb": round(os.path.getsize(nxm) / 1024, 0),
        "tables": {
            "memory_facts": count(nxm, "memory_facts"),
            "settings": count(nxm, "settings"),
            "threads": count(nxm, "threads"),
        },
    }

    facts = query(nxm, "SELECT * FROM memory_facts")
    dump["unified_memory"]["memory_facts"] = facts

    # ===== 6. orchestrator.db =====
    print("Synthesizing orchestrator.db...")
    orch = db_path("modelrouter/data/orchestrator.db")
    dump["sources"]["orchestrator"] = {
        "path": "modelrouter/data/orchestrator.db",
        "size_kb": round(os.path.getsize(orch) / 1024, 0),
        "tables": {
            "orchestration_sessions": count(orch, "orchestration_sessions"),
            "model_stats": count(orch, "model_stats"),
            "token_log": count(orch, "token_log"),
            "vpn_history": count(orch, "vpn_history"),
            "api_keys": count(orch, "api_keys"),
            "instance_stats": count(orch, "instance_stats"),
        },
    }

    # ===== 7. jarvis_memory.db =====
    print("Synthesizing jarvis_memory.db...")
    jm = db_path("context/memory/jarvis_memory.db")
    dump["sources"]["jarvis_memory"] = {
        "path": "context/memory/jarvis_memory.db",
        "size_kb": round(os.path.getsize(jm) / 1024, 0),
        "tables": {
            "conversation_history": count(jm, "conversation_history"),
            "episodes": count(jm, "episodes"),
            "facts": count(jm, "facts"),
        },
    }

    # ===== 8. jarvis_events.db =====
    print("Synthesizing jarvis_events.db...")
    je = db_path("context/memory/jarvis_events.db")
    dump["sources"]["jarvis_events"] = {
        "path": "context/memory/jarvis_events.db",
        "size_kb": round(os.path.getsize(je) / 1024, 0),
        "tables": {"event_log": count(je, "event_log")},
    }

    # ===== 9. nervous_system.db =====
    print("Synthesizing nervous_system.db...")
    ns = db_path("data/nervous_system.db")
    dump["sources"]["nervous_system"] = {
        "path": "data/nervous_system.db",
        "size_kb": round(os.path.getsize(ns) / 1024, 0),
        "tables": {
            "metrics": count(ns, "metrics"),
            "actions": count(ns, "actions"),
            "agent_alerts": count(ns, "agent_alerts"),
            "metrics_hourly": count(ns, "metrics_hourly"),
        },
    }

    # ===== Statistics =====
    dump["statistics"] = {
        "total_sessions_global": dump["sources"]["opencode-global"]["tables"][
            "sessions"
        ],
        "total_messages_global": dump["sources"]["opencode-global"]["tables"][
            "messages"
        ],
        "total_sessions_local": dump["sources"]["opencode-local"]["tables"]["sessions"],
        "total_messages_local": dump["sources"]["opencode-local"]["tables"]["messages"],
        "total_memories": len(dump["unified_memory"]["memories"]),
        "total_preferences": len(dump["unified_memory"]["preferences"]),
        "total_projects": len(dump["unified_memory"]["projects"]),
        "total_migrations": dump["sources"]["memory_migration"]["tables"]["migrations"],
        "total_threads_mfm": dump["sources"]["mind_from_mind"]["tables"]["threads"],
        "total_data_size_gb": round(
            os.path.getsize(og) / 1024 / 1024 / 1024
            + os.path.getsize(ol) / 1024 / 1024 / 1024
            + os.path.getsize(mfm) / 1024 / 1024 / 1024
            + os.path.getsize(mm) / 1024 / 1024 / 1024,
            2,
        ),
    }

    # Write dump
    with open(OUTPUT, "w") as f:
        json.dump(dump, f, indent=2, default=str)

    print(f"\n✅ Unified memory dump written to: {OUTPUT}")
    print(f"📊 Statistics:")
    for k, v in dump["statistics"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    synthesize()
