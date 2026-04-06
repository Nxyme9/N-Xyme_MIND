# N-Xyme MIND Dashboard v2.0 — Enhancement Master Plan

> **Status**: Phase 1-5 Complete | **Next**: Phase 6 Enhancements  
> **Generated**: 2026-04-06 | **Owner**: Sisyphus

---

## Executive Summary

Dashboard v2.0 is now functional with 17 tabs, 65+ buttons, and real interactivity. This master plan outlines Phase 6 refinements to transform the dashboard from "functional" to "production-grade."

---

## Phase 6: Production Enhancements

### 6.1 Real-Time Data Integration (Priority: HIGH)

**Objective**: Connect all buttons to real system data

| Task | Description | Effort |
|------|-------------|--------|
| T6.1.1 | Wire daemon start/stop to actual `src.memory.daemon` module | Medium |
| T6.1.2 | Connect agent status to real agent health data | Medium |
| T6.1.3 | Wire memory stats to actual memory graph | Medium |
| T6.1.4 | Connect proxy controls to `rotator.py` | Medium |
| T6.1.5 | Implement config editor with actual file read/write | High |

**Files to modify**:
- `src/ui/tui/ultimate_dashboard.py` - Wire action handlers
- `src/dashboard/data_provider.py` - Add missing data sources

### 6.2 Enhanced Visualization (Priority: HIGH)

**Objective**: Add rich visualizations beyond ASCII text

| Task | Description | Effort |
|------|-------------|--------|
| T6.2.1 | Add Sparkline graphs to Overview tab metrics | Medium |
| T6.2.2 | Implement ProgressBar for task completion | Low |
| T6.2.3 | Add DataTable for agent/performance listing | Medium |
| T6.2.4 | Create real-time charts for cost tracking | High |
| T6.2.5 | Add Tree visualization for knowledge graph | High |

**Files to create**:
- `src/ui/tui/widgets/charts.py` - Chart components
- `src/ui/tui/widgets/tables.py` - Data table components

### 6.3 Modal Dialogs (Priority: MEDIUM)

**Objective**: Add interactive dialogs for complex operations

| Task | Description | Effort |
|------|-------------|--------|
| T6.3.1 | Config Editor Modal (ace/editor integration) | High |
| T6.3.2 | Agent Creator Dialog | Medium |
| T6.3.3 | Trigger Editor Modal | Medium |
| T6.3.4 | Benchmark Results Viewer | Medium |
| T6.3.5 | Settings Preferences Panel | Medium |

**Files to create**:
- `src/ui/tui/dialogs/config_editor.py`
- `src/ui/tui/dialogs/agent_creator.py`
- `src/ui/tui/dialogs/trigger_editor.py`

### 6.4 Persistence & State (Priority: HIGH)

**Objective**: Save and restore dashboard state

| Task | Description | Effort |
|------|-------------|--------|
| T6.4.1 | Save/restore last active tab | Low |
| T6.4.2 | Persist user preferences (dark mode, etc.) | Medium |
| T6.4.3 | Remember scroll positions per tab | Low |
| T6.4.4 | Save custom button configurations | Medium |
| T6.4.5 | Export/import dashboard config | Medium |

**Files to modify**:
- Create `src/ui/tui/dashboard_state.py`

### 6.5 Advanced Features (Priority: MEDIUM)

**Objective**: Add enterprise-grade features

| Task | Description | Effort |
|------|-------------|--------|
| T6.5.1 | Multi-select for batch operations | Medium |
| T6.5.2 | Keyboard macros / custom shortcuts | High |
| T6.5.3 | Plugin system for custom widgets | High |
| T6.5.4 | Webhook integration for alerts | High |
| T6.5.5 | Scheduled tasks / cron within dashboard | High |

### 6.6 Search & Filter (Priority: MEDIUM)

**Objective**: Add powerful search capabilities

| Task | Description | Effort |
|------|-------------|--------|
| T6.6.1 | Global search across all tabs (Ctrl+F) | Medium |
| T6.6.2 | Filter agents by status | Low |
| T6.6.3 | Filter memory by source/type | Low |
| T6.6.4 | Search logs and events | Medium |
| T6.6.5 | Regex search in config files | Medium |

### 6.7 Logging & Debugging (Priority: MEDIUM)

**Objective**: Better observability

| Task | Description | Effort |
|------|-------------|--------|
| T6.7.1 | Activity log panel | Medium |
| T6.7.2 | Error history viewer | Low |
| T6.7.3 | Performance metrics dashboard | High |
| T6.7.4 | Debug mode toggle | Low |
| T6.7.5 | Export diagnostic bundle | Medium |

---

## Implementation Roadmap

### Phase 6.1 (Week 1-2): Data Wiring
```
T6.1.1 → T6.1.2 → T6.1.3 → T6.1.4 → T6.1.5
```

### Phase 6.2 (Week 2-3): Visualization
```
T6.2.1 → T6.2.2 → T6.2.3 → T6.2.4 → T6.2.5
```

### Phase 6.3 (Week 3-4): Dialogs
```
T6.3.1 ↔ T6.3.2 ↔ T6.3.3 ↔ T6.3.4 ↔ T6.3.5
```

### Phase 6.4-6.7 (Week 4-6): Advanced
```
Parallel: T6.4 + T6.5 + T6.6 + T6.7
```

---

## Technical Debt (Fix Now)

| Issue | Location | Fix |
|-------|----------|-----|
| LSP errors lines 356, 363 | `ultimate_dashboard.py` | Fix dict access pattern |
| Missing `Switch` in imports | Line 20-36 | Already imported |
| Unused `_action_*` stubs | End of file | Implement or remove |

---

## Success Metrics

- [ ] All buttons trigger real actions (no stub functions)
- [ ] Data refreshes automatically every 10s
- [ ] Settings persist across sessions
- [ ] Search returns results in <1s
- [ ] No LSP errors in dashboard code

---

## Files Reference

### Existing (Don't Break)
```
src/ui/tui/
├── ultimate_dashboard.py       # 2526 lines - MAIN
├── widgets/
│   ├── __init__.py             # Exports
│   ├── kg_viewer.py            # Knowledge graph
│   ├── routing_funnel.py       # Routing viz
│   ├── cost_dashboard.py      # Cost tracking
│   ├── activity_feed.py       # Live events
│   └── enhancements.py        # Theme/performance
└── screens/
    ├── help_screen.py
    └── command_palette.py
```

### To Create
```
src/ui/tui/
├── dialogs/                    # NEW
│   ├── __init__.py
│   ├── config_editor.py
│   ├── agent_creator.py
│   └── trigger_editor.py
├── widgets/
│   ├── charts.py               # NEW - Sparklines, charts
│   └── tables.py              # NEW - DataTables
└── dashboard_state.py         # NEW - Persistence
```

---

## Next Steps

1. **Approve this plan** → Proceed with Phase 6.1
2. **Pick priority** → Start with T6.1.1 (daemon wiring)
3. **Assign tasks** → Delegate to Hephaestus

---

*Master Plan v1.0 | N-Xyme MIND Dashboard v2.0*