---
epic_id: E-105
title: "Configuration Consolidation"
priority: P2
stories: 3
points: 5
created: 2026-05-11
sprint: sprint-3
status: pending
bmad_agents:
  lead: Amelia (dev)
---

# Epic E-105: Configuration Consolidation

**Priority:** P2 | **Stories:** 3 | **Points:** 5 | **Risk:** LOW

## Epic Goal

Consolidate scattered configuration, make systemd services portable, and add missing docker-compose scaffold.

## Rationale

- Configuration scored 72/100 (B-)
- Hardcoded paths in systemd services break portability
- .env.example drift is a developer onboarding friction
- docker-compose would simplify local development

## Success Criteria

1. All systemd service files use portable paths
2. .env.example synced with actual .env
3. docker-compose.yml works for main application

---

## Story S-501: systemd Service Path Portability

**Story ID:** S-501 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Verification | **DEPENDS:** None | **BLOCKS:** S-503

### What
5+ systemd service files have hardcoded `/home/nxyme/` paths. Replace with `$HOME` or relative paths.

### Files
- `~/.config/systemd/user/` (systemd service files)
- Or `.config/systemd/user/` in project

### Root Cause
`/home/nxyme/` hardcoded in `ExecStart`, `WorkingDirectory`, etc. Fails on any other machine.

### Acceptance Criteria
- AC-501.1: All `/home/nxyme/` replaced with `$HOME` in ExecStart, WorkingDirectory, etc.
- AC-501.2: Paths use environment variable expansion where appropriate
- AC-501.3: `systemctl --user daemon-reload` succeeds
- AC-501.4: `systemctl --user start <service>` works (or fails for expected reasons)
- AC-501.5: No hardcoded paths in any `.service` file

### QA Commands
```bash
# Find hardcoded paths
grep -r "home/nxyme" ~/.config/systemd/user/*.service

# Verify portability
cat ~/.config/systemd/user/*.service | grep -v "HOME"
# Should use $HOME or %h

# Test daemon-reload
systemctl --user daemon-reload && echo "SUCCESS"
```

### Atomic Commit
```
fix(systemd): use portable paths in service files
```

---

## Story S-502: .env.example Divergence Fix

**Story ID:** S-502 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Verification | **DEPENDS:** None

### What
.env.example diverged from actual .env. Sync variables, add descriptions.

### Files
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.env` (actual)
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.env.example` (template)

### Root Cause
Variables added to .env but not reflected in .env.example. New developers get broken setup.

### Acceptance Criteria
- AC-502.1: All actual .env variables reflected in .env.example
- AC-502.2: Comments describe each variable's purpose
- AC-502.3: Required vs optional variables marked
- AC-502.4: Sensitive values redacted (show format, not actual value)
- AC-502.5: No extraneous variables in .env.example

### QA Commands
```bash
# Compare variables
diff <(grep -v '^#' .env | cut -d= -f1 | sort) <(grep -v '^#' .env.example | cut -d= -f1 | sort)

# Check descriptions
grep -v '^#' .env.example | grep -v '^[A-Z_]*='  # Should have comments
```

### Atomic Commit
```
fix(config): sync .env.example with actual .env
```

---

## Story S-503: docker-compose for Main Application

**Story ID:** S-503 | **Points:** 1 | **Priority:** LOW | **TDD:** Verification | **DEPENDS:** S-501

### What
No docker-compose for main application. Add `docker-compose.yml` covering all services.

### Files
- `docker-compose.yml` (create)
- `docs/DOCKER.md` (create)

### Services to Include
1. **GGUF inference server** (llama-server)
2. **SOCKS5 proxies** (8 proxies on ports 1080-1087)
3. **MCP servers** (brain_mcp, nx_mcp, etc.)
4. **OpenCode TUI** (optional — may not need docker)

### Acceptance Criteria
- AC-503.1: `docker-compose.yml` exists at project root
- AC-503.2: All main services included (GGUF, proxies, MCP)
- AC-503.3: `docker compose config` passes (valid YAML, no errors)
- AC-503.4: `docker compose up` starts all services successfully
- AC-503.5: `docker compose down` cleans up gracefully
- AC-503.6: `docs/DOCKER.md` documents usage

### QA Commands
```bash
# Validate compose file
docker compose config > /dev/null && echo "VALID YAML"

# Test up/down
docker compose up -d && sleep 5 && docker compose ps
docker compose down

# Check all services start
docker compose up -d
docker compose ps | grep -c "Up"  # Should show all services up
docker compose down
```

### Atomic Commit
```
feat(docker): add docker-compose for main application
```

---

## Quality Gates (All Stories)

| Gate | Command | Must Pass |
|------|---------|-----------|
| Typecheck | N/A | N/A (config-only) |
| Lint | `docker compose config` | Valid YAML |
| Format | `yamllint docker-compose.yml` | Zero errors |
| Tests | N/A | N/A (config-only) |
| Secrets | `gitleaks detect --verbose` | Zero leaks |

---

## Timeline & Dependencies

| Wave | Day | Stories | Dependencies |
|------|-----|---------|--------------|
| Wave 1 | Day 5-8 | S-501: systemd paths | None |
| Wave 1 | Day 5-8 | S-502: .env sync | None |
| Wave 2 | Day 8-9 | S-503: docker-compose | S-501 |

---

## Definition of Done

All of the following must be true for this epic to be DONE:

1. All systemd services use `$HOME` instead of `/home/nxyme/`
2. .env.example is in sync with actual .env
3. docker-compose.yml works for all main services
4. All 3 commits merged
5. Configuration audit score improves from **72/100 to 85+/100**