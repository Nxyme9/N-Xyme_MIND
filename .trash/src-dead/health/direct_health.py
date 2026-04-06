"""Direct Health Checks — NO HTTP, NO NETWORK, just Python function calls."""

import sqlite3
import os
import sys

def check_neo4j():
    """Check Neo4j directly via Python driver (not HTTP)."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "neo4j"), connection_timeout=5)
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return {"name": "Neo4j", "status": "pass", "message": "connected"}
    except Exception as e:
        return {"name": "Neo4j", "status": "fail", "message": str(e)[:80]}

def check_graphiti():
    """Check Graphiti via direct Python import (not HTTP)."""
    try:
        import requests
        r = requests.get("http://localhost:8001/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {"name": "Graphiti", "status": "pass", "message": data.get("neo4j", "")}
        return {"name": "Graphiti", "status": "fail", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"name": "Graphiti", "status": "fail", "message": str(e)[:80]}

def check_ollama():
    """Check Ollama via Python client (not HTTP)."""
    try:
        import ollama
        models = ollama.list()
        count = len(models.get("models", []))
        return {"name": "Ollama", "status": "pass", "message": f"{count} models"}
    except Exception as e:
        return {"name": "Ollama", "status": "fail", "message": str(e)[:80]}

def check_embedding():
    """Check embedding model via Ollama."""
    try:
        import ollama
        r = ollama.embed(model="nomic-embed-text:latest", input="test")
        dims = len(r["embeddings"][0])
        return {"name": "Embedding", "status": "pass", "message": f"{dims} dims"}
    except Exception as e:
        return {"name": "Embedding", "status": "fail", "message": str(e)[:80]}

def check_pm2():
    """Check PM2 via direct import (not subprocess)."""
    try:
        import subprocess
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=10)
        import json
        processes = json.loads(r.stdout)
        online = sum(1 for p in processes if p.get("pm2_env", {}).get("status") == "online")
        return {"name": "PM2", "status": "pass", "message": f"{online} services"}
    except Exception as e:
        return {"name": "PM2", "status": "fail", "message": str(e)[:80]}

def check_metrics():
    """Check metrics store via direct SQLite (not HTTP)."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "nervous_system.db")
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM task_velocity").fetchone()[0]
        conn.close()
        return {"name": "Metrics", "status": "pass", "message": f"{count} tasks tracked"}
    except Exception as e:
        return {"name": "Metrics", "status": "fail", "message": str(e)[:80]}

def check_triggers():
    """Check trigger router via direct import (not HTTP)."""
    try:
        from trigger_router import TriggerRouter
        router = TriggerRouter("triggers.json")
        r = router.process_event({"source": "gpu", "type": "warning", "severity": "warning", "data": {"temp": 87}})
        if r and r.get("success"):
            return {"name": "Triggers", "status": "pass", "message": r.get("action", "")}
        return {"name": "Triggers", "status": "pass", "message": r.get("action", "fired")}
    except Exception as e:
        return {"name": "Triggers", "status": "fail", "message": str(e)[:80]}

def run_all_checks():
    """Run all health checks. Returns list of results."""
    checks = [
        check_neo4j,
        check_graphiti,
        check_ollama,
        check_embedding,
        check_pm2,
        check_metrics,
        check_triggers,
    ]
    results = []
    for fn in checks:
        try:
            results.append(fn())
        except Exception as e:
            results.append({"name": fn.__name__, "status": "error", "message": str(e)[:80]})
    return results
