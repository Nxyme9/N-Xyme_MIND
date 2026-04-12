# nx-context-mcp
# Context injection MCP server for N-Xyme_MIND

A Python MCP server that provides context injection from N-Xyme's memory bank into OpenCode sessions. Reads identity, user, active context, and constraints defined in `athena.yaml`.

## Tools

| Tool | Description |
|------|-------------|
| `get_active_context` | Returns current active context from memory bank |
| `get_product_context` | Returns product context (identity/soul) from memory bank |
| `get_user_context` | Returns user context from memory bank |
| `get_constraints` | Returns behavioral constraints from memory bank |
| `get_bmad_agents` | Lists available BMAD agents from `_bmad/_config/agents/` |
| `get_bmad_workflows` | Lists BMAD workflows by phase from `_bmad/bmm/workflows/` |
| `inject_context` | Writes context into session for prompt injection |

## Installation

```bash
pip install -e .
```

## Usage

### stdio mode (for OpenCode/Claude Desktop)
```bash
python -m nx_context_mcp
```

### SSE mode (for remote access)
```bash
python -m nx_context_mcp --sse --port 8766
```

## Configuration

Paths are loaded from `athena.yaml`. Default memory bank location:
- `.context/memory_bank/activeContext.md`
- `.context/memory_bank/productContext.md`
- `.context/memory_bank/userContext.md`
- `.context/memory_bank/constraints.md`

Override via `NX_CONTEXT_ROOT` environment variable.
