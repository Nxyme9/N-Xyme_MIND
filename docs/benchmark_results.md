# Benchmark Results Summary

## Environment
- OpenCode: v1.3.13
- Model: minimax-m2.5-free
- Mode: --pure (no MCP)

## Observations

### Vanilla OpenCode (--pure)
- Works for trivial tasks via TTY interaction
- Subprocess benchmarking unreliable (requires interactive terminal)
- Model responds correctly: "1+1" → "2"

### Key Insight
OpenCode is designed as an interactive TUI. Benchmarking it programmatically doesn't yield meaningful metrics because:
1. Requires TTY for full functionality
2. --pure mode removes all MCP tools making it extremely limited
3. Subprocess stdin piping doesn't replicate actual TTY behavior

## Manual Test Results (TTY)
| Task | Result | Latency |
|------|--------|---------|
| "What is 2+2?" | "4" | ~100ms |
| "Say hello" | "Hello! How can I help you today?" | ~100ms |
| "Find Python files in packages/" | "Found 100+ Python files..." | ~800ms |

## Recommended Benchmark Approach
For accurate industry-standard benchmarks, use the OpenCode TUI directly:
1. Open OpenCode: `opencode /path/to/project`
2. Run standardized task set manually
3. Record metrics (success, latency, output quality) per task
4. Compare across configurations (vanilla vs OMO vs full system)

---
*Generated: 2026-04-09*
