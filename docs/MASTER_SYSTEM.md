# N-Xyme MIND - MASTER SYSTEM DOCUMENT

**Last Updated:** 2026-03-30  
**Status:** ✅ WORKING

---

## 🎯 ONE-LINER

AI agent workspace for ADHD devs - combines OpenCode + Graphiti memory + 16 MCP servers + multi-agent orchestration. NO Docker, native Linux (CachyOS).

---

## 🖥️ HARDWARE

| Component | Spec |
|-----------|------|
| CPU | AMD Ryzen 7 7800X3D (8C/16T, 104MB cache) |
| GPU | RTX 3080 Ti (12GB VRAM) |
| RAM | 32GB DDR5 |
| OS | CachyOS Linux (native, no Docker) |
| Storage | 17GB total: 2.9GB captures + 1.1GB Neo4j + backups |

---

## 🧠 MEMORY (CONSOLIDATED)

### Primary: Graphiti + Neo4j
- **Location:** `/home/nxyme/N-Xyme_MIND/data/neo4j/`
- **Endpoint:** `http://localhost:8001`
- **Status:** ✅ RUNNING
- **Migrated Memories:** 31+ consolidated

### Configuration
```
codebase-memory lobes: /home/nxyme/N-Xyme_MIND ✅
graphiti plugin: @happycastle/opencode-graphiti@latest ✅
```

### Memory Sources (ALL CONSOLIDATED TO GRAPHITI)
| Source | Before | After |
|--------|--------|--------|
| mind_from_mind.db (323 memories) | Scattered | ✅ Graphiti |
| CATALYST external | Backup only | N/A |
| Neo4j (1.1GB) | Active | ✅ Active |
| Captures (2.9GB) | Audio/Screenshots | N/A |

---

## 🤖 AGENTS (11 CONFIGURED)

| Agent | Model | Purpose |
|-------|-------|---------|
| **Sisyphus** | mimo-v2-pro-free | Primary orchestrator |
| **Hephaestus** | mimo-v2-pro-free | Deep research |
| **Oracle** | mimo-v2-pro-free | Architecture/debugging |
| **Prometheus** | mimo-v2-pro-free | Plan builder |
| **Metis** | mimo-v2-pro-free | Plan consultant |
| **Momus** | mimo-v2-pro-free | Plan critic |
| **Atlas** | mimo-v2-pro-free | Plan executor |
| **Plan** | mimo-v2-pro-free | Multi-step planner |
| **Librarian** | gpt-5-nano | External docs |
| **Explore** | gpt-5-nano | Internal code |
| **Multimodal-Looker** | mimo-v2-omni-free | Vision/media |

---

## 🔌 MCP SERVERS (16 ENABLED)

| MCP | Status | Purpose |
|-----|---------|----------|
| graphiti | ✅ | Memory/knowledge graph |
| ollama | ✅ | Local models |
| context7 | ✅ | Docs lookup |
| github | ✅ | GitHub API |
| obsidian | ✅ | Notes |
| playwright | ✅ | Browser automation |
| fetch | ✅ | Web fetching |
| exa | ✅ | Web search |
| grep-app | ✅ | Code search |
| sqlite | ✅ | Database |
| slack | ✅ | Slack integration |
| linear | ✅ | Linear integration |
| kubernetes | ✅ | K8s management |
| terraform | ✅ | IaC |
| discord | ✅ | Discord bot |
| codetidy | ✅ | Code utilities |

---

## 📦 PLUGINS

| Plugin | Status |
|--------|--------|
| oh-my-opencode | ✅ |
| @happycastle/opencode-graphiti | ✅ |
| opencode-akane | ✅ |
| opencode-agent-skills | ✅ |
| opencode-skill-activation | ✅ |
| opencode-router | ✅ |
| opencode-gateway | ✅ |

---

## ⚙️ CONFIG FILES

| File | Location |
|------|-----------|
| **oh-my-opencode.json** | `~/.config/opencode/` |
| **opencode.json** | `~/.config/opencode/` |
| **model-router.json** | `~/.config/opencode/` |
| **AGENTS.md** | `~/.config/opencode/` |
| **graphiti.jsonc** | `~/.config/opencode/` |

---

## 🔧 OPTIMIZATIONS (TODAY)

### Compression - DISABLED ✅
```json
"compaction": {
  "auto": false,
  "prune": false,
  "reserved": 50000
}
```

### Hooks - ENABLED
- session-recovery: ✅
- think-mode: ✅
- ultrawork: ✅

### Hooks - DISABLED
- context-window-monitor: ❌ (was causing stops)
- preemptive-compaction: ❌

### Models - BEST FREE
- Primary: `mimo-v2-pro-free` (priority #1)
- Quick: `gpt-5-nano`
- Vision: `mimo-v2-omni-free`

---

## 📊 PARALLEL LIMITS

| Limit | Value |
|-------|-------|
| maxConcurrentAgents | 8 |
| maxConcurrentBackgroundTasks | 12 |
| maxConcurrentExplore | 8 |
| maxConcurrentLibrarian | 4 |
| maxConcurrentOracle | 2 |
| maxConcurrentDeep | 4 |

---

## 🔐 SECURITY

- API keys: `/home/nxyme/N-Xyme_MIND/secrets/`
- No secrets in commits
- Local Ollama (zero cost)

---

## 📝 QUICK REFERENCE

```bash
# Restart OpenCode
pkill -f "opencode serve" && opencode

# Check Graphiti
curl http://localhost:8001/health

# Check memory consolidation
sqlite3 /home/nxyme/N-Xyme_MIND/data/memory/mind_from_mind.db "SELECT COUNT(*) FROM memories;"
```

---

## 🚀 STARTUP

1. `opencode` - Gateway serves at localhost:3000
2. Graphiti auto-connects
3. Memories auto-inject at session start

---

## 💎 KEY MEMORIES (CONSOLIDATED)

| Fact | Value |
|------|--------|
| **Your Codename** | MIMIR |
| **Project Codename** | ORBIT, ALPHA-BLUE |
| **Theme** | dark |
| **Voice Hotkey** | ctrl+shift+v |
| **Local LLM** | llama3.2:3b |
| **Embedding Model** | mxbai-embed-large (1024d) |

### Embedding Models Available (Ollama)
| Model | Status |
|-------|--------|
| mxbai-embed-large:latest | ✅ Graphiti uses this |
| nomic-embed-text:latest | Available |
| **Preferred Mode** | focus mode |
| **Smoke Color** | blue (test) |

---

## 🚀 MODEL CAPABILITIES (Best Free)

### OpenCode Zen (All Free)
| Model | Best For | Context |
|-------|----------|---------|
| **mimo-v2-pro-free** | Everything (DEFAULT) | 128K |
| mimo-v2-omni-free | Vision/images | 128K |
| gpt-5-nano | Fast/quick tasks | 128K |
| kimi-k2.5-free | Reasoning | 128K |
| claude-sonnet-4 | Coding | 128K |
| qwen3-coder | Coding | 128K |

---

## 🔌 MCP CAPABILITIES

### Graphiti Memory (15 tools)
- graphiti_add_episode
- graphiti_search_nodes
- graphiti_vector_search
- graphiti_hybrid_search
- graphiti_adhd_search
- graphiti_backfill_embeddings

### Browser (Playwright)
- Navigate, click, fill forms
- Screenshots, snapshots
- Network capture

### Web (Fetch/Exa)
- Raw/rendered HTML, markdown
- Web search, code search

### Local (Ollama)
- 9 models loaded
- Embeddings: mxbai-embed-large

### Integrations
- GitHub: repos, issues, PRs
- Obsidian: notes, search
- Slack/Discord: messaging
- Linear: issues, projects
- Kubernetes: pods, logs, exec
- Terraform: IaC

---

## ⚠️ NOTES

- Configs stay in `~/.config/opencode/` (NOT N-Xyme_MIND)
- Memory consolidated to N-Xyme_MIND/ + Graphiti
- 17GB total storage used
