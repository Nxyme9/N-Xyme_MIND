"""
DISTILL MEMORY — Local LLM compresses raw data into knowledge.

Takes raw events (clipboard, commands, conversations)
and distills them into meaningful episodes for Graphiti.

Usage:
  python scripts/distill-memory.py                    # Distill all new events
  python scripts/distill-memory.py --clipboard        # Distill clipboard only
  python scripts/distill-memory.py --commands          # Distill command history only
  python scripts/distill-memory.py --conversations    # Distill conversations only
"""
import requests, json, sys, os, time

OLLAMA = "http://localhost:11434/api/chat"
GRAPHITI = "http://localhost:8001/json-rpc"
DISTILL_MODEL = "qwen2.5-coder:7b"  # Fast local model
STATE_FILE = "data/distill-state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"last_clipboard": 0, "last_command": 0, "last_distill": ""}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(state, open(STATE_FILE, 'w'))

def distill(raw_text, category="general"):
    """Use local LLM to distill raw text into meaningful knowledge."""
    prompt = f"""Distill the following into 1-3 concise knowledge points. 
Extract: decisions made, patterns observed, things learned, preferences revealed.
Ignore noise (commands, file paths, timestamps).
Return ONLY the distilled knowledge, no preamble.

Category: {category}
Raw data:
{raw_text[:2000]}

Distilled knowledge:"""

    r = requests.post(OLLAMA, json={
        "model": DISTILL_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": 200}
    }, timeout=30)
    
    if r.status_code == 200:
        return r.json()["message"]["content"].strip()
    return None

def store_episode(text, name, source):
    """Store distilled knowledge in Graphiti."""
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_add_episode", "arguments": {"text": text, "name": name, "source": source}}
    }, timeout=10)
    return r.status_code == 200

def get_recent_graphiti(limit=20):
    """Get recent episodes to avoid duplicating."""
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_list_episodes", "arguments": {"limit": limit}}
    }, timeout=10)
    try:
        data = json.loads(r.json()["result"]["content"][0]["text"])
        return data if isinstance(data, list) else data.get("episodes", [])
    except:
        return []

# Main
state = load_state()
mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

print("=== DISTILL MEMORY ===")
print(f"Model: {DISTILL_MODEL}")
print(f"Mode: {mode}")
print()

distilled = 0

# Distill recent clipboard entries
if mode in ("--all", "--clipboard"):
    print("--- Distilling clipboard ---")
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_search_nodes", "arguments": {"query": "clipboard change", "limit": 10}}
    }, timeout=10)
    try:
        data = json.loads(r.json()["result"]["content"][0]["text"])
        episodes = data.get("episodes", [])
        
        # Group clipboard entries
        clipboard_text = "\n".join(ep.get("text", "")[:200] for ep in episodes[:10])
        
        if clipboard_text.strip():
            distilled_text = distill(clipboard_text, "clipboard")
            if distilled_text:
                name = f"clipboard-distilled-{int(time.time())}"
                if store_episode(distilled_text, name, "distillation"):
                    print(f"  Distilled {len(episodes)} clipboard entries -> 1 episode")
                    distilled += 1
    except:
        print("  No clipboard entries to distill")

# Distill recent command history
if mode in ("--all", "--commands"):
    print("--- Distilling commands ---")
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_search_nodes", "arguments": {"query": "command history batch", "limit": 10}}
    }, timeout=10)
    try:
        data = json.loads(r.json()["result"]["content"][0]["text"])
        episodes = data.get("episodes", [])
        
        commands_text = "\n".join(ep.get("text", "")[:200] for ep in episodes[:10])
        
        if commands_text.strip():
            distilled_text = distill(commands_text, "command history")
            if distilled_text:
                name = f"commands-distilled-{int(time.time())}"
                if store_episode(distilled_text, name, "distillation"):
                    print(f"  Distilled {len(episodes)} command batches -> 1 episode")
                    distilled += 1
    except:
        print("  No commands to distill")

# Distill recent conversations
if mode in ("--all", "--conversations"):
    print("--- Distilling conversations ---")
    r = requests.post(GRAPHITI, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_search_nodes", "arguments": {"query": "session conversation discussion", "limit": 10}}
    }, timeout=10)
    try:
        data = json.loads(r.json()["result"]["content"][0]["text"])
        episodes = data.get("episodes", [])
        
        conv_text = "\n".join(ep.get("text", "")[:300] for ep in episodes[:5])
        
        if conv_text.strip():
            distilled_text = distill(conv_text, "conversations")
            if distilled_text:
                name = f"conversations-distilled-{int(time.time())}"
                if store_episode(distilled_text, name, "distillation"):
                    print(f"  Distilled {len(episodes)} conversations -> 1 episode")
                    distilled += 1
    except:
        print("  No conversations to distill")

print()
print(f"=== RESULT ===")
print(f"Distilled: {distilled} episodes")
print(f"Total episodes: {len(get_recent_graphiti(100))}")

state["last_distill"] = time.strftime("%Y-%m-%d %H:%M:%S")
save_state(state)
