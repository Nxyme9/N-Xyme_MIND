#!/usr/bin/env python3
"""BATCH WRITE — Generate multiple files from a spec.
Usage: echo '{"spec": "create a logger module with 3 files", "files": ["log.py", "config.py", "handler.py"]}' | python3 batch_write_bridge.py --stdin
"""
import sys
import json
import os
import subprocess

DAEMON = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon"

def batch_write(spec, file_list):
    """Generate files by spawning background agents per file."""
    results = []
    for fname in file_list:
        if not fname:
            results.append({"file": fname, "status": "failed", "error": "empty filename"})
            continue
        q = json.dumps({"type": "route", "query": f"delegate code writing: {spec} — file: {fname}", "id": "bw"})
        try:
            proc = subprocess.run([DAEMON], input=q, capture_output=True, text=True, timeout=30)
            result = json.loads(proc.stdout.strip())
            results.append({"file": fname, "status": "queued", "tool": result.get("tool", "unknown")})
        except subprocess.TimeoutExpired:
            results.append({"file": fname, "status": "failed", "error": "daemon timeout"})
        except (json.JSONDecodeError, OSError) as e:
            results.append({"file": fname, "status": "failed", "error": str(e)})
    
    return {
        "type": "batch_write_result",
        "spec": spec[:100],
        "files": file_list,
        "results": results,
        "count": len(file_list)
    }

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                req = json.loads(line)
                result = batch_write(req.get("spec", ""), req.get("files", []))
                print(json.dumps(result), flush=True)
            except Exception as e:
                print(json.dumps({"type": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    main()
