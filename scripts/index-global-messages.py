#!/usr/bin/env python3
import sqlite3
import struct
import json
import subprocess

GLOBAL_DB = "context/opencode/opencode-global.db"
TARGET_DB = "context/memory/mind_from_mind.db"
MODEL = "nomic-embed-text"
DIM = 768
BATCH_SIZE = 10
MAX_CONTENT = 2000


def get_messages():
    conn = sqlite3.connect(GLOBAL_DB)
    cursor = conn.execute("""
        SELECT p.id, p.data, p.time_created, s.title, p2.name
        FROM part p
        LEFT JOIN session s ON p.session_id = s.id
        LEFT JOIN project p2 ON s.project_id = p2.id
        ORDER BY p.time_created DESC
        LIMIT 500
    """)
    messages = []
    for row in cursor.fetchall():
        part_id, data_json, time_created, session_title, project = row
        data = json.loads(data_json)
        content = data.get("text", "")
        role = data.get("role", "unknown")
        created_at = time_created
        messages.append(
            {
                "id": part_id,
                "content": content,
                "role": role,
                "session_title": session_title or "",
                "project": project or "",
                "created_at": created_at,
            }
        )
    conn.close()
    return messages


def generate_embedding(prompt):
    truncated = prompt[:MAX_CONTENT]
    result = subprocess.run(
        [
            "curl",
            "-s",
            "http://localhost:11434/api/embeddings",
            "-d",
            json.dumps({"model": MODEL, "prompt": truncated}),
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return data["embedding"]


def vec_to_blob(vec):
    return struct.pack("<" + "f" * DIM, *vec)


def create_table():
    conn = sqlite3.connect(TARGET_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS global_message_index (
            id TEXT PRIMARY KEY,
            content TEXT,
            role TEXT,
            session_title TEXT,
            project TEXT,
            created_at TEXT,
            vec BLOB
        )
    """)
    conn.commit()
    conn.close()


def insert_messages(messages):
    conn = sqlite3.connect(TARGET_DB)
    total = len(messages)

    for i, msg in enumerate(messages, 1):
        content = msg["content"]
        if not content:
            print(f"Skipping {msg['id']}: empty content")
            continue

        print(f"[{i}/{total}] Embedding message...")
        vec = generate_embedding(content)
        blob = vec_to_blob(vec)

        conn.execute(
            """
            INSERT OR REPLACE INTO global_message_index 
            (id, content, role, session_title, project, created_at, vec)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                msg["id"],
                content,
                msg["role"],
                msg["session_title"],
                msg["project"],
                str(msg["created_at"]),
                blob,
            ),
        )

        if i % BATCH_SIZE == 0:
            conn.commit()
            print(f"Committed batch at {i}")

    conn.commit()
    conn.close()


def verify():
    conn = sqlite3.connect(TARGET_DB)
    count = conn.execute("SELECT COUNT(*) FROM global_message_index").fetchone()[0]
    conn.close()
    return count


def main():
    print("Fetching 500 most recent messages from global DB...")
    messages = get_messages()
    print(f"Retrieved {len(messages)} messages")

    print("Creating global_message_index table...")
    create_table()

    print("Inserting messages with embeddings...")
    insert_messages(messages)

    count = verify()
    print(f"\nVerification: {count} messages indexed")

    if count == 500:
        print("SUCCESS: All 500 messages indexed")
    else:
        print(f"WARNING: Expected 500, got {count}")


if __name__ == "__main__":
    main()
