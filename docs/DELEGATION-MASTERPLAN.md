# N-Xyme_MIND — Delegation Masterplan

> **Generated**: 2026-04-03 | **Status**: Active | **Version**: 1.0

---

## Overview

This document maps all remaining work across **Sprint 3-5** to the appropriate agents for delegation.

---

## Agent Capability Matrix

| Agent | Role | Best For | Avoid |
|-------|------|----------|-------|
| **Sisyphus** | Orchestrator | Delegation, planning, coordination | Direct implementation |
| **Prometheus** | Plan Builder | Detailed implementation plans | Quick fixes |
| **Hephaestus** | Implementation | Code writing, file creation | Research |
| **Oracle** | Architecture | Design review, schema validation | Fast tasks |
| **Momus** | Adversarial | Edge case finding, critical analysis | Building |
| **Metis** | Pre-Planning | Gap analysis, scope definition | Execution |
| **Atlas** | Executor | Step-by-step plan execution | Planning |
| **Explore** | Search | Codebase patterns, file discovery | Writing |
| **Librarian** | Research | External docs, web search | Internal code |
| **Sisyphus-Junior** | Light Tasks | Simple fixes, quick changes | Complex logic |

---

## Work Breakdown by Sprint

### 🔄 Sprint 3 — Completeness (In Progress)

| Task | Agent | Subagents | Priority | Est. Time |
|------|-------|-----------|----------|-----------|
| Wire VPN configs | **Prometheus** | Atlas (execute) | High | 2h |
| Activate trigger engine | **Hephaestus** | Explore (find code) | High | 3h |
| Add more MCPs | **Metis** | Hephaestus (install) | Medium | 2h |
| Ollama models pull | **Hephaestus** | — | Medium | 1h |

### 📋 Sprint 4 — Integration (Next)

| Task | Agent | Subagents | Priority | Est. Time |
|------|-------|-----------|----------|-----------|
| Integrate CATALYST modules | **Oracle** | Hephaestus (wire) | High | 4h |
| VPN rotator automation | **Prometheus** | Hephaestus (script) | High | 3h |
| Trigger engine automation | **Metis** | Atlas (execute) | High | 2h |
| BMAD workflow integration | **Oracle** | Momus (review) | Medium | 3h |
| Create integration tests | **Hephaestus** | — | Medium | 2h |

### 🚀 Sprint 5 — Features (Future)

| Task | Agent | Subagents | Priority | Est. Time |
|------|-------|-----------|----------|-----------|
| Custom MCP servers | **Hephaestus** | Oracle (design) | High | 6h |
| Memory consolidation | **Oracle** | Explore (audit) | High | 4h |
| Multi-machine sync | **Prometheus** | Hephaestus (impl) | Medium | 5h |
| Performance optimization | **Metis** | Hephaestus (tune) | Medium | 3h |
| Community contributions | **Librarian** | — | Low | 2h |

---

## Wave 1: Sprint 3 Completion (Immediate)

### Task 1: Wire VPN Configs

**Delegation Chain**: Sisyphus → Prometheus → Atlas

```
Sisyphus:
  → Delegate to Prometheus: "Create VPN config wiring plan for protonvpn, mullvad, nordvpn"
  → Prometheus creates plan with:
      - Download ProtonVPN WireGuard configs (manual step, user confirms)
      - Update rotator.py to use configs from providers/*/configs/
      - Test VPN rotation with 3 providers
      - Document usage in docs/VPN-ROTATOR.md
  → Prometheus → Atlas: Execute VPN wiring plan
  → Atlas reports completion
  → Sisyphus verifies with Momus (adversarial review)
```

**Files Involved**:
- `vpn/rotator.py` (update)
- `vpn/providers/*/configs/` (create)
- `docs/VPN-ROTATOR.md` (create)

---

### Task 2: Activate Trigger Engine

**Delegation Chain**: Sisyphus → Metis → Hephaestus

```
Sisyphus:
  → Delegate to Metis: "Analyze trigger_engine.py, identify gaps vs triggers.json"
  → Metis produces gap analysis:
      - List missing handlers
      - List unbound triggers
      - Create activation plan
  → Metis → Hephaestus: Implement trigger bindings
  → Hephaestus wires triggers.json → trigger_engine.py
  → Hephaestus adds PM2 integration
  → Metis verifies completion
  → Sisyphus validates with Oracle (architecture review)
```

**Files Involved**:
- `src/trigger_engine.py` (fix)
- `src/trigger_router.py` (update)
- `triggers.json` (integrate)
- `bin/health-*.sh` (wire to triggers)

---

### Task 3: Add More MCPs

**Delegation Chain**: Sisyphus → Metis → Hephaestus

```
Sisyphus:
  → Delegate to Metis: "Audit MCP_REGISTRY.md, identify high-ROI MCPs to add"
  → Metis produces recommendation:
      - Priority MCPs: mcp-server-git, mcp-server-fetch-typescript
      - Install commands
      - Config required
  → Metis → Hephaestus: Install and configure MCPs
  → Hephaestus adds to opencode.json mcp config
  → Hephaestus creates systemd/PM2 entries
  → Metis verifies MCPs online
  → Sisyphus documents in MCP_REGISTRY.md (update)
```

**Files Involved**:
- `~/.config/opencode/opencode.json` (update)
- `docs/MCP_REGISTRY.md` (update)

---

## Wave 2: Sprint 4 Preparation (After Wave 1)

### Task 4: CATALYST Integration

**Delegation Chain**: Sisyphus → Oracle → Hephaestus → Momus

```
Sisyphus:
  → Delegate to Oracle: "Design CATALYST module integration architecture"
  → Oracle produces architecture doc in docs/CATALYST-INTEGRATION.md:
      - Which modules to integrate
      - Data flow between systems
      - API contracts
  → Oracle → Hephaestus: Implement CATALYST wiring
  → Hephaestus creates bridge code
  → Hephaestus → Momus: Adversarial review of integration
  → Momus finds edge cases
  → Hephaestus fixes issues
  → Oracle approves final integration
```

**Files Involved**:
- `src/*catalyst*` (integrate)
- `_bmad/catalyst/` (wire to MIND)
- `docs/CATALYST-INTEGRATION.md` (create)

---

### Task 5: VPN Rotator Automation

**Delegation Chain**: Sisyphus → Prometheus → Hephaestus

```
Sisyphus:
  → Delegate to Prometheus: "Create automated VPN rotation plan"
  → Prometheus produces automation plan:
      - Triggers: rate limit hit, IP blocked, 429 error
      - Actions: rotate to next provider, log, notify
      - Health check integration
  → Prometheus → Hephaestus: Implement rotator automation
  → Hephaestus updates rotator.py with auto-rotate logic
  → Hephaestus adds systemd timer for periodic rotation
  → Prometheus verifies with test run
```

---

### Task 6: Trigger Engine Automation

**Delegation Chain**: Sisyphus → Metis → Atlas

```
Sisyphus:
  → Delegate to Metis: "Design trigger-based automation workflows"
  → Metis creates automation triggers:
      - Session start → load context, check health
      - Task complete → update memory, log metrics
      - Error → log to DLQ, notify if critical
      - Heartbeat (30min) → disk check, MCP check, process check
  → Metis → Atlas: Implement automation workflows
  → Atlas wires triggers to scripts
  → Metis validates with health check run
```

---

## Wave 3: Sprint 5 Planning (Future)

### Task 7: Custom MCP Servers

**Delegation Chain**: Sisyphus → Oracle → Hephaestus

```
Sisyphus:
  → Delegate to Oracle: "Design custom MCP servers for N-Xyme_MIND"
  → Oracle recommends:
      - athena-context-mcp: Context injection server
      - nx-mind-mcp: MIND state management
      - trigger-guardian-mcp: Trigger monitoring
  → Oracle → Hephaestus: Build MCP servers
  → Hephaestus implements in packages/
  → Oracle reviews implementation
  → Sisyphus adds to opencode.json
```

---

### Task 8: Memory Consolidation

**Delegation Chain**: Sisyphus → Oracle → Explore → Hephaestus

```
Sisyphus:
  → Delegate to Oracle: "Design unified memory architecture"
  → Oracle produces memory consolidation plan:
      - Graphiti (episodic)
      - Hindsight (session)
      - Memory MCP (cross-session)
      - Unification strategy
  → Oracle → Explore: Audit current memory usage
  → Explore produces memory usage report
  → Oracle → Hephaestus: Implement consolidation
  → Hephaestus wires unified memory API
  → Momus tests edge cases
```

---

## Execution Protocol

### Before Delegation

1. **Check Agent Availability**: Verify agent not busy (session-state.json)
2. **Verify Model Status**: Ensure model not discontinued (just fixed!)
3. **Prepare Context**: Read relevant docs, prepare file paths

### Delegation Command Format

```bash
task(
  description="[TASK NAME]",
  prompt="""[DETAILED PROMPT]

## Context
- Working dir: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
- Files: [RELEVANT FILES]
- Previous state: [IF ANY]

## Deliverables
1. [DELIVERABLE 1]
2. [DELIVERABLE 2]

## Verification
Run: [VERIFICATION COMMAND]
Expected: [EXPECTED OUTPUT]""",
  subagent_type="[AGENT NAME]",
  load_skills=[],
  run_in_background=false
)
```

### Post-Delivery Verification

1. Run quality gates for code changes
2. Verify no hardcoded paths introduced
3. Check JSON configs valid
4. Test with Momus (adversarial) if significant

---

## Emergency Fallbacks

| Scenario | Action |
|----------|--------|
| Agent hangs (>5min) | Switch to fallback model in oh-my-opencode.json |
| Agent fails twice | Escalate to next agent in chain |
| Config breaks | Restore from backup, validate schema |
| Disk full | Run health-l2-vitals.sh, clean old sessions |

---

*Delegation Masterplan v1.0 | N-Xyme_MIND*
