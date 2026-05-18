# Workflow Synthesis Engine — Master Plan & Handoff

**Date:** 2026-05-18 (Session: ~14h build marathon)
**Author:** Nxyme + Hephaestus + Prometheus + Momus + Metis + Librarian
**Status:** Planning complete, build not started
**Estimated MVP:** 2 hours | **Full scope:** 11.5 hours

---

## 0. Executive Summary

Build a voice-activated workflow engine that bridges the N-Xyme MIND documentation stack with the Jarvis dictation pipeline. User speaks → Whisper GPU → text → router → documented procedure executes → TTS response.

### The Consensus (Momus + Metis both agreed)
- **SCOPE-REDUCE** to a 2h regex MVP
- Fix config drift FIRST
- Test the tray rebuild BEFORE building on top of it
- Confirmation gate contradicts "frictionless" — omit for v1

---

## 1. Current System State

### Running ✅
| Component | File | Status |
|-----------|------|--------|
| **Dictation** | `nx_dictate/` (systemd `nx-dictate.service`) | GPU Whisper, C920 mic, tray rebuilt (1107 lines) |
| **Jarvis Bridge** | `services/jarvis/jarvis_bridge.py` (systemd `jarvis-bridge.service`) | FIFO → rosetta-v13 LLM → TTS |
| **Compiled Agent** | `bins/hephaestus-agent` (296K ELF) | Mojo 1.0 MCP server, registered in `opencode.json` |
| **Memory Vectors** | `data/memory/vectors/` (133MB) | 11,251 vectors, 10 agents, MiniLM 384-dim |
| **Dashboard** | `services/dashboard/dashboard.py` (557 lines) | TUI, monitors CPU/GPU/services/dictation |
| **MCP Servers** | `opencode.json` | bmad, bash_mcp, nx-tools, hephaestus-agent (all enabled) |
| **Embeddings** | `data/memory/models/embedding.onnx` | MiniLM ONNX, pooled 384-dim output, verified working |

### Broken/Missing ❌
| Issue | File | Priority |
|-------|------|----------|
| Config drift | `opencode.json` vs `config/nx_agents.json` | 🔴 MUST FIX FIRST |
| Tray untested | `nx_dictate/ui/tray.py` (rebuilt by Hephaestus) | 🔴 MUST TEST |
| FIFO race condition | `jarvis-pc` reads same FIFO as `jarvis_bridge.py` | 🟡 |
| Compiled agent not in nx_agents.json | `config/nx_agents.json` missing MCP entry | 🔴 |
| No voice commands for system actions | `jarvis_bridge.py` | This is the entire project goal |

---

## 2. Known Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Developer fatigue** — user 12+ hours in session | HIGH | HIGH — breaks voice | Hard stop at 2h |
| **Config drift** — MCP entry missing from nx_agents.json | CERTAIN | HIGH | Fix in step 1 |
| **Tray crashes** — 1107 lines untested | MED | MED | Test before adding workflow |
| **ONNX model fails** — corrupt or incompatible | LOW | HIGH | Fallback to regex-only routing |
| **Wrong Python venv** — systemd uses main venv | MED | HIGH | Always use `/home/nxyme/N-Xyme_CODE/venv/bin/python3` |

---

## 3. Implementation Plan (2h MVP)

### Phase 0 — Prerequisites (20 min)

#### 0.1 Fix config drift
```python
# Add to config/nx_agents.json MCP section:
{
  "name": "hephaestus-agent",
  "command": ["/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bins/hephaestus-agent"],
  "enabled": true,
  "timeout": 15000,
  "protocol": "mcp",
  "transport": "stdio"
}
```
**Files:**
- `config/nx_agents.json` — target (lines 60-110)
- `opencode.json` — reference (lines 61-68 already have it)

#### 0.2 Test the tray
```bash
# Run tray standalone to verify it doesn't crash:
systemctl --user restart nx-dictate
journalctl --user -u nx-dictate --no-pager -n 10 | grep -i "tray"
```
**Files:**
- `nx_dictate/ui/tray.py` — 1107 lines, rebuilt by Hephaestus
- Check `Tray started` in journalctl output

#### 0.3 Verify ONNX model output
```bash
python3 -c "
import onnxruntime as ort
m = ort.InferenceSession('data/memory/models/embedding.onnx')
print('Inputs:', [(i.name, i.shape) for i in m.get_inputs()])
print('Outputs:', [(o.name, o.shape) for o in m.get_outputs()])
"
```
Expected: `tanh` output shape `(batch, 384)` — already verified working.

### Phase 1 — Voice Commands (30 min)

#### 1.1 Add system command handler to jarvis_bridge.py

**Integration point:** `services/jarvis/jarvis_bridge.py` line 209 — replace `response = query_llama(text)` with routing.

```python
# ── Voice command registry (Tier 1: regex) ──
import re, subprocess

COMMANDS = [
    # (regex_pattern, handler_function, description)
    (r"restart dictation", "handle_restart_dictation", "Restart the dictation service"),
    (r"(gpu|graphics) (status|info|temp|memory)", "handle_gpu_status", "GPU information"),
    (r"system status|how is the system", "handle_system_status", "System health overview"),
    (r"(memory|ram) (status|usage|info)", "handle_memory_status", "Memory usage"),
    (r"(services|what.*running)", "handle_list_services", "List running services"),
    (r"(compiled|mojo|agent) (agent|status|context)", "handle_agent_status", "Compiled agent status"),
    (r"who are you", "handle_agent_identity", "Agent identity"),
    (r"search memory for (.+)", "handle_search_memory", "Search memory vectors"),
    (r"help|what can you do", "handle_help", "List available commands"),
    (r"status", "handle_full_status", "Full system status"),
]

def handle_restart_dictation():
    r = subprocess.run(["systemctl", "--user", "restart", "nx-dictate"], capture_output=True, text=True, timeout=10)
    return f"Dictation restarted. Service: {r.stdout.strip() or 'running'}."

def handle_gpu_status():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5
    )
    if r.returncode == 0:
        parts = r.stdout.strip().split(", ")
        return f"GPU: {parts[0]}, {parts[1]}°C, {parts[2]}% util, VRAM: {parts[3]}/{parts[4]} MB"
    return "GPU: error querying"

def handle_system_status():
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3)
    gpu_line = gpu.stdout.strip() if gpu.returncode == 0 else "N/A"
    mem_line = mem.stdout.split("\n")[1] if mem.returncode == 0 else "N/A"
    return f"GPU: {gpu_line}. Memory: {mem_line}"

def handle_memory_status():
    r = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3)
    if r.returncode == 0:
        lines = r.stdout.split("\n")
        return f"Memory: {lines[1]}"
    return "Memory: error"

def handle_list_services():
    r = subprocess.run(["systemctl", "--user", "--no-pager", "list-units", "--type=service", "--state=running"],
                       capture_output=True, text=True, timeout=5)
    lines = [l for l in r.stdout.split("\n") if "nx-" in l or "jarvis" in l or "pipewire" in l]
    return "Services: " + ", ".join(l.split()[0] for l in lines[:8]) if lines else "No services found."

def handle_agent_status():
    """Query the compiled hephaestus-agent binary via MCP."""
    import json, subprocess as sp
    p = sp.Popen(["/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bins/hephaestus-agent"],
                 stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.DEVNULL, text=True)
    p.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
    p.stdin.flush(); p.stdout.readline()
    p.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_context"}}\n')
    p.stdin.flush()
    resp = json.loads(p.stdout.readline())
    ctx = json.loads(resp["result"]["content"][0]["text"])
    p.kill()
    return f"Compiled agent: {ctx.get('agent', '?')}, {ctx.get('patterns_loaded', 0)} patterns, {ctx.get('success_rate', 0)}% success rate."

def handle_agent_identity():
    return "I am Jarvis, your N-Xyme personal assistant. I route commands through a compiled Mojo agent and query memory vectors."

def handle_search_memory(query: str):
    """Search the 11K memory vectors."""
    import json
    from services.memory_pipeline.memory_watcher import EmbedEngine  # or use your existing embed
    # Fallback: grep the vector store
    import subprocess as sp
    r = sp.run(["grep", "-rl", query, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/vectors/"],
               capture_output=True, text=True, timeout=10)
    files = r.stdout.strip().split("\n") if r.stdout.strip() else []
    return f"Found {len(files)} matching entries." if files else "No matches found."

def handle_help():
    cmds = [c[2] for c in COMMANDS]
    return "Available commands: " + "; ".join(cmds)

def handle_full_status():
    gpu = handle_gpu_status()
    mem = handle_memory_status()
    agent = handle_agent_status()
    return f"{gpu}. {mem}. {agent}"

def route_command(text: str) -> str | None:
    """Tier 1: Regex command routing."""
    text_lower = text.lower().strip()
    for pattern, handler_name, _ in COMMANDS:
        match = re.search(pattern, text_lower)
        if match:
            handler = globals()[handler_name]
            if handler_name == "handle_search_memory":
                return handler(match.group(1))
            return handler()
    return None  # Fall through to LLM
```

**Insert into `query_agent()` at line 209:**
```python
def query_agent(text: str) -> str:
    # ...existing session logging...
    
    # NEW: Route through voice command system
    result = route_command(text)
    if result:
        response = result
    else:
        response = query_llama(text)  # existing fallback
    
    # ...existing response logging...
    return response
```

#### 1.2 Fix FIFO race condition
```bash
# Check if jarvis-pc also reads the FIFO:
grep -r "jarvis_fifo" /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/ --include="*.py" --include="*.sh" 2>/dev/null
```
If found, remove the FIFO reader from that file. Only jarvis_bridge.py should read the FIFO.

### Phase 2 — Dashboard Panel (30 min)

#### 2.1 Add compiled agent panel to dashboard

**Integration point:** `services/dashboard/dashboard.py` — already has backend functions added at lines 286-316. Wire the panel.

**Lines to add** (right column layout, after autostart):
```python
# At line 155 area, add:
def get_compiled_agent_status() -> dict:
    try:
        import subprocess, json
        p = subprocess.Popen(
            ["/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bins/hephaestus-agent"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        p.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
        p.stdin.flush(); p.stdout.readline()
        p.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_context"}}\n')
        p.stdin.flush()
        resp = json.loads(p.stdout.readline())
        ctx = json.loads(resp["result"]["content"][0]["text"])
        p.kill()
        return {"agent": ctx.get("agent","?"), "patterns": ctx.get("patterns_loaded",0),
                "success_rate": ctx.get("success_rate",0), "status": "running"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:40]}

# In right column layout (line ~460), add:
Layout(name="agent", size=5),

# In the panel population section (line ~490), add:
agent = get_compiled_agent_status()
if agent.get("status") == "running":
    agent_text = (f"[green]● {agent['agent']}[/]\n"
                  f"  Patterns: {agent['patterns']}\n"
                  f"  Success: {agent['success_rate']}%")
else:
    agent_text = f"[red]✗ {agent.get('error', 'offline')}[/]"
right["agent"].update(Panel(agent_text, title="Compiled Agent", border_style="cyan"))
```

### Phase 3 — Tray Integration (20 min)

#### 3.1 Add compiled agent status to tray tooltip

**Integration point:** `nx_dictate/ui/tray.py` — find the tooltip setter (search for `setToolTip` in the file) and add:

```python
# In the _do_update_state or wherever tooltip is set:
try:
    import subprocess, json
    p = subprocess.Popen(
        ["/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bins/hephaestus-agent"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    p.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
    p.stdin.flush(); p.stdout.readline()
    p.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_context"}}\n')
    p.stdin.flush()
    resp = json.loads(p.stdout.readline())
    ctx = json.loads(resp["result"]["content"][0]["text"])
    p.kill()
    agent_info = f"Agent: {ctx.get('agent','?')} ({ctx.get('patterns_loaded',0)} patterns)"
except:
    agent_info = "Agent: offline"

# Append to existing tooltip
tooltip += f"\n{agent_info}"
```

### Phase 4 — Test (20 min)

#### 4.1 Round-trip test
```bash
# Simulate voice commands:
echo "GPU status" > /tmp/jarvis_fifo
sleep 3
journalctl --user -u jarvis-bridge --no-pager -n 5

echo "system status" > /tmp/jarvis_fifo
sleep 3
journalctl --user -u jarvis-bridge --no-pager -n 5

echo "restart dictation" > /tmp/jarvis_fifo
sleep 5
systemctl --user is-active nx-dictate

echo "compiled agent status" > /tmp/jarvis_fifo
sleep 3
journalctl --user -u jarvis-bridge --no-pager -n 5
```

---

## 4. Full Scope (Future — 11.5h after MVP validation)

When ready, add:
| Phase | What | Time | When |
|-------|------|------|------|
| **1** | `.wf.md` format + parser | 2.5h | After MVP confirmed working |
| **2** | ONNX semantic routing (Tier 2) | 2.5h | When regex needs extension |
| **3** | Confirmation gate | 3h | When destructive commands added |
| **4** | Doc discovery | 2h | When auto-generating workflows from docs |
| **5** | Full integration | 1.5h | Polish + edge cases |

---

## 5. File Reference Index

### Core Files
| File | Role | Lines | Status |
|------|------|-------|--------|
| `services/jarvis/jarvis_bridge.py` | Main voice pipeline — FIFO → LLM → TTS | 334 | 🔧 MODIFY |
| `services/jarvis/jarvis-pc` | PC commands (regrex-based) | ~138 | May need FIFO fix |
| `services/dashboard/dashboard.py` | TUI system monitor | 557 | 🔧 ADD panel |
| `nx_dictate/ui/tray.py` | System tray app | 1107 | 🔧 ADD tooltip |
| `nx_dictate/__main__.py` | Dictation entry point | ~420 | Reference only |

### Compiled Binaries
| File | Role | Size |
|------|------|------|
| `bins/hephaestus-agent` | Compiled Mojo MCP server | 296K ELF |
| `bins/mojo-daemon` | Mojo daemon (old 0.26) | 340K (bricked) |
| `bins/mojo-engine` | Mojo engine (old 0.26) | 104K (bricked) |

### Memory & Models
| File | Role | Size |
|------|------|------|
| `data/memory/vectors/` | 11,251 vectors across 10 agents | 133MB |
| `data/memory/models/embedding.onnx` | MiniLM ONNX, pooled 384-dim | ~90MB |
| `data/memory/index.json` | Vector index | ~10K |

### Config Files
| File | Role | Note |
|------|------|------|
| `opencode.json` | MCP config — has hephaestus-agent | Has entry at lines 61-68 |
| `config/nx_agents.json` | Agent config — MISSING hephaestus-agent | 🔴 DRIFT |
| `.config/systemd/user/nx-dictate.service` | Dictation service | Uses `/home/nxyme/N-Xyme_CODE/venv/bin/python3` |
| `.config/systemd/user/jarvis-bridge.service` | Jarvis bridge service | Uses system Python |
| `.config/nx_dictate/config.yaml` | Dictation config | C920, 32000Hz, CUDA |

### Build Scripts
| File | Role |
|------|------|
| `scripts/compile-feedback.sh` | Mojo compile wrapper with structured output |
| `scripts/compile-pattern-memory.py` | Pattern memory storage + search |
| `scripts/build-agent.sh` | Per-agent Mojo binary compiler |
| `scripts/ingest-memory.py` | GPU batch embedding of sessions |

---

## 6. Integration Architecture (Final State)

```
┌──────────────────────────────────────────────────────────┐
│                   USER SPEAKS                             │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│    Whisper large-v3 (CTranslate2 GPU)                     │
│    nx_dictate → /tmp/jarvis_fifo (SINGLE WRITER)          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│    jarvis_bridge.py (SINGLE READER)                       │
│                                                           │
│    text → route_command(text) → match? → execute handler  │
│                                  ↓ no match               │
│                            query_llama(text) ← LLM fallback│
│                                                           │
│    Output: speak() + notify-send                          │
└────────────────────┬─────────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     Piper TTS   notify-send   /tmp/workflow-last-result.txt
     (neural)     (desktop)          │
                                     ▼
                              Dashboard (TUI)
                              + Tray Tooltip
```

---

## 7. Handoff Notes for Next Agent

### What was built today (May 18):
1. **Mojo 1.0 migration** — 13/23 files compile clean (fn→def, PythonObject fix, etc.)
2. **Compile-feedback loop** — `compile-feedback.sh` + `compile-pattern-memory.py` + Ralph Loop injection
3. **Compiled agent binary** — `bins/hephaestus-agent` (Mojo 1.0 ELF, MCP protocol, reads pattern memory)
4. **Dictation tray** — Rebuilt by Hephaestus (1107 lines, ADHD-friendly, audio meter, GPU stats, model switch)
5. **Memory ingestion** — 11,251 GPU-embedded vectors (MiniLM 384-dim, ONNX)
6. **Dashboard additions** — Compiled agent + MCP + memory backend functions added (not yet wired)

### Still broken:
- `gpu_memory.mojo` + `gpu_kernels.mojo` — need `std.gpu` migration (Mojo 1.0 breaking change)
- 10/23 .mojo files don't compile (multi-file package issue)
- `bins/mojo-engine` + `bins/mojo-daemon` — bricked by 0.26→1.0 symbol mismatch
- `services/nx-agents-mcp/` — 9 Rust compile errors

### The Golden Rule:
**Always use `/home/nxyme/N-Xyme_CODE/venv/bin/python3`** for running anything. The system Python might not have the required packages. The main venv has torch CUDA + sentence-transformers + PyQt6.

### READ THIS FIRST:
```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source /home/nxyme/N-Xyme_CODE/venv/bin/activate  # activate the right venv
```
