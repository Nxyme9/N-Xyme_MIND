"""
Pattern Extractor v2 — SIMPLIFIED.
Uses LLM directly to find patterns from episodes.
No complex similarity matching. Just feed episodes to LLM.
"""
import requests, json, sys, time

GRAPHITI = "http://localhost:8001/json-rpc"
OLLAMA = "http://localhost:11434/api/chat"
MODEL = "qwen2.5-coder:7b"

def get_episodes(limit=30):
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_list_episodes", "arguments": {"limit": limit}}
    }, timeout=30)
    data = json.loads(r.json()["result"]["content"][0]["text"])
    return data if isinstance(data, list) else data.get("episodes", [])

def extract_patterns(episodes):
    """Feed episodes to LLM, ask for patterns."""
    combined = "\n---\n".join(ep.get("text", "")[:200] for ep in episodes[:20])
    
    prompt = f"""Analyze these development session episodes. Find patterns.

Rules:
- Only report patterns seen 2+ times
- Be specific (file names, error types, timing)
- Format: "PATTERN: [when X happens, Y follows] (seen N times)"

Episodes:
{combined[:3000]}

Patterns found:"""

    r = requests.post(OLLAMA, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": 500}
    }, timeout=30)
    
    if r.status_code == 200:
        return r.json()["message"]["content"].strip()
    return None

def store_pattern(text):
    """Store pattern in Graphiti."""
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_add_episode", "arguments": {"text": text, "name": f"pattern-{int(time.time())}", "source": "pattern"}}
    }, timeout=10)
    return r.status_code == 200

# Main
print("=" * 60)
print("PATTERN EXTRACTOR v2")
print("=" * 60)
print()

episodes = get_episodes(30)
print(f"[INFO] Fetched {len(episodes)} episodes")

patterns = extract_patterns(episodes)
if patterns:
    print(f"\nPATTERNS FOUND:\n{patterns[:500]}")
    if store_pattern(patterns):
        print(f"\n[INFO] Stored in Graphiti")
    else:
        print(f"\n[WARN] Failed to store")
else:
    print("[INFO] No patterns found")

print("\n[DONE]")
