"""Episode embedding backfill — BATCH MODE (58x faster)."""
import requests, sys, time

N = "http://localhost:7474/db/neo4j/tx/commit"
O = "http://localhost:11434/api/embed"

def batch_embed(texts):
    """Batch embed multiple texts at once."""
    prefixed = ["search_document: " + (t or "")[:500] for t in texts]
    r = requests.post(O, json={"model": "nomic-embed-text:latest", "input": prefixed})
    if r.status_code == 200:
        return r.json().get("embeddings", [])
    return []

def get_unembedded(limit=50):
    r = requests.post(N, json={"statements": [{"statement": f"MATCH (e:Episode) WHERE e.embedding IS NULL RETURN e.id, substring(e.text,0,200) LIMIT {limit}"}]})
    return [(row["row"][0], row["row"][1]) for row in r.json()["results"][0]["data"]]

def get_counts():
    r = requests.post(N, json={"statements": [
        {"statement": "MATCH (e:Episode) RETURN count(e)"},
        {"statement": "MATCH (e:Episode) WHERE e.embedding IS NOT NULL RETURN count(e)"}
    ]})
    res = r.json()["results"]
    return res[0]["data"][0]["row"][0], res[1]["data"][0]["row"][0]

total, embedded = get_counts()
print(f"Starting: {embedded}/{total} ({embedded/total*100:.0f}%)")

batch_num = 0
while True:
    episodes = get_unembedded(50)
    if not episodes:
        print("100% complete!")
        break
    
    batch_num += 1
    ids = [e[0] for e in episodes]
    texts = [e[1] for e in episodes]
    
    t1 = time.time()
    embeddings = batch_embed(texts)
    t2 = time.time()
    
    updated = 0
    for eid, emb in zip(ids, embeddings):
        if emb:
            requests.post(N, json={"statements": [{"statement": "MATCH (e:Episode {id: $id}) SET e.embedding = $emb", "parameters": {"id": eid, "emb": emb}}]})
            updated += 1
    
    total, embedded = get_counts()
    remaining = total - embedded
    print(f"Batch {batch_num}: {updated}/{len(episodes)} in {t2-t1:.1f}s ({(t2-t1)/len(episodes)*1000:.0f}ms/ea) | Total: {embedded}/{total} ({embedded/total*100:.0f}%) | Remaining: {remaining}")
