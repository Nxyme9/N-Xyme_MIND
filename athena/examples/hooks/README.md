# Hooks

Deterministic scripts that run **outside** the agentic loop on specific events. Zero LLM overhead, guaranteed execution.

Inspired by [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) hooks pattern.

## Available Hooks

| Hook | Event | What It Does |
|:-----|:------|:-------------|
| `pre_compact.py` | Before context compaction | Auto-quicksaves session knowledge before the context window is compacted, preventing knowledge loss |

## How Hooks Differ from Workflows

| | Workflows | Hooks |
|:--|:---------|:------|
| **Execution** | Inside the agentic loop (LLM processes) | Outside (deterministic script) |
| **Overhead** | Consumes tokens | Zero token cost |
| **Guarantee** | Best-effort (LLM may skip) | Guaranteed execution |
| **Use case** | Complex multi-step reasoning | Simple, critical automation |

## Creating Your Own Hooks

1. Create a Python script in `.agent/hooks/`
2. The script should be self-contained and fast (< 10s execution)
3. Hook into your workflow scripts to call them at the right time

### Hook Events (Conceptual)

| Event | When |
|:------|:-----|
| `PreCompact` | Before context window compaction |
| `SessionStart` | At `/start` boot |
| `SessionEnd` | At `/end` shutdown |
| `PreCommit` | Before git commit |
| `PostCommit` | After git commit |
