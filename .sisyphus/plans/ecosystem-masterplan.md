# N-Xyme OpenMore Ecosystem Masterplan

## TL;DR

> **Goal**: Fix broken Graphiti global memory and Athena MCP installation.
> - Neo4j is NOT running (port 7474 down) - this is why memory is broken
> - Graphiti configs scattered across 6 locations - need consolidation
> - Athena MCP server never installed properly
> - 471 legacy sessions exist but not searchable
>
> **Deliverables**:
> 1. Start Neo4j → verify Graphiti works
> 2. Consolidate Graphiti config to one location
> 3. Install Athena as proper MCP server
> 4. Compile all 471 legacy sessions into searchable format
> 5. Drift detection script to prevent future breakage

---

## Context

### Root Cause
- Neo4j not running → Graphiti can't connect → global memory broken
- Graphiti configs in 6 different locations → system loads wrong one
- Athena was installed as plugin, not MCP server → chat compilation doesn't work
- 471 sessions in deprecated directory → not accessible from current instance

### User Requirements
- All chats compiled and searchable across the ENTIRE PC
- Athena working as MCP server (NOT plugin)
- Graphiti global memory working
- Config that survives restarts

---

## TODOs

### Wave 1: Infrastructure (IMMEDIATE)

- [ ] 1. Start Neo4j

  **What to do**:
  - Start Neo4j service at /home/nxyme/opt/neo4j/neo4j-community-2026.02.3/bin/neo4j
  - Verify port 7474 is listening
  - Verify Neo4j responds to queries

  **Acceptance Criteria**:
  - [ ] `ss -tlnp | grep 7474` shows LISTEN
  - [ ] `curl -s http://localhost:7474/` returns Neo4j UI

- [ ] 2. Start Graphiti MCP server

  **What to do**:
  - Check if Graphiti MCP server is at port 8001
  - If not running, start it
  - Verify it can connect to Neo4j

  **Acceptance Criteria**:
  - [ ] `curl -s http://localhost:8001/health` returns {"status":"ok"}

- [ ] 3. Fix Graphiti config

  **What to do**:
  - Consolidate graphiti.jsonc to ONE location: `/home/nxyme/nx_openmore/.opencode/config/graphiti.jsonc`
  - Set endpoint to http://localhost:8001
  - Verify write/read cycle works

  **Acceptance Criteria**:
  - [ ] Graphiti write succeeds
  - [ ] Graphiti search returns results

### Wave 2: Athena MCP

- [ ] 4. Install Athena as MCP server

  **What to do**:
  - Find athena-agent package
  - Configure as MCP server in opencode.json
  - Test that Athena can search chats

  **Acceptance Criteria**:
  - [ ] Athena MCP server responds
  - [ ] Can query Athena for chat history

### Wave 3: Chat Compilation

- [ ] 5. Compile all legacy sessions

  **What to do**:
  - Read all 471 sessions from deprecated directory
  - Extract chat history from each
  - Store in Graphiti as searchable episodes
  - Make accessible via Athena or Graphiti search

  **Acceptance Criteria**:
  - [ ] All 471 sessions indexed
  - [ ] Can search across all chats
  - [ ] Old conversations are accessible

### Wave 4: Bulletproofing

- [ ] 6. Create startup script

  **What to do**:
  - Script that starts: Neo4j → Graphiti MCP → Athena MCP → OpenCode
  - Health check each service
  - Auto-fix drift if detected

  **Acceptance Criteria**:
  - [ ] Single command starts entire ecosystem
  - [ ] Health checks pass

- [ ] 7. Drift detection

  **What to do**:
  - Script that checks config integrity on startup
  - Auto-fixes known issues
  - Alerts on new issues

  **Acceptance Criteria**:
  - [ ] Script detects missing Neo4j
  - [ ] Script detects wrong configs

---

## Verification

```bash
# Check Neo4j
ss -tlnp | grep 7474

# Check Graphiti
curl -s http://localhost:8001/health

# Check config
cat /home/nxyme/nx_openmore/.opencode/config/opencode.json | jq '.model'

# Run startup
bash /home/nxyme/nx_openmore/bin/start-ecosystem.sh
```
