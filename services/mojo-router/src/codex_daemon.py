#!/usr/bin/env python3
"""CODEX Daemon — Persistent semantic code search server.
Loads ONNX model once, caches index in RAM, sub-ms search.
stdin/stdout JSON-L — same protocol as embed_bridge.

Usage:
  python3 codex_daemon.py
  # Send: {"type": "index", "path": "/project"}
  # Send: {"type": "search", "query": "find routing", "top_k": 5}
  # Send: {"type": "quality", "file": "src/main.mojo"}
  # Send: {"type": "status"}
"""
import sys, json, os, time, hashlib, numpy as np

PROJECT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
MEM_PATH = os.path.join(PROJECT, "data/memory/vectors/ingest.jsonl")
_index_cache = None  # Pre-computed index loaded into RAM

DAEMON_PATH = os.path.join(PROJECT, "services/mojo-router/src/daemon")

def _embed_via_daemon(text):
    """Use Mojo daemon's embed endpoint for ALL embeddings.
    This means: change daemon's backend → change EVERYTHING'S embeddings.
    """
    import subprocess, json
    try:
        q = json.dumps({"type": "embed", "query": text, "id": "codex"})
        proc = subprocess.run([DAEMON_PATH], input=q, capture_output=True, text=True, timeout=30)
        result = json.loads(proc.stdout.strip())
        if "embedding" in result:
            # Parse the embedding array from the JSON output format
            # Format: {"type":"embed_result","embedding":[0.1,0.2,...], ...}
            return np.array(result.get("embedding", []))
    except:
        pass
    # Fallback: ONNX if daemon unavailable
    return _embed_onnx_fallback(text)

_onnx_model = None
_onnx_tokenizer = None

def _embed_onnx_fallback(text):
    """Fallback to local ONNX model (no daemon dependency)."""
    global _onnx_model, _onnx_tokenizer
    if _onnx_model is None:
        sys.path.insert(0, os.path.join(PROJECT, "archive/data_chaos/data_chaos/.venv/lib/python3.14/site-packages"))
        from transformers import AutoTokenizer
        import onnxruntime as ort
        model_path = os.path.join(PROJECT, "data/memory/models/embedding.onnx")
        _onnx_tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        _onnx_model = ort.InferenceSession(model_path)
    tokens = _onnx_tokenizer(text, padding=True, truncation=True, return_tensors="np", max_length=128)
    inputs = {i.name: tokens[i.name] for i in _onnx_model.get_inputs()}
    return _onnx_model.run(None, inputs)[1][0]

def _embed(text):
    # Onnx for bulk (fast, 5ms), daemon for single queries (unified engine)
    if hasattr(_embed, "_use_daemon") and _embed._use_daemon:
        return _embed_via_daemon(text)
    return _embed_onnx_fallback(text)

def _cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def cmd_index(root, force=False):
    """Index all code files, cache in RAM."""
    global _index_cache
    if _index_cache and not force:
        return {"type": "index_result", "files": len(_index_cache), "cached": True}
    
    code_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        skip = {'venv', '.venv', 'node_modules', '__pycache__', '.git', 'target', 'build', '.cache'}
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f.endswith(('.mojo', '.py', '.rs', '.ts', '.js', '.mojo')):
                code_files.append(os.path.join(dirpath, f))
    
    _index_cache = []
    for path in code_files:
        try:
            with open(path) as f:
                content = f.read()
            rel = path.replace(root, '', 1).lstrip('/')
            summary = f"{rel}: {content[:200].replace(chr(10), ' ')[:200]}"
            vec = _embed(summary)
            _index_cache.append({"path": rel, "vec": vec.tolist(), "summary": summary[:100]})
        except:
            continue
    
    return {"type": "index_result", "files": len(_index_cache), "path": root}

def cmd_search(query, top_k=5):
    """Search indexed files."""
    if not _index_cache:
        return {"type": "error", "code": "NO_INDEX", "message": "Run --index first"}
    
    q_vec = _embed(query)
    results = []
    for entry in _index_cache:
        f_vec = np.array(entry["vec"])
        sim = _cosine(q_vec, f_vec)
        results.append({"path": entry["path"], "score": round(sim, 4), "summary": entry["summary"]})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"type": "search_result", "query": query, "results": results[:top_k], "total": len(_index_cache)}

def cmd_quality(file_path):
    """Code quality check with memory context."""
    full = file_path if file_path.startswith("/") else os.path.join(PROJECT, file_path)
    if not os.path.exists(full):
        return {"type": "error", "message": f"Not found: {file_path}"}
    
    with open(full) as f:
        code = f.read()
    lines = code.split('\n')
    
    issues = []
    error_handlers = len([l for l in lines if 'try' in l or 'except' in l])
    hardcoded = len([l for l in lines if '/home/' in l])
    funcs = len([l for l in lines if l.strip().startswith(('def ', 'fn ', 'class ', 'struct '))])
    
    if error_handlers < 5 and len(lines) > 100:
        issues.append(f"Few error handlers ({error_handlers}) for {len(lines)} lines")
    if hardcoded > 0:
        issues.append(f"Hardcoded paths: {hardcoded}")
    if funcs < 3 and len(lines) > 200:
        issues.append(f"Monolithic: {funcs} defs in {len(lines)} lines")
    
    return {
        "type": "quality_result", "file": file_path,
        "lines": len(lines), "defs": funcs, "errors": error_handlers,
        "issues": issues, "score": max(0, 10 - len(issues))
    }

def main():
    # Pre-index on startup
    print(json.dumps({"type": "info", "message": "CODEX daemon starting..."}), flush=True)
    result = cmd_index(PROJECT, force=False)
    print(json.dumps(result), flush=True)
    
    # Main JSON-L loop
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            t = req.get("type", "")
            if t == "search":
                print(json.dumps(cmd_search(req.get("query", ""), req.get("top_k", 5))), flush=True)
            elif t == "index":
                print(json.dumps(cmd_index(req.get("path", PROJECT), force=True)), flush=True)
            elif t == "quality":
                print(json.dumps(cmd_quality(req.get("file", ""))), flush=True)
            elif t == "status":
                count = len(_index_cache) if _index_cache else 0
                print(json.dumps({"type": "status", "files_indexed": count, "ram_mb": "~" + str(count * 400 // 1000000)}), flush=True)
            else:
                print(json.dumps({"type": "error", "message": f"Unknown: {t}"}), flush=True)
        except Exception as e:
            print(json.dumps({"type": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    main()
