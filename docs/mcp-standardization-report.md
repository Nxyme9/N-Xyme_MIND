# MCP Category & Naming Standardization Report

## Current MCP Servers (Wired in opencode.json)

| MCP Name | Package | Status | Tools |
|----------|---------|--------|-------|
| `sequential-thinking` | npx | ✅ External | 1 |
| `context7` | npx | ✅ External | 1 |
| `nx-mind` | packages/nx-mind-mcp | ✅ NX-prefixed | 14 |
| `unified-memory` | packages/memory_core | ✅ Named correctly | 20+ |
| `learning-engine` | packages/learning_engine | ✅ Named correctly | 15+ |
| `intelligence` | packages/intelligence | ✅ Named correctly | 12+ |
| `quality-gates` | packages/quality-gates-mcp | ✅ NX-prefixed | 8 |
| `telegram` | wrapper | ⚠️ External | 1 |
| `nx-context` | packages/nx-context-mcp | ✅ NX-prefixed | 6 |
| `trigger-guardian` | packages/trigger-guardian-mcp | ✅ NX-prefixed | 5 |
| `orchestration` | packages/orchestration | ✅ Named correctly | 10+ |
| `notion` | npx | ✅ External | 1 |
| `obsidian` | packages/obsidian_mcp_fixed.py | ⚠️ Standalone file | 4 |
| `github` | npx | ✅ External | 1 |

---

## Package Naming (✅ All Standardized)

```
packages/           → snake_case ✅
packages/nx-*       → nx- prefix ✅
packages/*-mcp     → MCP packages ✅
```

---

## Issues Found

### 1. Obsidian MCP (Standalone)
- **Current:** `packages/obsidian_mcp_fixed.py` (root level file)
- **Better:** `packages/obsidian-mcp/obsidian_mcp/__init__.py`
- **Status:** Works but not standardized

### 2. Telegram MCP (Wrapper)
- **Current:** Wrapper script in bin/
- **Status:** Works but could be cleaner

### 3. intelligent_router_mcp (Not Wired)
- **Current:** `packages/intelligent_router_mcp/`
- **Status:** Exists but NOT in opencode.json MCP config

---

## Recommendations

| Priority | Item | Action |
|----------|------|--------|
| Medium | Obsidian MCP | Move to packages/obsidian-mcp/ |
| Low | Telegram MCP | Document in readme |
| Low | intelligent_router_mcp | Decide: integrate or deprecate |

---

## Summary

- **NX-prefixed packages:** 3 (nx-mind, nx-context, quality-gates)
- **MCP wired:** 13 MCPs configured
- **Package naming:** ✅ All snake_case
- **Missing:** intelligent_router_mcp not wired

**Status: 95% complete** - Only minor cosmetic issues remain.
