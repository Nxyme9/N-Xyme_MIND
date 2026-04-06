#!/usr/bin/env python3
import sqlite3
import struct
import json
import subprocess
import sys

DB_PATH = "context/memory/mind_from_mind.db"
MODEL = "nomic-embed-text:latest"
DIM = 768
BATCH_SIZE = 10

def get_missing_memory_ids(conn):
    cursor = conn.execute("""
        SELECT id FROM memories 
        WHERE id NOT IN (SELECT memory_id FROM memory_embeddings)
    """)
    return [row[0] for row in cursor.fetchall()]

def get_memory_content(conn, memory_id):
    cursor = conn.execute("""
        SELECT COALESCE(content, text, '') FROM memories WHERE id = ?
    """, (memory_id,))
    row = cursor.fetchone()
    return row[0] if row else ""

def generate_embedding(prompt):
    result = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/embeddings", "-d", json.dumps({"model": "nomic-embed-text", "prompt": prompt})],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    return data["embedding"]

def vec_to_blob(vec):
    return struct.pack('<' + 'f' * DIM, *vec)

def insert_embedding(conn, memory_id, vec):
    blob = vec_to_blob(vec)
    conn.execute("""
        INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec)
        VALUES (?, ?, ?, ?)
    """, (memory_id, MODEL, DIM, blob))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    
    missing_ids = get_missing_memory_ids(conn)
    total = len(missing_ids)
    
    print(f"Found {total} memories missing embeddings")
    
    for i, mem_id in enumerate(missing_ids, 1):
        content = get_memory_content(conn, mem_id)
        
        if not content:
            print(f"Warning: No content for {mem_id}, skipping")
            continue
        
        print(f"Embedding {i}/{total}...")
        
        vec = generate_embedding(content)
        insert_embedding(conn, mem_id, vec)
    
    conn.close()
    
    conn2 = sqlite3.connect(DB_PATH)
    count = conn2.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
    conn2.close()
    
    print(f"\nVerification: {count}/323 embeddings in database")
    
    if count == 323:
        print("SUCCESS: All 323 memories now have embeddings")
    else:
        print(f"ERROR: Expected 323, got {count}")
        sys.exit(1)

if __name__ == "__main__":
    main()
