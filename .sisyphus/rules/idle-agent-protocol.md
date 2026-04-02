# Rule 18: Idle Agent Protocol (Zero Tokens)

## The Rule

All agents IDLE (zero tokens) until work appears. Heartbeat monitors and wakes them.

## Architecture

```
HEARTBEAT (always running, local LLM, ~$0)
├─ Every 5 min: check global TODOs
├─ If TODOs: wake appropriate agent
├─ If P0: wake ALL agents immediately
└─ Never stops the chain

ALL AGENTS (idle, zero tokens)
├─ Hephaestus: idle until voice command
├─ Prometheus: idle until Hephaestus delegates
├─ Atlas: idle until Prometheus delegates
├─ Workers: idle until Atlas delegates
└─ All return to idle when done
```

## Agent States

| State | Tokens | When |
|-------|--------|------|
| **IDLE** | 0 | Default. No work. |
| **WAKING** | 0→active | Heartbeat or user wakes it |
| **WORKING** | active | Executing task |
| **DONE** | active→0 | Task complete. Return to idle. |

## Wake Triggers

| Trigger | Agent | Action |
|---------|-------|--------|
| Voice command | Hephaestus | Wake, delegate |
| TODO exists | Prometheus/Atlas | Wake, execute |
| P0 emergency | ALL | Wake immediately |
| Task complete | Worker | Return to idle |

## The Chain (Domino)

```
You speak → Hephaestus wakes
    ↓
Hephaestus delegates → Prometheus wakes
    ↓
Prometheus plans → Atlas wakes
    ↓
Atlas executes → Workers wake
    ↓
Workers complete → All return to idle
```

## Heartbeat (Always Running)

- Uses local LLM (llama3.2:3b, 1.9GB VRAM)
- Checks every 5 minutes
- Wakes agents when work exists
- Never stops the chain
- ~$0 cost

## The Rule

> **All agents idle (zero tokens) until work. Heartbeat monitors (local LLM, ~$0). Wake on TODO or voice. Domino chain: Hephaestus→Prometheus→Atlas→Workers. All return to idle when done.**
