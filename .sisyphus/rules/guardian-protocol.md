# N-Xyme Catalyst - Guardian Protocol
# Anti-breakage rules for all agents and workflows

## PURPOSE
Prevent the system from breaking again. Every agent must follow these rules before making changes.

---

## RULE 1: PRE-FLIGHT GATE (MANDATORY)
Before ANY work session:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\preflight-gate.ps1
```
- Exit code 1 = BLOCKED. Fix issues before proceeding.
- Exit code 0 = PROCEED.

---

## RULE 2: NEVER BREAK SHELL
| DO | DON'T |
|----|-------|
| Test profiles with `-NoProfile` first | Edit profiles without testing |
| Check PATH for duplicates before adding | Assume PATH is clean |
| Use `Test-Path` before `Set-Location` | Hardcode paths without validation |

**Shell test command:**
```powershell
powershell -NoProfile -Command "Write-Host 'Clean shell works'"
```

---

## RULE 3: NEVER BREAK ENV VARS
| DO | DON'T |
|----|-------|
| Use `.env` file for all secrets | Hardcode passwords in source |
| Verify env vars exist before using | Assume env vars are set |
| Document required vars in `.env.example` | Leave vars undocumented |

**Env var test:**
```powershell
if (-not $env:NEO4J_PASSWORD) { Write-Host "NEO4J_PASSWORD not set!" -ForegroundColor Red }
```

---

## RULE 4: NEVER BREAK PM2
| DO | DON'T |
|----|-------|
| `pm2 save` after any change | Restart PM2 without saving |
| Check `pm2 list` before assuming status | Assume processes are running |
| Use `pm2 restart <name>` for single service | `pm2 kill` without reason |

**PM2 test command:**
```powershell
pm2 list
curl http://localhost:8001/health
```

---

## RULE 5: NEVER BREAK MCP SERVERS
| DO | DON'T |
|----|-------|
| Test health endpoint after changes | Assume MCP is working |
| Check `ecosystem.config.js` for env vars | Change MCP code without config update |
| Use `pm2 restart <name>` for MCP changes | Kill MCP processes manually |

**MCP test command:**
```powershell
foreach ($port in 12010,12011,12012,12013,12014,11435,12001,12002,12003,12020,12021,12022,12023,8001) {
    curl -s http://localhost:$port/health | Out-Null
    if ($?) { Write-Host "Port $port: OK" -ForegroundColor Green }
}
```

---

## RULE 6: NEVER BREAK CONFIGS
| DO | DON'T |
|----|-------|
| Validate JSON before saving | Edit JSON without linting |
| Cross-reference paths in configs | Assume paths exist |
| Keep `.env.example` in sync with `.env` | Let configs drift |

**Config validation:**
```powershell
Get-Content "C:\Users\N-Xyme\.config\opencode\opencode.json" | ConvertFrom-Json | Out-Null
if ($?) { Write-Host "Config valid" }
```

---

## RULE 7: CHANGE VALIDATION (POST-FLIGHT)
After ANY config/code change:
1. Run pre-flight gate again
2. Verify affected service health endpoint
3. Check PM2 status for that service
4. Test shell profiles still load

**Post-flight command:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\preflight-gate.ps1
```

---

## RULE 8: KNOWN HAZARDS (DO NOT TOUCH)

| Hazard | Why Dangerous |
|--------|---------------|
| `D:\00_CODING` in any profile | Wrong path, shell hangs |
| PSReadLine 2.0.0 | 5-minute startup |
| Empty NEO4J_PASSWORD | Graphiti crashes |
| `pm2 kill` | Kills all MCP servers |
| Deleting `.env` | All env-dependent services fail |
| Removing `npm` from PATH | PM2, node, npm all break |

---

## RULE 9: SAFE COMMANDS REFERENCE

| Task | Safe Command |
|------|--------------|
| Start all MCPs | `pm2 start ecosystem.config.js` |
| Restart one MCP | `pm2 restart graphiti-mcp` |
| Check system health | `scripts\preflight-gate.ps1` |
| Fix PATH duplicates | `scripts\fix-system-path.ps1` (admin) |
| Update PSReadLine | `Install-Module PSReadLine -Force` |
| Test shell | `powershell -NoProfile -Command "exit"` |

---

## RULE 10: EMERGENCY RECOVERY

If system is broken:
1. Run `scripts\preflight-gate.ps1 -Fix`
2. Check PM2: `pm2 list`
3. Restart services: `pm2 start ecosystem.config.js`
4. Verify: `scripts\preflight-gate.ps1`

If shell is broken:
1. Open CMD (not PowerShell)
2. Run: `powershell -NoProfile -Command "Remove-Item $PROFILE -Force"`
3. Restart terminal
4. Run: `scripts\preflight-gate.ps1 -Fix`

---

## ENFORCEMENT
- OpenCode agents: Check pre-flight before any task
- Human: Run pre-flight before starting work
- CI/CD: Block merge if pre-flight fails
