#!/usr/bin/env python3
"""CODEX — ONNX-powered semantic code search bridge.

Usage:
  python3 code_search_bridge.py --index /path/to/project
  python3 code_search_bridge.py --search "find routing logic" --top-k 5

Output: JSON-L on stdout
"""
import sys
import json
import os
import re
import numpy as np

# Paths
MODEL_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/models"
MODEL_PATH = os.path.join(MODEL_DIR, "embedding.onnx")
INDEX_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/code_index"
os.makedirs(INDEX_DIR, exist_ok=True)

# Lazy-loaded globals
_tokenizer = None
_session = None
_index = None  # list of {path, vector, summary}

def _load_model():
    global _tokenizer, _session
    if _tokenizer is not None:
        return
    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/archive/data_chaos/data_chaos/.venv/lib/python3.14/site-packages")
    from transformers import AutoTokenizer
    import onnxruntime as ort
    _tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    _session = ort.InferenceSession(MODEL_PATH)

def _embed(text):
    _load_model()
    tokens = _tokenizer(text, padding=True, truncation=True, return_tensors="np", max_length=128)
    inputs = {i.name: tokens[i.name] for i in _session.get_inputs()}
    result = _session.run(None, inputs)
    return result[1][0]  # 384-dim tanh output

def _cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def cmd_index(project_root):
    """Index all source files in project."""
    files = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        # Skip junk
        skip_dirs = {"venv", ".venv", "node_modules", "__pycache__", ".git", "target", "build"}
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            # FIX: Remove duplicate .mojo, add more extensions
            if f.endswith((".mojo", ".py", ".rs", ".ts", ".js")):
                files.append(os.path.join(dirpath, f))
    
    results = []
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            summary = f"{os.path.basename(path)}: {content[:200].replace(chr(10), ' ')}"
            vec = _embed(summary)
            # FIX: Use os.path.relpath instead of str.replace for path manipulation
            rel_path = os.path.relpath(path, project_root)
            results.append({"path": rel_path, "vector": vec.tolist(), "summary": summary[:100]})
        except Exception as e:
            # FIX: Log errors instead of silently swallowing
            print(f"[index] Skipping {path}: {e}", file=sys.stderr)
            continue
    
    # Save index
    idx_path = os.path.join(INDEX_DIR, "index.json")
    with open(idx_path, "w") as f:
        json.dump({"files": results, "count": len(results), "project": project_root}, f)
    
    print(json.dumps({"type": "index_result", "files_indexed": len(results), "path": idx_path}))

def cmd_search(query, top_k=5):
    """Search indexed files by semantic similarity."""
    idx_path = os.path.join(INDEX_DIR, "index.json")
    if not os.path.exists(idx_path):
        print(json.dumps({"type": "error", "code": "NO_INDEX", "message": "Run --index first"}))
        return
    
    with open(idx_path) as f:
        idx = json.load(f)
    
    q_vec = _embed(query)
    results = []
    for entry in idx["files"]:
        f_vec = np.array(entry["vector"])
        sim = _cosine_sim(q_vec, f_vec)
        results.append({"path": entry["path"], "score": round(sim, 4), "summary": entry["summary"]})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps({"type": "search_result", "query": query, "results": results[:top_k], "total": len(idx["files"])}))

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"type": "error", "code": "USAGE", "message": "Use --index <path> or --search <query>"}))
        return
    
    if sys.argv[1] == "--index" and len(sys.argv) >= 3:
        cmd_index(sys.argv[2])
    elif sys.argv[1] == "--search" and len(sys.argv) >= 3:
        top_k = 5
        if "--top-k" in sys.argv:
            idx = sys.argv.index("--top-k")
            if idx + 1 < len(sys.argv):
                top_k = int(sys.argv[idx + 1])
        cmd_search(sys.argv[2], top_k)
    elif sys.argv[1] == "--stdin":
        # JSON-L mode: read lines from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                req = json.loads(line)
                if req.get("type") == "search":
                    cmd_search(req.get("query", ""), req.get("top_k", 5))
                elif req.get("type") == "index":
                    cmd_index(req.get("path", "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"))
            except Exception as e:
                print(json.dumps({"type": "error", "message": str(e)}), flush=True)
    else:
        print(json.dumps({"type": "error", "code": "USAGE", "message": "Unknown command"}))

if __name__ == "__main__":
    main()
