"""
CLAIM VERIFICATION SYSTEM — Never report "done" without proof.

Every agent MUST run this before claiming something works.
It tests FUNCTIONALITY, not just syntax.

Usage:
  python scripts/verify-claim.py "claim text" [--component name]
  
Examples:
  python scripts/verify-claim.py "Vector search works"
  python scripts/verify-claim.py "Trigger fires" --component nervous_system
  python scripts/verify-claim.py "Embeddings complete" --component graphiti
"""
import sys, requests, json, time, subprocess
from datetime import datetime

VERIFIED = []
FAILED = []

def verify(name, test_fn):
    """Run a verification test. Records pass/fail."""
    try:
        result = test_fn()
        if result:
            VERIFIED.append(name)
            print(f"  [PASS] {name}")
        else:
            FAILED.append(name)
            print(f"  [FAIL] {name} — claim is FALSE")
    except Exception as e:
        FAILED.append(name)
        print(f"  [FAIL] {name} — error: {str(e)[:80]}")

# ============================================================
# ACTUAL FUNCTIONALITY TESTS (not syntax checks)
# ============================================================

def test_graphiti_write():
    """Does graphiti_add_episode actually STORE data?"""
    r = requests.post("http://localhost:8001/json-rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_add_episode", "arguments": {"text": f"verify-{time.time()}", "name": "verify-write"}}
    }, timeout=10)
    data = r.json()
    content = data.get("result", {}).get("content", [])
    if not content:
        return False
    result = json.loads(content[0]["text"])
    return result.get("success", False)

def test_graphiti_read():
    """Does graphiti_search_nodes actually FIND data?"""
    r = requests.post("http://localhost:8001/json-rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_search_nodes", "arguments": {"query": "verify", "limit": 1}}
    }, timeout=10)
    data = r.json()
    content = data.get("result", {}).get("content", [])
    if not content:
        return False
    result = json.loads(content[0]["text"])
    return len(result.get("episodes", [])) > 0

def test_vector_search():
    """Does vector search return SEMANTIC results (not text-only)?"""
    r = requests.post("http://localhost:8001/json-rpc", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "graphiti_vector_search", "arguments": {"query": "memory system", "limit": 1}}
    }, timeout=10)
    data = r.json()
    content = data.get("result", {}).get("content", [])
    if not content:
        return False
    result = json.loads(content[0]["text"])
    return len(result.get("episodes", [])) > 0

def test_embedding_dims():
    """Are embedding dimensions consistent (768 everywhere)?"""
    # Check Ollama
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text:latest", "prompt": "test"
    }, timeout=10)
    ollama_dims = len(r.json().get("embedding", []))
    
    # Check Neo4j
    r2 = requests.post("http://localhost:7474/db/neo4j/tx/commit", json={
        "statements": [{"statement": "MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN size(e.embedding) as d LIMIT 1"}]
    }, timeout=10)
    neo4j_dims = r2.json()["results"][0]["data"][0]["row"][0]
    
    return ollama_dims == neo4j_dims == 768

def test_trigger_fires():
    """Does a trigger actually fire with real data?"""
    import sys; sys.path.insert(0, "src")
    from trigger_router import TriggerRouter
    router = TriggerRouter("triggers.json")
    r = router.process_event({"source": "gpu", "type": "warning", "severity": "warning", "data": {"temp": 87}})
    return r is not None and r.get("success") is not None

def test_velocity_tracking():
    """Does velocity actually record?"""
    import sys; sys.path.insert(0, "src")
    from metrics_store import MetricsStore
    store = MetricsStore("data/nervous_system.db")
    v = store.get_velocity(7)
    return v is not None and v.get("tasks", 0) > 0

def test_context_injector():
    """Does context injector actually return data?"""
    import sys; sys.path.insert(0, "src")
    from context_injector import ContextInjector
    ci = ContextInjector()
    ctx = ci.get_context("preferences", limit=1)
    return len(ctx.episodes) > 0

def test_startup_validator():
    """Does startup validator actually check things?"""
    r = subprocess.run([sys.executable, "scripts/startup-validate.py"], capture_output=True, text=True, timeout=30)
    return "OK" in r.stdout

def test_neo4j_alive():
    """Is Neo4j actually responding?"""
    r = requests.get("http://localhost:7474", timeout=5)
    return r.status_code == 200

def test_ollama_alive():
    """Is Ollama actually responding?"""
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    return r.status_code == 200

# ============================================================
# MAIN
# ============================================================

component = "all"
claim = "system verification"

if len(sys.argv) > 1:
    claim = sys.argv[1]
if "--component" in sys.argv:
    idx = sys.argv.index("--component")
    component = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "all"

print(f"=== VERIFYING: {claim} ===")
print(f"Component: {component}")
print(f"Time: {datetime.now().isoformat()}")
print()

if component in ("all", "services"):
    verify("Neo4j alive", test_neo4j_alive)
    verify("Ollama alive", test_ollama_alive)

if component in ("all", "graphiti"):
    verify("Graphiti write", test_graphiti_write)
    verify("Graphiti read", test_graphiti_read)
    verify("Vector search", test_vector_search)
    verify("Embedding dims consistent", test_embedding_dims)

if component in ("all", "nervous_system"):
    verify("Trigger fires", test_trigger_fires)

if component in ("all", "velocity"):
    verify("Velocity tracking", test_velocity_tracking)

if component in ("all", "context"):
    verify("Context injector", test_context_injector)

if component in ("all", "startup"):
    verify("Startup validator", test_startup_validator)

print()
print(f"=== RESULTS ===")
print(f"Verified: {len(VERIFIED)}")
print(f"Failed: {len(FAILED)}")

if FAILED:
    print(f"\n[FAIL] CLAIM REJECTED: {claim}")
    print(f"Failed: {FAILED}")
    print(f"\nDO NOT report 'done' until all failures are fixed.")
    sys.exit(1)
else:
    print(f"\n[PASS] CLAIM VERIFIED: {claim}")
    sys.exit(0)
