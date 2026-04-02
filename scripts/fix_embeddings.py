#!/usr/bin/env python3
"""Fix embeddings for all episodes in Neo4j using nomic-embed-text."""

import requests
import json
import time

NEO4J_URL = "http://localhost:7474/db/neo4j/tx/commit"
OLLAMA_URL = "http://localhost:11434/api/embeddings"
AUTH = "bmVvNGo6cGFzc3dvcmQ="  # neo4j:password base64

def neo4j_query(query, params=None):
    """Execute Neo4j query."""
    headers = {"Content-Type": "application/json", "Authorization": f"Basic {AUTH}"}
    payload = {"statements": [{"statement": query, "parameters": params or {}}]}
    resp = requests.post(NEO4J_URL, json=payload, headers=headers, timeout=30)
    return resp.json()

def get_embedding(text):
    """Get embedding from Ollama."""
    resp = requests.post(OLLAMA_URL, json={"model": "nomic-embed-text:latest", "prompt": text}, timeout=30)
    return resp.json().get("embedding")

def main():
    print("Getting episodes without embeddings...")
    result = neo4j_query("MATCH (e:Episode) WHERE e.embedding IS NULL AND e.text IS NOT NULL RETURN e.id as id, e.text as text LIMIT 100")
    episodes = result["results"][0]["data"]
    
    print(f"Found {len(episodes)} episodes to embed")
    
    success = 0
    failed = 0
    
    for i, row in enumerate(episodes):
        ep_id = row["row"][0]
        text = row["row"][1]
        
        if not text or len(text) < 10:
            continue
        
        try:
            embedding = get_embedding(text[:500])  # Limit text length
            if embedding:
                # Update episode with embedding
                neo4j_query("MATCH (e:Episode {id: $id}) SET e.embedding = $embedding", {"id": ep_id, "embedding": embedding})
                success += 1
                if success % 10 == 0:
                    print(f"  Embedded {success} episodes...")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  Error embedding {ep_id}: {e}")
        
        time.sleep(0.1)  # Rate limit
    
    print(f"\nDone! Embedded {success} episodes, {failed} failed")

if __name__ == "__main__":
    main()
