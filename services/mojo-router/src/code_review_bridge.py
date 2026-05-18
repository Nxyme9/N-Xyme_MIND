#!/usr/bin/env python3
"""CODEX REVIEW — Memory-backed code review megatool.

Checks code against holographic memory for past decisions, known patterns.
Usage: echo '{"file": "daemon.mojo", "context": "check error handling"}' | python3 code_review_bridge.py --stdin
"""
import sys
import json
import os

MEM_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/vectors/ingest.jsonl"
PROJECT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

def load_memories():
    if not os.path.exists(MEM_PATH):
        return []
    entries = []
    with open(MEM_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # Skip malformed lines
    return entries

def review_file(file_path, context=""):
    """Review a file against holographic memory for past decisions + patterns."""
    full_path = file_path if file_path.startswith("/") else os.path.join(PROJECT, file_path)
    if not os.path.exists(full_path):
        return {"type": "error", "message": f"File not found: {full_path}"}
    
    with open(full_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    lines = content.split("\n")
    memories = load_memories()
    
    # Find relevant memories
    query_terms = set((file_path + " " + context).lower().split())
    relevant = []
    for m in memories:
        text = (m.get("text", "") + " " + m.get("type", "")).lower()
        score = sum(1 for t in query_terms if t in text)
        if score > 0:
            relevant.append({"score": score, "text": m.get("text", ""), "type": m.get("type", "")})
    
    relevant.sort(key=lambda x: x["score"], reverse=True)
    
    # FIX: Filter out None from suggestions
    suggestions = []
    if len(lines) > 200:
        suggestions.append(f"File has {len(lines)} lines")
    if relevant:
        suggestions.append(f"Has {len(relevant)} relevant memories")
    else:
        suggestions.append("No memory context — consider memory_ingest")
    
    return {
        "type": "review_result",
        "file": file_path,
        "lines": len(lines),
        "defs": len([l for l in lines if l.strip().startswith(("def ", "fn ", "class ", "struct "))]),
        "imports": len([l for l in lines if l.strip().startswith(("import ", "from ", "use "))]),
        "memory_context": relevant[:5],
        "suggestions": suggestions,
        "decision_history": [r for r in relevant if "decision" in r.get("type", "")]
    }

def main():
    if len(sys.argv) < 2 or sys.argv[1] != "--stdin":
        print(json.dumps({"type": "error", "message": "Use --stdin mode"}))
        return
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            result = review_file(req.get("file", ""), req.get("context", ""))
            print(json.dumps(result))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"type": "error", "message": str(e)}))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
