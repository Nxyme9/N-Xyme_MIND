#!/usr/bin/env python3
"""
Startup Validator - Runs once, checks 6 things, prints table, exits.
Exit 0 = all OK, Exit 1 = critical failure.
"""

import subprocess
import sys
import json
import re
import os
from pathlib import Path

GRAPHITI_CONFIG = (
    Path(__file__).parent.parent / "packages" / "graphiti-memory" / "src" / "config" / "index.js"
)
OLLAMA_URL = "http://localhost:11434"
NEO4J_URL = "http://localhost:7474"
GRAPHITI_URL = "http://localhost:8001"
REQUIRED_MODELS = ["nomic-embed-text:latest", "llama3-groq-tool-use:8b"]
VRAM_THRESHOLD = 90


def run(cmd, timeout=10):
    """Run command, return (success, output)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)


def curl_json(url, timeout=5):
    """curl GET → parsed JSON or None."""
    ok, out = run(f'curl -s --max-time {timeout} "{url}"')
    if not ok:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def curl_status(url, timeout=5):
    """curl GET → HTTP status code or 0."""
    _, out = run(f'curl -s -o /dev/null -w "%{{http_code}}" --max-time {timeout} "{url}"')
    try:
        return int(out.strip())
    except ValueError:
        return 0


results = []


def check_graphiti_config():
    """1. Verify embedModel=nomic-embed-text:latest and dimensions=768."""
    name = "Graphiti Config"
    try:
        content = GRAPHITI_CONFIG.read_text(encoding="utf-8")
    except FileNotFoundError:
        results.append((name, "FAIL", f"File not found: {GRAPHITI_CONFIG}"))
        return False

    embed_ok = "nomic-embed-text:latest" in content
    dims_ok = "768" in content

    if embed_ok and dims_ok:
        results.append((name, "OK", "-"))
        return True

    fix_parts = []
    if not embed_ok:
        content = re.sub(
            r"embedModel:\s*process\.env\.OLLAMA_EMBED_MODEL\s*\|\|\s*'[^']*'",
            "embedModel: process.env.OLLAMA_EMBED_MODEL || 'nomic-embed-text:latest'",
            content,
        )
        fix_parts.append("embedModel")
    if not dims_ok:
        content = re.sub(
            r"dimensions:\s*parseInt\(process\.env\.EMBEDDING_DIMENSIONS,\s*10\)\s*\|\|\s*\d+",
            "dimensions: parseInt(process.env.EMBEDDING_DIMENSIONS, 10) || 768",
            content,
        )
        fix_parts.append("dimensions")

    GRAPHITI_CONFIG.write_text(content, encoding="utf-8")
    run("pm2 restart graphiti-mcp")
    results.append((name, "FIXED", f"Patched {', '.join(fix_parts)} + restarted"))
    return True


def check_ollama_models():
    """2. Verify required Ollama models exist."""
    name = "Ollama Models"
    data = curl_json(f"{OLLAMA_URL}/api/tags")
    if data is None:
        results.append((name, "FAIL", "Ollama not reachable"))
        return False

    installed = {m.get("name", "") for m in data.get("models", [])}
    missing = [m for m in REQUIRED_MODELS if m not in installed]

    if not missing:
        results.append((name, "OK", "-"))
        return True

    pulled = []
    for model in missing:
        try:
            import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from trigger_router import TriggerRouter
            TriggerRouter("triggers.json").process_event({"source": "ollama", "type": "model_missing", "severity": "critical", "data": {"model": model}})
        except: pass
    # Original loop continues
    for model in missing:
        ok, _ = run(
            f'curl -s -X POST "{OLLAMA_URL}/api/pull" -d \'{{"name":"{model}"}}\'', timeout=300
        )
        if ok:
            pulled.append(model)

    if pulled:
        results.append((name, "FIXED", f"Pulled: {', '.join(pulled)}"))
    else:
        results.append((name, "FAIL", f"Could not pull: {', '.join(missing)}"))
        return False
    return True


def check_neo4j():
    """3. Neo4j HTTP returns 200."""
    name = "Neo4j"
    status = curl_status(NEO4J_URL)
    if status == 200:
        results.append((name, "OK", "-"))
        return True
    results.append((name, "FAIL", f"HTTP {status} (expected 200)"))
    return False


def check_graphiti_health():
    """4. Graphiti /health shows neo4j: connected."""
    name = "Graphiti Health"
    data = curl_json(f"{GRAPHITI_URL}/health")
    if data is None:
        results.append((name, "FAIL", "Graphiti not reachable"))
        return False

    neo4j_status = data.get("neo4j", data.get("checks", {}).get("neo4j", ""))
    if "connect" in str(neo4j_status).lower():
        results.append((name, "OK", "-"))
        return True
    results.append((name, "FAIL", f"neo4j: {neo4j_status}"))
    return False


def check_vram():
    """5. nvidia-smi shows <90% VRAM usage."""
    name = "VRAM"
    ok, out = run("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")
    if not ok:
        results.append((name, "SKIP", "nvidia-smi not available"))
        return True

    try:
        used, total = [int(x.strip()) for x in out.split(",")]
        pct = (used / total) * 100
    except (ValueError, ZeroDivisionError):
        results.append((name, "SKIP", "Could not parse nvidia-smi"))
        return True

    if pct < VRAM_THRESHOLD:
        results.append((name, "OK", f"{pct:.1f}% used"))
        return True
    results.append((name, "WARN", f"{pct:.1f}% used (>{VRAM_THRESHOLD}%)"))
    return True  # warning, not critical


def check_pm2_graphiti():
    """6. PM2 shows graphiti-mcp online."""
    name = "PM2 graphiti-mcp"
    ok, out = run("pm2 jlist")
    if not ok:
        results.append((name, "FAIL", "PM2 not available"))
        return False

    try:
        procs = json.loads(out)
    except json.JSONDecodeError:
        results.append((name, "FAIL", "Could not parse pm2 output"))
        return False

    for p in procs:
        if p.get("name") == "graphiti-mcp":
            status = p.get("pm2_env", {}).get("status", "unknown")
            if status == "online":
                results.append((name, "OK", "-"))
                return True
            results.append((name, "FAIL", f"Status: {status}"))
            return False

    results.append((name, "FAIL", "Not found in PM2"))
    return False


def main():
    checks = [
        check_graphiti_config,
        check_ollama_models,
        check_neo4j,
        check_graphiti_health,
        check_vram,
        check_pm2_graphiti,
    ]

    for fn in checks:
        fn()

    print(f"\n{'CHECK':<22} {'STATUS':<8} {'FIX'}")
    print("-" * 60)
    critical_fail = False
    for name, status, fix in results:
        print(f"{name:<22} {status:<8} {fix}")
        if status == "FAIL":
            critical_fail = True

    print()
    sys.exit(1 if critical_fail else 0)


if __name__ == "__main__":
    main()
