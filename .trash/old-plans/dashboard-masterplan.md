# N-Xyme MIND Dashboard Masterplan

## Problem Statement
Dashboard has redundant screens, missing UI for critical configs, slow loading, and confusing UX. Users can't edit opencode.json, VPN backends, signals, or routing weights through the TUI.

## Current State (Broken)
- **SettingsScreen**: Edits learning-config.json (23 keys) — works but slow
- **ConfigScreen**: Read-only display of learning-config.json — DUPLICATE
- **ConfigEditorScreen**: Also edits learning-config.json — DUPLICATE
- **Admin panel**: Command input with `set key=value` — limited
- **opencode.json**: NO UI (agents, MCPs, permissions)
- **VPN backends**: NO UI (8 SOCKS5 proxies)
- **Signals config**: NO UI (signal weights)
- **Routing weights/triggers**: NO UI

## Target State

### 1. Unified Settings Screen (X key)
**Single entry point for ALL system configuration.**

| Panel | Source File | Edit Type |
|-------|-------------|-----------|
| Learning | `src/.sisyphus/learning-config.json` | Toggles + Inputs |
| Agents | `opencode.json` → `agent` section | DataTable + Edit |
| MCPs | `opencode.json` → `mcp` section | DataTable + Edit |
| VPN | `configs/vpn/backends.json` | DataTable + Add/Remove |
| Signals | `src/learning/signals_config.json` | Weights editor |
| Routing | `.sisyphus/routing-weights.json` | Weight sliders |
| Ollama | `configs/ollama.json` | Concurrency input |
| Stats | Live system stats | Read-only |
| Controls | Live system status | Read-only |

### 2. Admin Panel (Tab 7) — Central Control Hub
**Not just display — actual control center.**

- System status overview (all 43 data sources)
- Quick actions: restart daemon, flush cache, reset learning, rebuild index
- Direct file editor for any config file
- Memory manager (add/edit/delete/search)
- Rules editor (view/edit global rules)
- Pattern viewer (learned patterns)
- Command history
- Performance metrics

### 3. Remove Redundant Screens
- **Delete ConfigScreen** — read-only duplicate of learning config
- **Merge ConfigEditorScreen** into SettingsScreen (Agents/MCPs panels)
- **Keep**: SearchScreen, LogsScreen, HealScreen, PatternViewerScreen, MemoryManagerScreen, RulesEditorScreen

### 4. Performance Fixes
- SettingsScreen loads instantly (lazy-load panels on first view)
- All data fetched in background thread
- Cache config reads (5s TTL)
- Only write to disk on explicit save

### 5. New Functionality
- **VPN Panel**: Add/remove SOCKS5 proxies, test connectivity, view health
- **Signals Panel**: Adjust signal weights (misalignment, stagnation, failure, loop, exhaustion, satisfaction)
- **Routing Panel**: View/adjust routing weights per agent
- **Agent Panel**: Change models, edit permissions, view performance
- **MCP Panel**: Add/remove MCP servers, test connections

## Implementation Phases

### Phase 1: Clean Up (30 min)
1. Delete ConfigScreen class
2. Merge ConfigEditorScreen functionality into SettingsScreen
3. Fix SettingsScreen performance (lazy-load panels)
4. Verify dashboard launches instantly

### Phase 2: Add Missing Panels (1 hour)
1. Agents panel — read/edit opencode.json agent section
2. MCPs panel — read/edit opencode.json mcp section
3. VPN panel — read/edit configs/vpn/backends.json
4. Signals panel — read/edit src/learning/signals_config.json
5. Routing panel — read/edit .sisyphus/routing-weights.json

### Phase 3: Admin Panel Overhaul (45 min)
1. Quick actions (restart, flush, reset, rebuild)
2. Direct file editor for any config
3. Command history
4. Performance metrics display

### Phase 4: Polish (30 min)
1. Consistent styling across all panels
2. Save/Cancel workflow for all edits
3. Validation before saving
4. Error handling and user feedback

## Files to Modify
- `src/tui/ultimate_dashboard.py` — Remove ConfigScreen, enhance Admin panel
- `src/tui/settings_screen.py` — Add 5 new panels, lazy-load, merge ConfigEditorScreen

## Files to Create
- None (all config files already exist)

## Success Criteria
- Dashboard launches in <1s
- Settings screen opens in <0.5s
- All 12 config files editable through UI
- Zero redundant screens
- Admin panel shows all 43 data sources + quick actions
- All edits validated before saving
- No crashes on any panel
