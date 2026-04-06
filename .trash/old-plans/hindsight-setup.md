# Hindsight Local Memory Masterplan (v4 — BLEEDING EDGE)

## TL;DR

> **Goal**: Local Hindsight memory system in `/home/nxyme/nx_openmore/`
> Self-contained (embedded PostgreSQL), Ollama native, 91.4% LongMemEval.
> No Neo4j. No external DB. No cloud. No shortcuts.

## Why Hindsight (Final Decision)

| Benchmark | Hindsight | Graphiti/Zep | Gap |
|-----------|-----------|-------------|-----|
| **LongMemEval** | **91.4%** | 63.8% | **+27.6 points** |
| **LoCoMo** | **89.61%** | ~70% | **+19.6 points** |

| Factor | Hindsight | Graphiti | Your History |
|--------|-----------|----------|--------------|
| External DB | **No** (embedded PostgreSQL) | Yes (Neo4j/FalkorDB) | Neo4j failed 4x |
| Ollama | **Native** (2 env vars) | Via OpenAIGenericClient | You have 8 models |
| Setup | `pip install hindsight-all` | Neo4j + graphiti-core | Simple > complex |
| License | MIT (forkable) | Apache 2.0 | Both fine |
| Community | 6.7k stars, 44 releases | 24.4k stars | Smaller but active |
| Production | Fortune 500 | Zep Cloud | Both production-ready |

## Verified State

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama | ✅ Running | Port 11434, 8 models |
| Python | ⚠️ 3.14.3 | Need dry-run test |
| PostgreSQL | ❌ Not needed | Hindsight uses embedded pg0 |
| Neo4j | ✅ Installed | Keep running (don't touch) |
| Hindsight | ❌ Not installed | `pip install hindsight-all` |
| MCP server | ❌ Not configured | Need to add to opencode.json |

## Execution Plan (3 Phases)

### Phase A: Install & Verify (30 min)

```bash
# 1. Dry-run to check Python 3.14 compatibility
./athena/.venv/bin/pip install --dry-run hindsight-all

# 2. Install
./athena/.venv/bin/pip install hindsight-all

# 3. Verify import
./athena/.venv/bin/python -c "from hindsight import HindsightServer; print('OK')"

# 4. Test with Ollama
export HINDSIGHT_API_LLM_PROVIDER=ollama
export HINDSIGHT_API_LLM_MODEL=qwen2.5:14b
export HINDSIGHT_API_LLM_BASE_URL=http://localhost:11434/v1

# 5. Start server
./athena/.venv/bin/hindsight-api &
# API: http://localhost:8888
# UI: http://localhost:9999

# 6. Test retain/recall
./athena/.venv/bin/python << 'PYEOF'
from hindsight_client import Hindsight
c = Hindsight("http://localhost:8888")
c.retain("test-bank", "I prefer functional programming over OOP")
results = c.recall("test-bank", "What programming style do I prefer?")
print(f"Results: {results}")
PYEOF
```

**QA Scenario A-1** (install):
```bash
./athena/.venv/bin/python -c "from hindsight import HindsightServer; print('OK')"
# EXPECTED: OK
```

**QA Scenario A-2** (retain + recall round-trip):
```bash
./athena/.venv/bin/python -c "
from hindsight_client import Hindsight
c = Hindsight('http://localhost:8888')
c.retain('test-bank', 'The sky is blue')
r = c.recall('test-bank', 'What color is the sky?')
print(f'Found: {len(r)} results')
assert len(r) > 0, 'No results!'
print('PASS')
"
# EXPECTED: Found: >= 1 results\nPASS
```

### Phase B: MCP Integration (15 min)

```bash
# 1. Configure MCP server in OpenCode
python3 << 'PYEOF'
import json
config_path = "config/opencode.json"
with open(config_path) as f:
    config = json.load(f)

config.setdefault("mcp", {})["hindsight-memory"] = {
    "type": "local",
    "command": ["uvx", "--from", "hindsight-api", "hindsight-local-mcp"],
    "environment": {
        "HINDSIGHT_API_LLM_PROVIDER": "ollama",
        "HINDSIGHT_API_LLM_MODEL": "qwen2.5:14b",
        "HINDSIGHT_API_LLM_BASE_URL": "http://localhost:11434/v1",
        "HINDSIGHT_LOCAL_MCP_PORT": "8889",
    },
    "enabled": True,
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print("OK")
PYEOF
```

**QA Scenario B-1** (MCP tools list):
```bash
# MCP exposes 29 tools: retain, recall, reflect, mental models, directives, etc.
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | timeout 15 ./athena/.venv/bin/hindsight-local-mcp 2>&1 | head -1
# EXPECTED: JSON with tools array
```

**QA Scenario B-2** (OpenCode config):
```bash
python3 -c "import json; c=json.load(open('config/opencode.json')); assert 'hindsight-memory' in c.get('mcp',{}); print('OK')"
# EXPECTED: OK
```

### Phase C: Test Full Pipeline (15 min)

```bash
# 1. Retain real knowledge
./athena/.venv/bin/python << 'PYEOF'
from hindsight_client import Hindsight
c = Hindsight("http://localhost:8888")

# Store some facts
c.retain("nxyme", "I use Ollama with nomic-embed-text for 768 dimension embeddings")
c.retain("nxyme", "My system runs CachyOS Linux with 30GB RAM")
c.retain("nxyme", "I prefer bleeding edge local-first tools over cloud services")
c.retain("nxyme", "Neo4j crashed 4 times in previous projects, now using Hindsight")

# Recall
results = c.recall("nxyme", "What embedding model do I use?")
print(f"Recall results: {results}")

# Reflect (agentic reasoning)
reflection = c.reflect("nxyme", "What do I care about in my tech stack?")
print(f"Reflection: {reflection}")
PYEOF
```

**QA Scenario C-1** (knowledge recall):
```bash
./athena/.venv/bin/python -c "
from hindsight_client import Hindsight
c = Hindsight('http://localhost:8888')
r = c.recall('nxyme', 'What OS do I run?')
assert any('CachyOS' in str(x) for x in r), 'Did not find CachyOS'
print('PASS')
"
# EXPECTED: PASS
```

## Directory Structure

```
/home/nxyme/nx_openmore/
├── athena/
│   └── .venv/
│       └── lib/python3.14/site-packages/
│           ├── hindsight/           # Core library
│           ├── hindsight_client/    # Python client
│           └── hindsight_api/       # API server
├── config/
│   └── opencode.json               # Updated with hindsight-memory MCP
└── .sisyphus/plans/
    └── hindsight-setup.md           # This plan
```

## Hindsight Architecture

```
┌─────────────────────────────────────────────────────┐
│            Hindsight Server (port 8888)              │
│  ┌────────┐ ┌────────┐ ┌────────────────┐          │
│  │RETAIN  │ │RECALL  │ │    REFLECT     │          │
│  │(ingest)│ │(search)│ │   (reason)     │          │
│  └────┬───┘ └────┬───┘ └───────┬────────┘          │
│       │          │              │                    │
│  ┌────▼──────────▼──────────────▼────────┐          │
│  │    TEMPR (4 parallel strategies)      │          │
│  │  Semantic │ BM25 │ Graph │ Temporal   │          │
│  │      + RRF fusion + reranker          │          │
│  └───────────────────────────────────────┘          │
│       │                                              │
│  ┌────▼──────────────────────────────────┐          │
│  │  Four-Network Memory Bank             │          │
│  │  World Facts │ Experience │ Observation│          │
│  │  │ Mental Models                       │          │
│  └───────────────────────────────────────┘          │
│       │                                              │
│  ┌────▼──────────────────────────────────┐          │
│  │  Embedded PostgreSQL (pg0)            │          │
│  │  NO EXTERNAL DB NEEDED                │          │
│  └───────────────────────────────────────┘          │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │ Ollama (11434)  │
              │ qwen2.5:14b     │
              │ nomic-embed-text│
              └─────────────────┘
```

## MCP Tools (29 total)

| Category | Tools |
|----------|-------|
| Core | retain, recall, reflect |
| Mental Models | list, get, create, update, delete, refresh |
| Directives | list, create, delete |
| Memories | list, get, delete |
| Documents | list, get, delete |
| Operations | list, get, cancel |
| Banks | list, create, get, delete |
| Tags | list, create, delete |
| Bank Config | get, update |
| Events | list |
| Settings | get |
| Model Info | get |

## Known Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Python 3.14 incompatibility | Medium | Dry-run first; pin version if needed |
| Ollama model quality | Medium | Use qwen2.5:14b (best local model) |
| `reflect` needs tool-calling | Medium | qwen2.5:14b supports tool-calling |
| Breaking changes | Low | Pin to `hindsight-all==0.4.21` |
| Smaller community | Low | Slack exists, team responds to issues |
| Neo4j data (3,881 nodes) | Low | Don't migrate — start fresh with Hindsight |

## Success Criteria

- [ ] `pip install hindsight-all` succeeds in venv
- [ ] `from hindsight import HindsightServer` imports OK
- [ ] Server starts on port 8888
- [ ] Retain stores a fact
- [ ] Recall retrieves the fact
- [ ] Reflect generates reasoning
- [ ] MCP server exposes 29 tools
- [ ] OpenCode config shows hindsight-memory MCP
- [ ] Ollama embeddings work (no API keys needed)

## Commit Strategy

- Commit after Phase A passes all QA scenarios
- Commit after Phase B passes MCP integration
- Commit after Phase C passes full pipeline
- Message: `feat(memory): add Hindsight local memory system`
