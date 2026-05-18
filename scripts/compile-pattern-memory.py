#!/usr/bin/env python3
"""
compile-pattern-memory.py — Store and retrieve compile patterns with embeddings.

This is the memory layer for the compile-feedback loop:
  - Stores compile results as embedded memory vectors
  - Retrieves similar past compilations by semantic search
  - Tracks agent-specific compile success rates
  - Feeds patterns into next compilation iteration

Usage:
  # Store a compile result
  ./scripts/compile-pattern-memory.py store <feedback.json>

  # Search for similar patterns
  ./scripts/compile-pattern-memory.py search <query> [--k 5]

  # Get agent compile stats
  ./scripts/compile-pattern-memory.py stats <agent_name>

  # List recent failures for an agent
  ./scripts/compile-pattern-memory.py failures <agent_name> [--limit 10]
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "data" / "memory"
COMPILE_MEMORY_FILE = MEMORY_DIR / "compile-patterns.jsonl"
COMPILE_EMBEDDINGS_DIR = MEMORY_DIR / "embeddings" / "compile"
HOLOGRAPHIC_FILE = MEMORY_DIR / "holographic-memory.json"
CONSCIOUSNESS_DIR = MEMORY_DIR / "consciousness"

os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(COMPILE_EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(CONSCIOUSNESS_DIR, exist_ok=True)


def ensure_file(path):
    if not path.exists():
        path.write_text("")


def load_jsonl(path):
    ensure_file(path)
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return results


def append_jsonl(path, entry):
    ensure_file(path)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_holographic():
    ensure_file(HOLOGRAPHIC_FILE)
    try:
        return json.loads(HOLOGRAPHIC_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_holographic(data):
    HOLOGRAPHIC_FILE.write_text(json.dumps(data, indent=2))


# ── Embedding helper (calls Mojo or local) ────────────────────────────────

def embed_text(text: str) -> list:
    """Generate embedding vector for text.
    
    Tries Mojo native embed first, falls back to a simple
    token-based hash embedding for offline use.
    """
    # Try Mojo daemon embed if available
    try:
        import subprocess
        result = subprocess.run(
            [str(PROJECT_ROOT / "services" / "mojo-router" / "src" / "daemon")],
            input=json.dumps({"type": "embed", "text": text}) + "\n",
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            if "embedding" in data:
                return data["embedding"]
    except Exception:
        pass

    # Fallback: write to Mojo CLI for embed
    try:
        mojo = os.path.expanduser("~/.local/bin/mojo")
        if os.path.exists(mojo):
            embed_script = COMPILE_EMBEDDINGS_DIR / "_embed.mojo"
            if not embed_script.exists():
                embed_script.write_text('''
from std.python import Python
def main():
    py = Python.interpret("import sys, json; text = sys.stdin.read(); print(json.dumps([hash(text[i:i+4]) %% 1000 / 1000.0 for i in range(0, min(len(text), 384), 1)]))")
    print(py)
''')
            result = subprocess.run(
                [mojo, str(embed_script)],
                input=text, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout.strip())
    except Exception:
        pass

    # Simple fallback embedding (deterministic)
    import hashlib
    dim = 384
    vec = [0.0] * dim
    words = text.split()
    for i, word in enumerate(words):
        h = hashlib.md5(word.encode()).digest()
        for j in range(min(4, dim)):
            vec[(i + j) % dim] += (h[j] / 255.0) * 2 - 1
    # Normalize
    mag = sum(v*v for v in vec) ** 0.5
    if mag > 0:
        vec = [v / mag for v in vec]
    return vec


# ── Store compile feedback ────────────────────────────────────────────────

def store_feedback(feedback: dict):
    """Store a compile result as memory.
    
    Writes to:
      1. compile-patterns.jsonl (vector store)
      2. holographic-memory.json (general memory)
      3. consciousness/<agent>.json (agent stats)
    """
    source = feedback.get("source", "unknown")
    agent = feedback.get("agent", "unknown")
    task = feedback.get("task", "compile")
    success = feedback.get("success", False)
    errors = feedback.get("errors", [])
    warnings = feedback.get("warnings", [])
    duration_ms = feedback.get("duration_ms", 0)
    
    # Build content for embedding
    error_text = "; ".join(errors[:5]) if errors else "no errors"
    warning_text = "; ".join(warnings[:3]) if warnings else "no warnings"
    content = (
        f"agent={agent} task={task} source={source} "
        f"success={'yes' if success else 'no'} "
        f"errors=[{error_text}] "
        f"warnings=[{warning_text}] "
        f"duration={duration_ms}ms"
    )
    
    # Generate embedding
    vector = embed_text(content)
    
    # Timestamp
    ts = time.time()
    date_str = time.strftime("%Y-%m-%d", time.gmtime(ts))
    
    # 1. Store in compile-patterns.jsonl
    entry = {
        "content": content,
        "vector": vector,
        "dim": len(vector),
        "id": f"compile-{agent}-{int(ts)}",
        "agent": agent,
        "task": task,
        "source": source,
        "success": success,
        "errors": errors[:10],
        "warnings": warnings[:10],
        "duration_ms": duration_ms,
        "date": date_str,
        "ts": ts,
        "type": "compile-feedback"
    }
    append_jsonl(COMPILE_MEMORY_FILE, entry)
    
    # 2. Store in holographic memory
    holo = load_holographic()
    holo_entry = {
        "id": f"compile-{agent}-{int(ts)}",
        "content": content,
        "category": "compile-feedback",
        "agent": agent,
        "success": success,
        "timestamp": ts
    }
    holo.append(holo_entry)
    # Keep last 1000 entries
    if len(holo) > 1000:
        holo = holo[-1000:]
    save_holographic(holo)
    
    # 3. Update agent consciousness
    update_agent_consciousness(agent, task, success, duration_ms)
    
    return entry


def update_agent_consciousness(agent: str, task: str, success: bool, duration_ms: int):
    """Track per-agent compile success/failure."""
    consciousness_file = CONSCIOUSNESS_DIR / f"{agent.replace(' ', '_')}.json"
    
    if consciousness_file.exists():
        try:
            data = json.loads(consciousness_file.read_text())
        except json.JSONDecodeError:
            data = {"agent": agent, "outcomes": []}
    else:
        data = {"agent": agent, "outcomes": []}
    
    data["outcomes"].append({
        "task": task[:200],
        "type": "compile",
        "success": success,
        "latency_ms": duration_ms,
        "timestamp": time.time()
    })
    
    # Calculate stats
    total = len(data["outcomes"])
    successes = sum(1 for o in data["outcomes"] if o["success"])
    data["total_tasks"] = total
    data["successes"] = successes
    data["failures"] = total - successes
    data["success_rate"] = successes / total if total > 0 else 0.0
    data["last_updated"] = time.time()
    
    consciousness_file.write_text(json.dumps(data, indent=2))


# ── Search ────────────────────────────────────────────────────────────────

def search(query: str, k: int = 5, agent: str = None):
    """Search compile patterns by semantic similarity."""
    query_vec = embed_text(query)
    patterns = load_jsonl(COMPILE_MEMORY_FILE)
    
    if agent:
        patterns = [p for p in patterns if p.get("agent") == agent]
    
    if not patterns:
        return []
    
    # Cosine similarity
    scored = []
    for p in patterns:
        p_vec = p.get("vector", [])
        if not p_vec or len(p_vec) != len(query_vec):
            continue
        dot = sum(a * b for a, b in zip(query_vec, p_vec))
        q_mag = sum(v*v for v in query_vec) ** 0.5
        p_mag = sum(v*v for v in p_vec) ** 0.5
        if q_mag > 0 and p_mag > 0:
            sim = dot / (q_mag * p_mag)
            scored.append((sim, p))
    
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def get_agent_stats(agent: str):
    """Get compile stats for an agent."""
    consciousness_file = CONSCIOUSNESS_DIR / f"{agent.replace(' ', '_')}.json"
    if consciousness_file.exists():
        return json.loads(consciousness_file.read_text())
    return {"agent": agent, "outcomes": [], "total_tasks": 0, "successes": 0, "failures": 0}


def get_recent_failures(agent: str, limit: int = 10):
    """Get recent compile failures for an agent."""
    patterns = load_jsonl(COMPILE_MEMORY_FILE)
    agent_patterns = [p for p in patterns if p.get("agent") == agent and not p.get("success")]
    agent_patterns.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return agent_patterns[:limit]


def format_patterns_for_prompt(patterns: list, max_chars: int = 2000) -> str:
    """Format matched patterns into a prompt injection string."""
    if not patterns:
        return ""
    
    lines = ["## Similar compilation patterns from memory:"]
    for score, p in patterns[:5]:
        status = "✅" if p.get("success") else "❌"
        errors = p.get("errors", [])
        err_str = "; ".join(errors[:2]) if errors else "clean"
        lines.append(
            f"- {status} [{p.get('source', '?')}] "
            f"agent={p.get('agent', '?')} "
            f"duration={p.get('duration_ms', '?')}ms "
            f"errors={err_str[:100]}"
        )
    
    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    return result


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compile pattern memory")
    sub = parser.add_subparsers(dest="command")
    
    # store
    store_p = sub.add_parser("store", help="Store compile feedback")
    store_p.add_argument("feedback_file", help="JSON feedback file from compile-feedback.sh")
    
    # search
    search_p = sub.add_parser("search", help="Search compile patterns")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--k", type=int, default=5)
    search_p.add_argument("--agent", default=None)
    
    # stats
    stats_p = sub.add_parser("stats", help="Agent compile stats")
    stats_p.add_argument("agent", help="Agent name")
    
    # failures
    fail_p = sub.add_parser("failures", help="Recent compile failures")
    fail_p.add_argument("agent", help="Agent name")
    fail_p.add_argument("--limit", type=int, default=10)
    
    # format-prompt
    fmt_p = sub.add_parser("format-prompt", help="Format patterns for prompt injection")
    fmt_p.add_argument("query", help="Search query")
    fmt_p.add_argument("--k", type=int, default=5)
    fmt_p.add_argument("--agent", default=None)
    fmt_p.add_argument("--max-chars", type=int, default=2000)
    
    args = parser.parse_args()
    
    if args.command == "store":
        feedback = json.loads(Path(args.feedback_file).read_text())
        result = store_feedback(feedback)
        print(json.dumps({"status": "stored", "id": result["id"]}))
    
    elif args.command == "search":
        results = search(args.query, k=args.k, agent=args.agent)
        print(json.dumps([
            {"score": round(s, 4), "content": p["content"][:200], 
             "success": p.get("success"), "agent": p.get("agent"),
             "errors": p.get("errors", [])[:3]}
            for s, p in results
        ], indent=2))
    
    elif args.command == "stats":
        stats = get_agent_stats(args.agent)
        print(json.dumps(stats, indent=2))
    
    elif args.command == "failures":
        failures = get_recent_failures(args.agent, limit=args.limit)
        print(json.dumps(failures, indent=2))
    
    elif args.command == "format-prompt":
        results = search(args.query, k=args.k, agent=args.agent)
        print(format_patterns_for_prompt(results, max_chars=args.max_chars))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
