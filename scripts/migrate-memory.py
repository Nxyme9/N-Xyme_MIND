import sqlite3
import json
import requests

GRAPHITI_URL = "http://localhost:8001/json-rpc"
SOURCE_DB = "./data/memory/mind_from_mind.db"

def migrate():
    conn = sqlite3.connect(SOURCE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, kind, scope, content, created_at, tags FROM memories WHERE content IS NOT NULL AND content != ''")
    
    migrated = 0
    errors = 0
    
    for row in cursor.fetchall():
        mem_id, kind, scope, content, created_at, tags = row
        
        metadata = {
            "source": "mind_from_mind",
            "kind": kind,
            "scope": scope,
            "created_at": created_at,
            "tags": tags,
            "original_id": mem_id
        }
        
        try:
            resp = requests.post(GRAPHITI_URL, json={
                "jsonrpc": "2.0",
                "method": "graphiti_add_episode",
                "params": {"text": content[:2000], "metadata": metadata},
                "id": 1
            }, timeout=10)
            
            if resp.status_code == 200:
                migrated += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            print(f"Error: {e}")
    
    conn.close()
    print(f"Done: {migrated} migrated, {errors} errors")

if __name__ == "__main__":
    migrate()
