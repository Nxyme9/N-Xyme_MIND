# N-Xyme MIND Dashboard - Master Plan v2.0
## Cutting-Edge TUI Frontend Implementation

**Created**: 2026-04-06  
**Version**: 2.0 (Cutting-Edge)  
**Status**: REVISED based on Metis/Momus review

---

## REVISION NOTES (2026-04-06)

Based on Metis and Momus review:

1. **ERROR HANDLING MOVED TO PHASE 1** - T5.3 → T1.1 (production blocker)
2. **SESSION REPLAY REMOVED** - T3.4 dropped (scope creep)
3. **TIMELINE EXTENDED** - 5 weeks → 8 weeks for feasibility
4. **BACKWARD COMPATIBILITY ADDED** - DataProvider will wrap existing get_system_stats()
5. **ASYNC LOCKING STRATEGY** - Added to prevent race conditions
6. **PHASE 4-5 DEFERRED** - To v2.1, focus on Phase 1-3

---

## Vision Statement

Transform the N-Xyme MIND dashboard from a **data display** into an **interactive command center** with real-time visualizations, predictive analytics, and action-oriented panels using 2025-2026 best practices.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         N-Xyme MIND Dashboard v2.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  COMMAND PALETTE (Cmd+K) - Primary Navigation & Actions             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┐  │
│  │ Overview│ Agents  │ Memory  │Intelligence│ Routing │ Health  │ Skills │  │
│  ├─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┤  │
│  │                                                                       │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────┐  │  │
│  │  │   PRIMARY PANEL     │  │   SECONDARY PANEL   │  │   SIDEBAR    │  │  │
│  │  │   (Sparklines/Data) │  │   (Details/Tables)  │  │   (Actions) │  │  │
│  │  └─────────────────────┘  └─────────────────────┘  └──────────────┘  │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │              ACTIVITY FEED / LOGS (Real-time)                   │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  STATUS BAR: [Tab] Navigate | [?] Help | [Cmd+K] Command | [Q] Quit │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation & Quick Wins (Week 1)

### 1.1 Unified Data Layer

**Objective**: Eliminate scattered subprocess calls, implement caching + error handling

| Task | File | Description |
|------|------|-------------|
| `T1.1.1` | `src/dashboard/data_provider.py` (NEW) | Create DataProvider class with sync fetchers (no async - too risky) |
| `T1.1.2` | `src/dashboard/data_provider.py` | Implement TTL cache (30s default, thread-safe) |
| `T1.1.3` | `src/dashboard/data_provider.py` | Add error handling - fallback values for ALL data sources |
| `T1.1.4` | `src/dashboard/data_provider.py` | Add PID lock to prevent duplicate dashboard |
| `T1.1.5` | `src/ui/tui/ultimate_dashboard.py` | Wrap get_system_stats() with DataProvider (backward compat) |

**Data Sources to Include**:
```python
class DataProvider:
    async def get_daemon_status() -> dict:       # pgrep check
    async def get_ollama_status() -> dict:        # HTTP check
    async def get_memory_stats() -> dict:         # mcp_server
    async def get_indexed_count() -> dict:         # drive_embedder
    async def get_router_status() -> dict:        # memory_router
    async def get_orchestration_status() -> dict: # agent_card_registry
    async def get_learning_stats() -> dict:        # priority_engine
    async def get_all() -> dict:                  # Batch fetch all
```

### 1.2 Reactive Architecture Migration

**Objective**: Replace manual refresh with Textual's reactive system

| Task | File | Description |
|------|------|-------------|
| `T1.2.1` | `src/ui/tui/ultimate_dashboard.py` | Add `@reactive` attributes for live data |
| `T1.2.2` | `src/ui/tui/ultimate_dashboard.py` | Implement `watch_*` methods for auto-refresh |
| `T1.2.3` | `src/ui/tui/ultimate_dashboard.py` | Remove manual `_apply_refresh()` calls |

**Pattern**:
```python
class NxymeDashboard(App):
    # Replace: live_data = {}
    # With:
    daemon_status = reactive({"running": False, "pid": "N/A"})
    ollama_status = reactive({"running": False})
    memory_stats = reactive({"sources": 0, "enabled": 0})
    indexed_stats = reactive({"files": 0, "chunks": 0})
    learning_stats = reactive({"feedback": 0, "queries": 0})
    
    def watch_daemon_status(self, status: dict) -> None:
        """Auto-triggered when daemon_status changes"""
        self.refresh_content()
```

### 1.3 Data Freshness Indicators

**Objective**: Visual indicators showing data age

| Task | File | Description |
|------|------|-------------|
| `T1.3.1` | `src/ui/tui/ultimate_dashboard.py` | Add `last_updated` timestamp to each metric |
| `T1.3.2` | `src/ui/tui/ultimate_dashboard.py` | Color-coded freshness: 🟢 <10s, 🟡 <30s, 🔴 >30s |
| `T1.3.3` | `src/ui/tui/ultimate_dashboard.py` | Display in status bar |

### 1.4 Help Overlay (? key)

**Objective**: Keyboard shortcuts reference

| Task | File | Description |
|------|------|-------------|
| `T1.4.1` | `src/ui/tui/ultimate_dashboard.py` | Create HelpScreen modal |
| `T1.4.2` | `src/ui/tui/ultimate_dashboard.py` | Bind `?` key to show help |
| `T1.4.3` | `src/ui/tui/ultimate_dashboard.py` | Group shortcuts by category |

**Help Content**:
```
┌────────────────────────────────────────────┐
│  KEYBOARD SHORTCUTS                        │
├────────────────────────────────────────────┤
│  NAVIGATION                                │
│  1-9,0    Switch panels                    │
│  [,]       Cycle panels                    │
│  TAB       Next panel                      │
│                                            │
│  ACTIONS                                   │
│  R         Refresh data                    │
│  D         Toggle dark mode                │
│  E         Export dashboard                │
│  S         Search                          │
│  X         Settings                        │
│                                            │
│  SPECIAL                                  │
│  ?         This help                       │
│  Cmd+K    Command palette                  │
│  Q         Quit                            │
└────────────────────────────────────────────┘
```

---

## Phase 2: Core Visualizations (Week 2)

### 2.1 Sparkline Implementation

**Objective**: Add trend charts for metrics over time

| Task | File | Description |
|------|------|-------------|
| `T2.1.1` | `src/ui/tui/widgets/sparkline_widget.py` (NEW) | Create SparklineWidget class |
| `T2.1.2` | `src/ui/tui/ultimate_dashboard.py` | Add sparklines to Overview panel |
| `T2.1.3` | `src/ui/tui/ultimate_dashboard.py` | Track history (last 100 samples) |

**Metrics to Track**:
- Indexed files trend (hourly)
- Memory sources trend
- Learning feedback events trend
- Agent task throughput

**Pattern**:
```python
class MetricSparkline(Static):
    """Real-time sparkline for dashboard metrics."""
    
    data = reactive([])
    max_points = 100
    
    def compose(self) -> ComposeResult:
        yield Sparkline(
            self.data,
            max_color="$success",
            min_color="$error",
            gradient=( "$error", "$warning", "$success" )
        )
    
    def add_sample(self, value: float) -> None:
        self.data = [*self.data, value][-self.max_points:]
```

### 2.2 Agent Activity Heatmap

**Objective**: Visualize agent activity patterns

| Task | File | Description |
|------|------|-------------|
| `T2.2.1` | `src/ui/tui/widgets/activity_heatmap.py` (NEW) | Create HeatmapWidget |
| `T2.2.2` | `src/dashboard/panels/agents.py` | Integrate heatmap into Agents panel |
| `T2.2.3` | `src/dashboard/panels/agents.py` | Show 24h activity by hour |

**Display**:
```
AGENT ACTIVITY (24h)
        00 03 06 09 12 15 18 21
Sisyphus  ░░░▓▓▓▓▓░░░░░░░░░
Hephaestus░░░░░░░▓▓▓▓▓▓▓░░░
Oracle   ░░▓▓▓▓▓░░░░░▓▓▓▓▓░
```

### 2.3 Tabbed Navigation

**Objective**: Replace button-based panel switching with TabbedContent

| Task | File | Description |
|------|------|-------------|
| `T2.3.1` | `src/ui/tui/ultimate_dashboard.py` | Migrate to Textual TabbedContent |
| `T2.3.2` | `src/ui/tui/ultimate_dashboard.py` | Preserve keyboard shortcuts |
| `T2.3.3` | `src/ui/tui/ultimate_dashboard.py` | Add tab icons |

**Tabs**:
```
[🚀 Overview] [🤖 Agents] [💾 Memory] [🧠 Intelligence] [🔀 Routing] [❤️ Health] [⚡ Skills] [⚙️ Settings]
```

### 2.4 DataTable for Tabular Data

**Objective**: Replace string-based tables with interactive DataTable

| Task | File | Description |
|------|------|-------------|
| `T2.4.1` | `src/ui/tui/ultimate_dashboard.py` | Migrate Agents panel to DataTable |
| `T2.4.2` | `src/ui/tui/ultimate_dashboard.py` | Migrate Routing panel to DataTable |
| `T2.4.3` | `src/ui/tui/ultimate_dashboard.py` | Add sorting, filtering |

**Pattern**:
```python
def _get_agents_content(self) -> str:
    # OLD: Return formatted string
    # NEW: Return DataTable widget
    
    table = DataTable(show_cursor=True, zebra_stripes=True)
    table.add_columns("Agent", "Model", "Status", "Tasks", "Success%", "Latency")
    
    for agent in self.live_data.get("agents", []):
        table.add_row(
            agent["name"],
            agent["model"],
            "🟢" if agent["running"] else "🔴",
            str(agent["tasks"]),
            f"{agent["success_rate"]:.1f}%",
            f"{agent["avg_latency"]}ms"
        )
    return table
```

---

## Phase 3: Interactive Features (Week 3)

### 3.1 Command Palette (Cmd+K)

**Objective**: VSCode-style command palette for navigation and actions

| Task | File | Description |
|------|------|-------------|
| `T3.1.1` | `src/ui/tui/widgets/command_palette.py` (NEW) | Create CommandPalette widget |
| `T3.1.2` | `src/ui/tui/ultimate_dashboard.py` | Bind Cmd+K / Ctrl+K |
| `T3.1.3` | `src/ui/tui/widgets/command_palette.py` | Fuzzy search commands |

**Commands**:
```
> Go to Memory Panel
> Go to Agents Panel
> Refresh All Data
> Toggle Dark Mode
> Export Dashboard
> Search...
> Settings
> Toggle Fullscreen
```

### 3.2 Predictive Insights Panel

**Objective**: Show AI-generated insights from learning data

| Task | File | Description |
|------|------|-------------|
| `T3.2.1` | `src/dashboard/panels/insights.py` (NEW) | Create InsightsPanel |
| `T3.2.2` | `src/dashboard/panels/insights.py` | Generate insights from learning stats |
| `T3.2.3` | `src/ui/tui/ultimate_dashboard.py` | Add to panel rotation |

**Insights Examples**:
```
INSIGHTS
─────────────────────────────────────────
📈 Your agents are 40% more active on Tuesdays
💾 Memory usage peaked at 22,466 files on Monday
🧠 28 unique queries this week (up 15%)
⚡ Top skill: git-master (127 uses)
🔄 Routing: opencode/qwen3.6-plus-free (78%)
```

### 3.3 Agent Relationship Graph

**Objective**: Visualize agent delegation chains

| Task | File | Description |
|------|------|-------------|
| `T3.3.1` | `src/ui/tui/widgets/agent_graph.py` (NEW) | Create ASCII graph visualization |
| `T3.3.2` | `src/dashboard/panels/agents.py` | Integrate into Agents panel |
| `T3.3.3` | `src/ui/tui/widgets/agent_graph.py` | Show delegation depth |

**Display**:
```
AGENT DELEGATION CHAIN
══════════════════════════════════════

[Sisyphus] ─────┬──> [Hephaestus]
 (orchestrate)  │    (implement)
                ├──> [Explore]
                │    (search)
                └──> [Oracle]
                     (review)

Depth: 2 | Active: 4 | Total: 8
```

### 3.4 Session Replay

**Objective**: Replay past dashboard sessions

| Task | File | Description |
|------|------|-------------|
| `T3.4.1` | `src/dashboard/session_recorder.py` (NEW) | Record dashboard state snapshots |
| `T3.4.2` | `src/dashboard/session_recorder.py` | Store in ~/.nxyme/sessions/ |
| `T3.4.3` | `src/ui/tui/ultimate_dashboard.py` | Add replay controls |

---

## Phase 4: Advanced Visualizations (Week 4)

### 4.1 Knowledge Graph View

**Objective**: Visualize memory knowledge graph

| Task | File | Description |
|------|------|-------------|
| `T4.1.1` | `src/ui/tui/widgets/kg_viewer.py` (NEW) | Create ASCII knowledge graph |
| `T4.1.2` | `src/dashboard/panels/knowledge.py` (NEW) | Create Knowledge panel |
| `T4.1.3` | `src/dashboard/panels/knowledge.py` | Show entities and relationships |

**Display**:
```
KNOWLEDGE GRAPH
═══════════════════════════════════════════

    [Sisyphus]
     ├──delegates──► [Hephaestus]
     │               └──implements──► [Code]
     ├──monitors──► [Oracle]
     │               └──reviews──► [Design]
     └──learns──► [Memory]
                    ├──stores──► [Entities]
                    └──tracks──► [Relations]

Entities: 156 | Relations: 234 | Depth: 3
```

### 4.2 Routing Funnel Visualization

**Objective**: Show request flow through intelligent router

| Task | File | Description |
|------|------|-------------|
| `T4.2.1` | `src/ui/tui/widgets/routing_funnel.py` (NEW) | Create RoutingFunnel widget |
| `T4.2.2` | `src/dashboard/panels/routing.py` | Integrate funnel |
| `T4.2.3` | `src/dashboard/panels/routing.py` | Show success rates |

**Display**:
```
ROUTING FUNNEL
═══════════════════════════════════════

Requests: 1,247
     │
     ▼ 100% [Trigger Match]
     │
     ▼  87% [Memory Route]
     │
     ▼  78% [Model Select]
     │
     ▼  94% [API Call]
     │
     ▼ 100% [Response]

Success Rate: 67% | Avg Latency: 1.2s
```

### 4.3 Cost & Usage Dashboard

**Objective**: Track API usage, VPN costs, token consumption

| Task | File | Description |
|------|------|-------------|
| `T4.3.1` | `src/dashboard/panels/costs.py` (NEW) | Create CostsPanel |
| `T4.3.2` | `src/dashboard/panels/costs.py` | Track provider usage |
| `T4.3.3` | `src/dashboard/panels/costs.py` | Show token consumption |

**Display**:
```
COST BREAKDOWN
═══════════════════════════════════════

Provider          Calls   Tokens   Cost
────────────────────────────────────────
opencode/qwen...  847    2.4M     $12.40
opencode/min...   312    890K     $4.50
ollama/llama...   88     120K     $0.00
────────────────────────────────────────
TOTAL            1,247   3.4M     $16.90

VPN Pool: $8.20 (9 backends active)
Today: $2.34 | This Week: $16.90
```

### 4.4 Live Activity Feed

**Objective**: Real-time scrolling log of all system events

| Task | File | Description |
|------|------|-------------|
| `T4.4.1` | `src/ui/tui/widgets/activity_feed.py` (NEW) | Create LiveActivityFeed |
| `T4.4.2` | `src/ui/tui/ultimate_dashboard.py` | Add as persistent bottom panel |
| `T4.4.3` | `src/ui/tui/widgets/activity_feed.py` | Color-coded by severity |

**Display**:
```
ACTIVITY FEED
═══════════════════════════════════════
14:32:05  🤖 Hephaestus: Completed task #847
14:32:03  📊 Memory: Indexed 12 new files
14:32:01  🧠 Intelligence: New pattern detected
14:31:58  🔀 Router: Selected qwen3.6-plus-free
14:31:55  ⚡ Skill: git-master invoked
14:31:52  💾 Learning: Stored feedback event
...
[Auto-scroll] [Filter: All] [Pause]
```

---

## Phase 5: Polish & Performance (Week 5)

### 5.1 Theme System Enhancement

| Task | File | Description |
|------|------|-------------|
| `T5.1.1` | `src/dashboard/themes/` | Add 3 new themes (Cyberpunk, Solarized, Dracula) |
| `T5.1.2` | `src/ui/tui/ultimate_dashboard.py` | Theme selector in settings |
| `T5.1.3` | `src/dashboard/themes/theme_system.py` | Animated theme transitions |

### 5.2 Performance Optimization

| Task | File | Description |
|------|------|-------------|
| `T5.2.1` | `src/dashboard/data_provider.py` | Implement smart refresh intervals |
| `T5.2.2` | `src/ui/tui/ultimate_dashboard.py` | Batch UI updates |
| `T5.2.3` | `src/dashboard/data_provider.py` | Background prefetching |

### 5.3 Error Boundaries

| Task | File | Description |
|------|------|-------------|
| `T5.3.1` | `src/ui/tui/ultimate_dashboard.py` | Individual panel try/catch |
| `T5.3.2` | `src/ui/tui/ultimate_dashboard.py` | Graceful degradation |
| `T5.3.3` | `src/ui/tui/ultimate_dashboard.py` | Error panel fallback |

---

## Widget Library (NEW)

Create `src/ui/tui/widgets/` directory:

```
widgets/
├── __init__.py
├── sparkline_widget.py      # T1.2, T2.1
├── activity_heatmap.py      # T2.2
├── command_palette.py       # T3.1
├── agent_graph.py          # T3.3
├── kg_viewer.py            # T4.1
├── routing_funnel.py       # T4.2
├── activity_feed.py        # T4.4
├── metric_card.py          # Generic metric display
├── progress_ring.py        # Circular progress
└── status_indicator.py     # Light-style status
```

---

## File Changes Summary

### New Files (17)

| File | Phase | Purpose |
|------|-------|---------|
| `src/dashboard/data_provider.py` | T1.1 | Unified async data layer |
| `src/dashboard/session_recorder.py` | T3.4 | Session recording |
| `src/dashboard/panels/insights.py` | T3.2 | Predictive insights |
| `src/dashboard/panels/knowledge.py` | T4.1 | Knowledge graph |
| `src/dashboard/panels/costs.py` | T4.3 | Cost tracking |
| `src/ui/tui/widgets/__init__.py` | T2+ | Widget package |
| `src/ui/tui/widgets/sparkline_widget.py` | T2.1 | Sparklines |
| `src/ui/tui/widgets/activity_heatmap.py` | T2.2 | Activity heatmap |
| `src/ui/tui/widgets/command_palette.py` | T3.1 | Cmd+K palette |
| `src/ui/tui/widgets/agent_graph.py` | T3.3 | Agent relationships |
| `src/ui/tui/widgets/kg_viewer.py` | T4.1 | Knowledge graph |
| `src/ui/tui/widgets/routing_funnel.py` | T4.2 | Routing funnel |
| `src/ui/tui/widgets/activity_feed.py` | T4.4 | Live feed |
| `src/ui/tui/widgets/metric_card.py` | T2+ | Metric display |
| `src/ui/tui/widgets/progress_ring.py` | T4+ | Circular progress |
| `src/ui/tui/widgets/status_indicator.py` | T2+ | Status lights |
| `docs/dashboard-v2-plan.md` | - | This document |

### Modified Files (3)

| File | Changes |
|------|---------|
| `src/ui/tui/ultimate_dashboard.py` | T1.2, T1.3, T1.4, T2.3, T2.4, T3.1, T4.4, T5.1, T5.2, T5.3 |
| `src/dashboard/panels/agents.py` | T2.2, T2.4, T3.3 |
| `src/dashboard/panels/routing.py` | T2.4, T4.2 |

---

## Dependencies

```python
# requirements.txt additions
textual>=0.90.0          # Core framework
textual-plotext>=0.3.0  # Plotting (optional)
rich>=13.0.0            # Terminal rendering
```

---

## Testing Strategy

| Phase | Tests |
|-------|-------|
| T1.1 | Unit tests for DataProvider |
| T1.2 | Reactive attribute tests |
| T2.1 | Sparkline rendering tests |
| T3.1 | Command palette fuzzy search |
| All | Integration tests for data flow |

---

## Implementation Priority

```
Week 1: T1.1 → T1.2 → T1.3 → T1.4
Week 2: T2.1 → T2.2 → T2.3 → T2.4
Week 3: T3.1 → T3.2 → T3.3 → T3.4
Week 4: T4.1 → T4.2 → T4.3 → T4.4
Week 5: T5.1 → T5.2 → T5.3 + Testing + Polish
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Panel load time | <500ms |
| Data refresh | 60fps UI |
| Memory footprint | <100MB |
| Startup time | <2s |
| Command palette | <100ms response |

---

## Future Considerations (Post-v2)

- Web-based dashboard with WebSocket
- Mobile companion app
- Real-time collaboration
- Plugin ecosystem
- Voice commands

---

*End of Master Plan v2.0*