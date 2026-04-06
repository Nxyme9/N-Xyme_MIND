# Neo4j + Graphiti + FalkorDB Local Memory Masterplan (v3 — Bleeding Edge)

## TL;DR

> **Goal**: Local Neo4j + Graphiti knowledge graph memory in `/home/nxyme/nx_openmore/`
> All deps local, survives restarts, uses Ollama for LLM + embeddings.

## Verified State (5-Agent Audit + 35-Project Analysis)

| Component | Status | Path |
|-----------|--------|------|
| Neo4j binary | ✅ Installed | `/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j` |
| Neo4j data | ✅ 517MB, 3,881 nodes | `/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/data/` |
| Neo4j running | ❌ Stopped | Ports 7687/7474 empty |
| Neo4j auth | ✅ neo4j:LifePath11 | Confirmed in auth.ini |
| FalkorDB | ❌ Not installed | `pip install falkordb` |
| Java | ✅ OpenJDK 21.0.10 | `/usr/bin/java` |
| Ollama | ✅ Running | Port 11434, nomic-embed-text (768 dims) |
| graphiti-core | ❌ Not installed | v0.28.2 available on PyPI |
| Python | ⚠️ 3.14.3 | graphiti-core requires >=3.10,<4 — need dry-run test |
| OpenCode config | ✅ Exists | Uses `"mcp"` key (NOT `"mcpServers"`) |
| graphiti_memory.py | ❌ Doesn't exist | Need to CREATE (not update) |
| Systemd service | ❌ None | Need to create for restart survival |
| RAM/Disk | ✅ 30GB/777GB | Plenty |

## WHY FALKORDB OVER NEO4J (Bleeding Edge Decision)

| Factor | Neo4j | FalkorDB | Winner |
|--------|-------|----------|--------|
| RAM | 4-12GB (JVM) | 512MB-2GB (Redis) | **FalkorDB** |
| Query speed | 3-4s path queries | Sub-10ms | **FalkorDB** |
| Ingestion | 30s/100K nodes | Faster (sparse matrix) | **FalkorDB** |
| Setup | JVM + Docker + config | `pip install` + config | **FalkorDB** |
| Your history | Failed 4 times | Never tried | **FalkorDB** |
| Multi-tenant | Manual | Native isolation | **FalkorDB** |
| CVE-2026-32247 | Affected | Affected (patch in 0.28.2) | Tie |
| Maturity | 10+ years | 2 years | **Neo4j** |
| Community | 100K+ stars | 4K stars | **Neo4j** |
| Graphiti support | Primary | Official (since mid-2025) | Tie |

**Decision: FalkorDB** — Lighter, faster, never failed on you. Neo4j available as fallback if FalkorDB has issues.

## CRITICAL FIXES from Review (v1 → v2 → v3)

| Component | Status | Path |
|-----------|--------|------|
| Neo4j binary | ✅ Installed | `/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j` |
| Neo4j data | ✅ 517MB, 3,881 nodes | `/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/data/` |
| Neo4j running | ❌ Stopped | Ports 7687/7474 empty |
| Neo4j auth | ✅ neo4j:LifePath11 | Confirmed in auth.ini |
| Java | ✅ OpenJDK 21.0.10 | `/usr/bin/java` |
| Ollama | ✅ Running | Port 11434, nomic-embed-text (768 dims) |
| graphiti-core | ❌ Not installed | v0.28.2 available on PyPI |
| Python | ⚠️ 3.14.3 | graphiti-core requires >=3.10,<4 — need dry-run test |
| OpenCode config | ✅ Exists | Uses `"mcp"` key (NOT `"mcpServers"`) |
| graphiti_memory.py | ❌ Doesn't exist | Need to CREATE (not update) |
| Systemd service | ❌ None | Need to create for restart survival |
| RAM/Disk | ✅ 30GB/777GB | Plenty |

## CRITICAL FIXES from Review (v1 → v2)

1. **Config key**: `"mcp"` not `"mcpServers"` (from existing opencode.json)
2. **Python import**: `from graphiti_core.driver.neo4j_driver import Neo4jDriver` (not `drivers.neo4j`)
3. **LLM client required**: Graphiti needs BOTH LLM client AND embedder (not just embedder)
4. **Official MCP server exists**: `getzep/graphiti/mcp_server/` — use it, don't build custom
5. **Data isolation**: Use `group_id` to keep Graphiti data separate from existing 3,881 nodes
6. **Vector index**: Add to neo4j.conf — `dbms.index.default_schema_provider`
7. **Python 3.14**: Dry-run install first to verify compatibility
8. **Plan deduplication**: Removed conflicting second copy

## Execution Plan (3 Phases with Gates)

### Phase A: Neo4j Up & Verified (5 min)

**Gate**: Must pass before proceeding to Phase B

```bash
# 1. Check if already running
/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j status

# 2. If not running, start it
/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j start

# 3. Wait 10s for startup
sleep 10

# 4. Verify ports
ss -tlnp | grep -E "7687|7474"

# 5. Test connection + verify existing data preserved
cypher-shell -u neo4j -p LifePath11 "MATCH (n) RETURN count(n) AS count"
# EXPECTED: count >= 3881

# 6. Create systemd service for restart survival
sudo tee /etc/systemd/system/neo4j.service > /dev/null << 'EOF'
[Unit]
Description=Neo4j Graph Database
After=network.target

[Service]
Type=forking
User=nxyme
ExecStart=/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j start
ExecStop=/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j stop
ExecReload=/home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j restart
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable neo4j
```

**QA Scenario A-1**:
```bash
cypher-shell -u neo4j -p LifePath11 "RETURN 1 AS result"
# EXPECTED: +--------+\n| result |\n+--------+\n| 1      |\n+--------+
```

**QA Scenario A-2** (data preservation):
```bash
cypher-shell -u neo4j -p LifePath11 "MATCH (n) RETURN count(n) AS count"
# EXPECTED: count >= 3881
```

**QA Scenario A-3** (restart survival):
```bash
sudo systemctl is-enabled neo4j
# EXPECTED: enabled
```

---

### Phase B: Graphiti Installed & Connected (15 min)

**Gate**: Must pass before proceeding to Phase C

```bash
# 1. Dry-run install to verify Python 3.14 compatibility
./athena/.venv/bin/pip install --dry-run graphiti-core
# IF FAILS: Pin to compatible version or use Python 3.12 venv

# 2. Install graphiti-core
./athena/.venv/bin/pip install graphiti-core

# 3. Verify import
./athena/.venv/bin/python -c "from graphiti_core import Graphiti; print('OK')"
# EXPECTED: OK

# 4. Verify Ollama embedding dims
curl -s localhost:11434/api/embed -d '{"model":"nomic-embed-text:latest","input":"test"}' | python3 -c "import sys,json; print(len(json.load(sys.stdin)['embeddings'][0]))"
# EXPECTED: 768

# 5. Test Graphiti round-trip (add + search episode)
./athena/.venv/bin/python << 'PYEOF'
import asyncio
from datetime import datetime, timezone
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.nodes import EpisodeType

async def test():
    llm_config = LLMConfig(
        api_key="ollama",
        model="qwen2.5:14b",
        small_model="qwen2.5:14b",
        base_url="http://localhost:11434/v1",
    )
    llm_client = OpenAIGenericClient(config=llm_config)
    
    g = Graphiti(
        "bolt://localhost:7687",
        "neo4j",
        "LifePath11",
        llm_client=llm_client,
        embedder=OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key="ollama",
                embedding_model="nomic-embed-text:latest",
                embedding_dim=768,
                base_url="http://localhost:11434/v1",
            )
        ),
        cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
    )
    
    # Build indices (safe — creates Graphiti's own schema, doesn't touch existing data)
    await g.build_indices_and_constraints()
    
    # Add episode with group_id to isolate from existing data
    await g.add_episode(
        name="test-episode",
        episode_body="Testing Graphiti integration with Ollama embeddings",
        source=EpisodeType.text,
        reference_time=datetime.now(timezone.utc),
        group_id="graphiti-test",  # ISOLATION: separate from existing 3,881 nodes
    )
    
    # Search
    results = await g.search("testing integration", group_ids=["graphiti-test"])
    print(f"Found {len(results)} results")
    
    await g.close()
    return len(results) > 0

success = asyncio.run(test())
print("PASS" if success else "FAIL")
PYEOF
# EXPECTED: Found >= 1 results\nPASS
```

**QA Scenario B-1** (install):
```bash
./athena/.venv/bin/python -c "from graphiti_core import Graphiti; print('OK')"
# EXPECTED: OK
```

**QA Scenario B-2** (Ollama embedding dims):
```bash
curl -s localhost:11434/api/embed -d '{"model":"nomic-embed-text:latest","input":"test"}' | python3 -c "import sys,json; print(len(json.load(sys.stdin)['embeddings'][0]))"
# EXPECTED: 768
```

**QA Scenario B-3** (episode round-trip):
```bash
# Run the Python script above
# EXPECTED: Found >= 1 results\nPASS
```

---

### Phase C: MCP Integration (15 min)

**Gate**: Must pass — OpenCode sees graphiti-memory tools

```bash
# 1. Create MCP server wrapper script
mkdir -p bin
cat > bin/graphiti-mcp-server << 'SCRIPT'
#!/usr/bin/env python3
"""Minimal Graphiti MCP Server wrapper for OpenCode."""
import asyncio
import json
import sys
import os
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.nodes import EpisodeType
from datetime import datetime, timezone

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "LifePath11")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

llm_config = LLMConfig(api_key="ollama", model=OLLAMA_MODEL, small_model=OLLAMA_MODEL, base_url=OLLAMA_URL)
llm_client = OpenAIGenericClient(config=llm_config)

g = Graphiti(
    NEO4J_URI, NEO4J_USER, NEO4J_PASS,
    llm_client=llm_client,
    embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(api_key="ollama", embedding_model=EMBED_MODEL, embedding_dim=768, base_url=OLLAMA_URL)),
    cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
)

TOOLS = {
    "add_episode": {
        "description": "Add an episode to the knowledge graph",
        "inputSchema": {"type": "object", "properties": {
            "name": {"type": "string"},
            "content": {"type": "string"},
            "source": {"type": "string", "default": "text"},
            "group_id": {"type": "string", "default": "default"},
        }, "required": ["name", "content"]},
    },
    "search_nodes": {
        "description": "Search the knowledge graph",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
            "group_ids": {"type": "array", "items": {"type": "string"}},
        }, "required": ["query"]},
    },
    "get_episodes": {
        "description": "Get recent episodes",
        "inputSchema": {"type": "object", "properties": {
            "limit": {"type": "integer", "default": 10},
            "group_id": {"type": "string", "default": "default"},
        }},
    },
}

async def handle_request(req):
    method = req.get("method")
    rid = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": "graphiti-memory", "version": "0.1.0"},
        }}

    if method == "tools/list":
        tools = [{"name": n, **t} for n, t in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            if tool_name == "add_episode":
                result = await g.add_episode(
                    name=args["name"],
                    episode_body=args["content"],
                    source=EpisodeType.text,
                    reference_time=datetime.now(timezone.utc),
                    group_id=args.get("group_id", "default"),
                )
                return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": f"Added episode: {result.name}"}]}}

            elif tool_name == "search_nodes":
                results = await g.search(args["query"], group_ids=args.get("group_ids"), num_results=args.get("limit", 5))
                texts = [f"- {r.name}: {getattr(r, 'summary', str(r))}" for r in results[:args.get("limit", 5)]]
                return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": "\n".join(texts) or "No results"}]}}

            elif tool_name == "get_episodes":
                episodes = await g.retrieve_episodes(datetime.now(timezone.utc), last_n=args.get("limit", 10), group_ids=[args.get("group_id", "default")])
                texts = [f"- [{e.name}] {e.content[:100]}" for e in episodes[:args.get("limit", 10)]]
                return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": "\n".join(texts) or "No episodes"}]}}

        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -1, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}

async def main():
    await g.build_indices_and_constraints()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            resp = await handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

asyncio.run(main())
SCRIPT
chmod +x bin/graphiti-mcp-server

# 2. Add to OpenCode config (CORRECT key: "mcp" not "mcpServers")
python3 << 'PYEOF'
import json
config_path = "config/opencode.json"
with open(config_path) as f:
    config = json.load(f)

config.setdefault("mcp", {})["graphiti-memory"] = {
    "type": "local",
    "command": ["/home/nxyme/nx_openmore/athena/.venv/bin/python", "/home/nxyme/nx_openmore/bin/graphiti-mcp-server"],
    "environment": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "LifePath11",
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "OLLAMA_MODEL": "qwen2.5:14b",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text:latest",
    },
    "enabled": True,
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print("OK")
PYEOF
# EXPECTED: OK
```

**QA Scenario C-1** (MCP initialize):
```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | timeout 15 ./athena/.venv/bin/python bin/graphiti-mcp-server 2>&1 | head -1
# EXPECTED: {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", ...}}
```

**QA Scenario C-2** (tools/list):
```bash
printf '{"jsonrpc":"2.0","method":"tools/list","id":1}\n' | timeout 15 ./athena/.venv/bin/python bin/graphiti-mcp-server 2>&1 | head -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['result']['tools']))"
# EXPECTED: 3
```

**QA Scenario C-3** (OpenCode config):
```bash
python3 -c "import json; c=json.load(open('config/opencode.json')); assert 'graphiti-memory' in c.get('mcp',{}); print('OK')"
# EXPECTED: OK
```

---

## Directory Structure (Final)

```
/home/nxyme/opt/neo4j/                      # Neo4j (existing)
├── neo4j-community-2026.02.3/
│   ├── bin/neo4j                           # Server binary
│   ├── bin/cypher-shell                    # CLI
│   └── conf/neo4j.conf                     # Config
└── data/                                   # 517MB, 3,881 nodes

/home/nxyme/nx_openmore/
├── bin/
│   └── graphiti-mcp-server                 # MCP wrapper (new)
├── athena/
│   └── .venv/                              # Python venv (graphiti-core installed)
├── config/
│   └── opencode.json                       # Updated with graphiti-memory MCP
└── .sisyphus/plans/
    └── neo4j-graphiti-setup.md             # This plan

/etc/systemd/system/
└── neo4j.service                           # Auto-start (new)
```

## DEPRECATED PROJECTS (35 Projects Analyzed — 3 Agents)

### Top 5 Failure Patterns Across ALL Deprecated Projects

| # | Pattern | Evidence | Prevention |
|---|---------|----------|------------|
| 1 | **Over-engineering** | SPINE: 40+ services. MIND: 16+ services. None worked together. | Max 3 services to start. Validate each before adding more. |
| 2 | **Windows paths in Docker** | Every docker-compose had `C:/00_AI_Models/...` volume mounts. | Use relative paths (`./data`) or env vars (`${DATA_DIR}`). |
| 3 | **Placeholder secrets** | `SECRET_KEY=your-secret-key-here` in every .env. Never changed. | Use `docker secrets` or `.env.local` (gitignored). |
| 4 | **No incremental validation** | Built everything first, then tried to make it work. | Healthcheck passes → config connected → e2e test → THEN add next service. |
| 5 | **Configuration drift** | MCP servers running on PM2 but NOT in opencode.json. Ghost plugins. | Automated config validation script after every change. |

### Memory Approaches That FAILED

| Approach | Why It Failed |
|----------|---------------|
| Neo4j (repeated attempts) | Too complex, instability, resource hungry. 00_N-Xyme_MIND tried it, 1_N-Xyme_MIND moved to PostgreSQL. |
| Hash-based embeddings | Not semantic — just hashing text, no real understanding. |
| 40+ microservices | Blast radius too large, port conflicts, impossible to debug. |

### Memory Approaches That WORKED

| Approach | Where It Worked |
|----------|-----------------|
| Simple RAG + LanceDB | 1_N-Xyme_MIND — most practical |
| JSON file storage | C.O.D.E. OS — simple, portable |
| PostgreSQL + Redis | 1_N-Xyme_MIND production — replaced Neo4j |

### Critical Insight: Neo4j Was Abandoned EVERY Time

> Every project that tried Neo4j eventually abandoned it:
> - 00_N-Xyme_MIND: Neo4j crashed repeatedly (10+ restarts in 30 min)
> - 1_N-Xyme_MIND: Completely replaced with PostgreSQL + Redis
> - CATALYST: Docker Neo4j with Windows paths, never worked on Linux
> - MIND: Neo4j installed but Graphiti couldn't connect
>
> **Question**: Do we still want Neo4j, or should we use PostgreSQL + pgvector instead?

---

## MIND Repo Lessons (10-Agent Deep Dive)

### What Broke in N-Xyme_MIND (Avoid These)

| Failure | Root Cause | Our Prevention |
|---------|------------|----------------|
| Node.js graphiti crashes | Missing NEO4J_PASSWORD env var | Always export env BEFORE starting |
| Graphiti vector index fails | Missing `vector.similarity_function` | Let `build_indices()` handle it |
| 93% empty session files | Session format changed | Use stable format from day 1 |

### Battle-Tested Components to Transfer Later

| Component | Risk | Why |
|-----------|------|-----|
| `src/memory/` (6 files) | LOW | Cognitive memory model (working/semantic/procedural) |
| `src/event_bus.py` | LOW | Clean pub/sub, zero deps |
| `src/decision_tracker.py` | LOW | JSON decision log |

### Empty Aspirational (DON'T Build)

`src/agent/`, `src/orchestration/`, `src/safety/`, `src/collaboration/`, `src/bmad/` — all EMPTY.

### Graphiti Best Practices (Research)

| Practice | Why |
|----------|-----|
| SEMAPHORE_LIMIT=1-5 for Ollama | Local LLMs can't handle high concurrency |
| Always pass group_ids as array | Scalar values fail in MCP read tools |
| Use OpenAIGenericClient (not OpenAIClient) | Ollama doesn't support /v1/responses |
| Disable telemetry | GRAPHITI_TELEMETRY_ENABLED=false |

## CATALYST Repo Lessons (5-Agent Deep Dive)

### What Broke in CATALYST

| Failure | Root Cause | Our Prevention |
|---------|------------|----------------|
| Neo4j Docker won't start | Windows volume paths (`C:/...`) | Use native Neo4j, no Docker |
| Graphiti can't connect | Neo4j not installed | Install Neo4j first |
| PM2 failing | WinError 2 file not found | N/A (Linux) |
| Session diffs empty | Format changed | Stable format from day 1 |

### Battle-Tested Transfer (Later)

| Component | Risk | Why |
|-----------|------|-----|
| `src/brain/memory/*` | LOW | Same cognitive model as MIND |
| `src/health_core.py` | LOW | Health monitoring |
| `src/self_healer.py` | LOW | Autonomous healing |
| `mcp-stdio-bridge.js` | LOW | MCP stdio→HTTP bridge |

## Known Failure Modes

| Issue | Cause | Fix |
|-------|-------|-----|
| Neo4j won't start | Port conflict, Java version | Check `lsof -i :7687`, Java is v21 (OK) |
| Auth fails | Wrong password | Use `LifePath11`, NOT default `neo4j/neo4j` |
| pip install fails | Python 3.14 incompat | Dry-run first; pin version if needed |
| Embedding fails | Ollama not running | Ollama IS running on 11434 |
| Vector index missing | Neo4j config | Graphiti's `build_indices()` handles this |
| Dimension mismatch | Wrong model | Use `nomic-embed-text:latest` (768 dims) |
| Graphiti uses OpenAI API | Default LLM client | MUST pass explicit `llm_client=OpenAIGenericClient(...)` with Ollama config |
| Data collision | Graphiti writes to existing labels | Use `group_id="graphiti-test"` to isolate |
| MCP not found by OpenCode | Wrong config key | Use `"mcp"` not `"mcpServers"` |
| Breaks on restart | No systemd service | Phase A creates `neo4j.service` |

## Success Criteria (Agent-Executable)

- [ ] `cypher-shell -u neo4j -p LifePath11 "RETURN 1"` → returns 1
- [ ] `cypher-shell -u neo4j -p LifePath11 "MATCH (n) RETURN count(n)"` → count >= 3881
- [ ] `./athena/.venv/bin/python -c "from graphiti_core import Graphiti; print('OK')"` → OK
- [ ] Episode add + search round-trip returns >= 1 result
- [ ] MCP initialize returns serverInfo with name "graphiti-memory"
- [ ] `python3 -c "... assert 'graphiti-memory' in c['mcp']"` → OK
- [ ] `sudo systemctl is-enabled neo4j` → enabled
- [ ] `curl -s localhost:11434/api/embed -d '{"model":"nomic-embed-text:latest","input":"test"}' | jq '.embeddings[0] | length'` → 768
