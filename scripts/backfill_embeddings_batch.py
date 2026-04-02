#!/usr/bin/env python3
"""Backfill embeddings for all episodes in Neo4j. Batch processing to avoid timeout."""

import requests
import json
import time
import sys

NEO4J_URL = "http://localhost:7474/db/neo4j/tx/commit"
OLLAMA_URL = "http://localhost:11434/api/embeddings"
AUTH = "bmVvNGo6cGFzc3dvcmQ="

def neo4j_query(query, params=None):
    headers = {"Content-Type": "application/json", "Authorization": f"Basic {AUTH}"}
    payload = {"statements": [{"statement": query, "parameters": params or {}}]}
    resp = requests.post(NEO4J_URL, json=payload, headers=headers, timeout=30)
    return resp.json()

def get_embedding(text):
    resp = requests.post(OLLAMA_URL, json={"model": "nomic-embed-text:latest", "prompt": text[:500]}, timeout=30)
    return resp.json().get("embedding")

def count_without_embeddings():
    result = neo4j_query("MATCH (e:Episode) WHERE e.embedding IS NULL AND e.text IS NOT NULL RETURN count(e) as cnt")
    return result["results"][0]["data"][0]["row"][0]

def get_batch(batch_size=20):
    result = neo4j_query(f"MATCH (e:Episode) WHERE e.embedding IS NULL AND e.text IS NOT NULL RETURN e.id as id, e.text as text LIMIT {batch_size}")
    return result["results"][0]["data"]

def save_embedding(ep_id, embedding):
    neo4j_query("MATCH (e:Episode {id: $id}) SET e.embedding = $embedding", {"id": ep_id, "embedding": embedding})

def main():
    total = count_without_embeddings()
    print(f"Episodes needing embeddings: {total}")
    
    success = 0
    failed = 0
    batch_num = 0
    
    while True:
        episodes = get_batch(20)
        if not episodes:
            break
        
        batch_num += 1
        print(f"Batch {batch_num}: Processing {len(episodes)} episodes...")
        
        for row in episodes:
            ep_id = row["row"][0]
            text = row["row"][1]
            
            if not text or len(text) < 5:
                continue
            
            try:
                embedding = get_embedding(text)
                if embedding:
                    save_embedding(ep_id, embedding)
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
            
            time.sleep(0.05)
        
        remaining = count_without_embeddings()
        print(f"  Done batch {batch_num}. Success: {success}, Failed: {failed}, Remaining: {remaining}")
        
        if remaining == 0:
            break
    
    print(f"\nComplete! Embedded {success} episodes, {failed} failed")

if __name__ == "__main__":
    main()
