# N-Xyme MIND Dashboard v2.0 — COMPREHENSIVE MASTER PLAN

> **Version**: 2.0 Final | **Status**: Ready for Execution  
> **Generated**: 2026-04-06 | **Total Tasks**: 127

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Phase 0: Cleanup (Pre-requisites)](#phase-0-cleanup-pre-requisites)
3. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
4. [Phase 2: Data Layer](#phase-2-data-layer)
5. [Phase 3: UI Components](#phase-3-ui-components)
6. [Phase 4: Features](#phase-4-features)
7. [Phase 5: Advanced Features](#phase-5-advanced-features)
8. [Phase 6: Polish](#phase-6-polish)
9. [Task Dependencies Matrix](#task-dependencies-matrix)
10. [Resource Allocation](#resource-allocation)
11. [Risk Assessment](#risk-assessment)

---

## EXECUTIVE SUMMARY

### Current State
- ✅ 17 tabs functional
- ✅ 65+ buttons with handlers
- ✅ 2526 lines of code
- ✅ Compilation verified

### Target State
- Production-ready dashboard
- Real-time data integration
- Full interactivity
- Zero LSP errors

### Effort Breakdown
| Phase | Tasks | Complexity |
|-------|-------|-------------|
| Phase 0 | 8 | Low |
| Phase 1 | 15 | Medium |
| Phase 2 | 20 | High |
| Phase 3 | 25 | Medium |
| Phase 4 | 30 | Medium-High |
| Phase 5 | 20 | High |
| Phase 6 | 9 | Low |

---

## PHASE 0: CLEANUP (Pre-requisites)

**Objective**: Fix critical issues before proceeding

### T0.1: Fix LSP Errors in Dashboard

- [ ] T0.1.1 Fix dictionary access at line 356 (ultimate_dashboard.py)
- [ ] T0.1.2 Fix dictionary access at line 363 (ultimate_dashboard.py)
- [ ] T0.1.3 Run `python3 -m py_compile` verify clean
- [ ] T0.1.4 Verify no new LSP errors introduced

### T0.2: Remove Dead Code

- [ ] T0.2.1 Identify unused `_action_*` stub functions
- [ ] T0.2.2 Either implement or remove stub functions
- [ ] T0.2.3 Clean up commented-out code blocks

### T0.3: Code Organization

- [ ] T0.3.1 Ensure consistent import ordering
- [ ] T0.3.2 Check all type hints are correct
- [ ] T0.3.3 Verify docstrings on public methods

---

## PHASE 1: CORE INFRASTRUCTURE

**Objective**: Build the foundation for data integration

### T1.1: Dashboard State Management

- [ ] T1.1.1 Create `src/ui/tui/dashboard_state.py`
- [ ] T1.1.2 Implement `DashboardState` class with:
  - `current_tab: str`
  - `dark_mode: bool`
  - `auto_refresh: bool`
  - `preferences: dict`
- [ ] T1.1.3 Add `save()` method to persist to JSON
- [ ] T1.1.4 Add `load()` method to restore from JSON
- [ ] T1.1.5 Add `reset()` method for defaults

### T1.2: Event Bus System

- [ ] T1.2.1 Create `src/ui/tui/events.py`
- [ ] T1.2.2 Define `EventBus` class
- [ ] T1.2.3 Add `subscribe(event_type, callback)` method
- [ ] T1.2.4 Add `publish(event_type, data)` method
- [ ] T1.2.5 Add `unsubscribe(event_type, callback)` method

### T1.3: Command Registry

- [ ] T1.3.1 Create `src/ui/tui/commands.py`
- [ ] T1.3.2 Define `Command` dataclass with:
  - `id: str`
  - `name: str`
  - `description: str`
  - `callback: Callable`
  - `shortcut: str | None`
- [ ] T1.3.3 Implement `CommandRegistry` class
- [ ] T1.3.4 Add `register(command)` method
- [ ] T1.3.5 Add `get_by_shortcut(key)` method
- [ ] T1.3.6 Add `get_all()` method returning list

### T1.4: Plugin System Skeleton

- [ ] T1.4.1 Create `src/ui/tui/plugins/__init__.py`
- [ ] T1.4.2 Define `Plugin` base class
- [ ] T1.4.3 Define `PluginMetadata` dataclass
- [ ] T1.4.4 Implement `PluginManager` class
- [ ] T1.4.5 Add `discover_plugins()` method
- [ ] T1.4.6 Add `load_plugin(plugin_id)` method
- [ ] T1.4.7 Add `unload_plugin(plugin_id)` method

### T1.5: Constants & Config

- [ ] T1.5.1 Create `src/ui/tui/constants.py`
- [ ] T1.5.2 Define tab IDs as constants
- [ ] T1.5.3 Define button IDs as constants
- [ ] T1.5.4 Define event types as constants
- [ ] T1.5.5 Define default refresh intervals

---

## PHASE 2: DATA LAYER

**Objective**: Connect dashboard to real system data

### T2.1: Enhanced Data Provider

- [ ] T2.1.1 Enhance `src/dashboard/data_provider.py`
- [ ] T2.1.2 Add `get_daemon_status() -> dict` method
- [ ] T2.1.3 Add `start_daemon() -> bool` method
- [ ] T2.1.4 Add `stop_daemon() -> bool` method
- [ ] T2.1.5 Add `get_agents_status() -> list[dict]` method
- [ ] T2.1.6 Add `get_memory_stats() -> dict` method
- [ ] T2.1.7 Add `get_proxy_status() -> dict` method

### T2.2: System Metrics Collector

- [ ] T2.2.1 Create `src/dashboard/metrics.py`
- [ ] T2.2.2 Implement `SystemMetrics` class
- [ ] T2.2.3 Add CPU usage tracking
- [ ] T2.2.4 Add memory usage tracking
- [ ] T2.2.5 Add disk I/O tracking
- [ ] T2.2.6 Add network I/O tracking
- [ ] T2.2.7 Add timestamp to each sample

### T2.3: Agent Health Monitor

- [ ] T2.3.1 Create `src/dashboard/agent_monitor.py`
- [ ] T2.3.2 Implement `AgentHealth` class
- [ ] T2.3.3 Add `check_agent(agent_name) -> dict` method
- [ ] T2.3.4 Add `check_all_agents() -> list[dict]` method
- [ ] T2.3.5 Add response time tracking
- [ ] T2.3.6 Add success/failure counting
- [ ] T2.3.7 Add health status determination

### T2.4: Memory Graph Interface

- [ ] T2.4.1 Create `src/dashboard/memory_interface.py`
- [ ] T2.4.2 Add `get_entities() -> list[dict]` method
- [ ] T2.4.3 Add `get_relations() -> list[dict]` method
- [ ] T2.4.4 Add `search_entities(query) -> list[dict]` method
- [ ] T2.4.5 Add `add_entity(entity) -> bool` method
- [ ] T2.4.6 Add `clear_all() -> bool` method

### T2.5: Routing Data Provider

- [ ] T2.5.1 Enhance routing data access
- [ ] T2.5.2 Add `get_triggers() -> list[dict]` method
- [ ] T2.5.3 Add `get_weights() -> dict` method
- [ ] T2.5.4 Add `get_routing_stats() -> dict` method
- [ ] T2.5.5 Add `add_trigger(trigger) -> bool` method

### T2.6: Config File Manager

- [ ] T2.6.1 Create `src/dashboard/config_manager.py`
- [ ] T2.6.2 Add `read_config(path) -> dict` method
- [ ] T2.6.3 Add `write_config(path, data) -> bool` method
- [ ] T2.6.4 Add `validate_config(path) -> tuple[bool, list[str]]` method
- [ ] T2.6.5 Add `backup_config(path) -> bool` method
- [ ] T2.6.6 Add `restore_config(backup_path) -> bool` method

### T2.7: Task Queue Interface

- [ ] T2.7.1 Create `src/dashboard/task_manager.py`
- [ ] T2.7.2 Add `get_tasks() -> list[dict]` method
- [ ] T2.7.3 Add `create_task(task) -> str` method
- [ ] T2.7.4 Add `start_task(task_id) -> bool` method
- [ ] T2.7.5 Add `stop_task(task_id) -> bool` method
- [ ] T2.7.6 Add `get_task_status(task_id) -> dict` method

---

## PHASE 3: UI COMPONENTS

**Objective**: Build reusable UI widgets

### T3.1: Chart Components

- [ ] T3.1.1 Create `src/ui/tui/widgets/charts.py`
- [ ] T3.1.2 Implement `LineChart` widget
- [ ] T3.1.3 Implement `BarChart` widget
- [ ] T3.1.4 Implement `Sparkline` widget (enhanced)
- [ ] T3.1.5 Add `set_data(data)` method to each
- [ ] T3.1.6 Add `set_color(color)` method
- [ ] T3.1.7 Add `set_labels(labels)` method

### T3.2: Table Components

- [ ] T3.2.1 Create `src/ui/tui/widgets/tables.py`
- [ ] T3.2.2 Implement `SortableTable` widget
- [ ] T3.2.3 Add `add_column(name, width)` method
- [ ] T3.2.4 Add `add_row(values)` method
- [ ] T3.2.5 Add `sort_by(column)` method
- [ ] T3.2.6 Add `filter(predicate)` method
- [ ] T3.2.7 Add `select_row(index)` method

### T3.3: Form Components

- [ ] T3.3.1 Create `src/ui/tui/widgets/forms.py`
- [ ] T3.3.2 Implement `TextField` widget
- [ ] T3.3.3 Implement `SelectField` widget
- [ ] T3.3.4 Implement `CheckboxField` widget
- [ ] T3.3.5 Implement `NumberField` widget
- [ ] T3.3.6 Add validation to each field type
- [ ] T3.3.7 Add `get_value()` and `set_value()`

### T3.4: Card Components

- [ ] T3.4.1 Enhance `MetricCard` widget
- [ ] T3.4.2 Add optional icon parameter
- [ ] T3.4.3 Add optional graph parameter
- [ ] T3.4.4 Add click handler support
- [ ] T3.4.5 Add hover state styling
- [ ] T3.4.6 Add expand/collapse capability

### T3.5: Status Indicators

- [ ] T3.5.1 Enhance `StatusIndicator` widget
- [ ] T3.5.2 Add blinking animation for "loading"
- [ ] T3.5.3 Add pulse animation for "active"
- [ ] T3.5.4 Add size variants (small, medium, large)
- [ ] T3.5.5 Add custom color support

### T3.6: Progress Components

- [ ] T3.6.1 Create `src/ui/tui/widgets/progress.py`
- [ ] T3.6.2 Implement `StepProgress` widget (multi-step)
- [ ] T3.6.3 Implement `CircularProgress` widget
- [ ] T3.6.4 Add percentage display option
- [ ] T3.6.5 Add label support

### T3.7: Navigation Components

- [ ] T3.7.1 Create `src/ui/tui/widgets/navigation.py`
- [ ] T3.7.2 Implement `Breadcrumbs` widget
- [ ] T3.7.3 Implement `Tabs` widget (horizontal)
- [ ] T3.7.4 Implement `Pagination` widget
- [ ] T3.7.5 Add keyboard navigation support

---

## PHASE 4: FEATURES

**Objective**: Implement core dashboard features

### T4.1: Config Editor Dialog

- [ ] T4.1.1 Create `src/ui/tui/dialogs/__init__.py`
- [ ] T4.1.2 Create `src/ui/tui/dialogs/config_editor.py`
- [ ] T4.1.3 Implement `ConfigEditorScreen` class
- [ ] T4.1.4 Add syntax highlighting for JSON
- [ ] T4.1.5 Add line numbers
- [ ] T4.1.6 Add save/cancel buttons
- [ ] T4.1.7 Add validation before save
- [ ] T4.1.8 Add undo/redo support

### T4.2: Agent Manager Dialog

- [ ] T4.2.1 Create `src/ui/tui/dialogs/agent_manager.py`
- [ ] T4.2.2 Implement `AgentManagerScreen` class
- [ ] T4.2.3 Add agent list display
- [ ] T4.2.4 Add start/stop buttons per agent
- [ ] T4.2.5 Add agent configuration form
- [ ] T4.2.6 Add agent logs viewer

### T4.3: Memory Explorer

- [ ] T4.3.1 Create `src/ui/tui/dialogs/memory_explorer.py`
- [ ] T4.3.2 Implement `MemoryExplorerScreen` class
- [ ] T4.3.3 Add entity list with search
- [ ] T4.3.4 Add relation visualization
- [ ] T4.3.5 Add entity detail panel
- [ ] T4.3.6 Add add/delete entity controls

### T4.4: Proxy Manager

- [ ] T4.4.1 Create `src/ui/tui/dialogs/proxy_manager.py`
- [ ] T4.4.2 Implement `ProxyManagerScreen` class
- [ ] T4.4.3 Add backend list display
- [ ] T4.4.4 Add start/stop per backend
- [ ] T4.4.5 Add country selector
- [ ] T4.4.6 Add rotation controls

### T4.5: Trigger Editor

- [ ] T4.5.1 Create `src/ui/tui/dialogs/trigger_editor.py`
- [ ] T4.5.2 Implement `TriggerEditorScreen` class
- [ ] T4.5.3 Add trigger list display
- [ ] T4.5.4 Add create new trigger form
- [ ] T4.5.5 Add edit existing trigger
- [ ] T4.5.6 Add delete trigger

### T4.6: Settings Panel

- [ ] T4.6.1 Enhance Settings tab
- [ ] T4.6.2 Add Display settings section
- [ ] T4.6.3 Add Behavior settings section
- [ ] T4.6.4 Add Notification settings section
- [ ] T4.6.5 Add Keyboard shortcuts section
- [ ] T4.6.6 Add About section

### T4.7: Search & Filter

- [ ] T4.7.1 Implement global search (Ctrl+F)
- [ ] T4.7.2 Add search input overlay
- [ ] T4.7.3 Add result highlighting
- [ ] T4.7.4 Add filter by tab dropdown
- [ ] T4.7.5 Add regex search toggle

### T4.8: Activity Log

- [ ] T4.8.1 Create `src/ui/tui/dialogs/activity_log.py`
- [ ] T4.8.2 Implement `ActivityLogScreen` class
- [ ] T4.8.3 Add timestamp column
- [ ] T4.8.4 Add event type column
- [ ] T4.8.5 Add message column
- [ ] T4.8.6 Add filter by type
- [ ] T4.8.7 Add export to file

---

## PHASE 5: ADVANCED FEATURES

**Objective**: Enterprise-grade functionality

### T5.1: Batch Operations

- [ ] T5.1.1 Add multi-select to agent list
- [ ] T5.1.2 Add batch start button
- [ ] T5.1.3 Add batch stop button
- [ ] T5.1.4 Add batch delete button
- [ ] T5.1.5 Add selection count display

### T5.2: Custom Shortcuts

- [ ] T5.2.1 Add keyboard shortcut configuration
- [ ] T5.2.2 Add shortcut conflict detection
- [ ] T5.2.3 Add custom macro recording
- [ ] T5.2.4 Add shortcut import/export

### T5.3: Scheduled Tasks

- [ ] T5.3.1 Add cron-like scheduling UI
- [ ] T5.3.2 Add task scheduling form
- [ ] T5.3.3 Add schedule list display
- [ ] T5.3.4 Add enable/disable toggle
- [ ] T5.3.5 Add next run time display

### T5.4: Webhook Integration

- [ ] T5.4.1 Create webhook configuration
- [ ] T5.4.2 Add webhook URL input
- [ ] T5.4.3 Add event selector
- [ ] T5.4.4 Add test webhook button
- [ ] T5.4.5 Add webhook history

### T5.5: Export/Import

- [ ] T5.5.1 Add full dashboard export
- [ ] T5.5.2 Add partial export (per tab)
- [ ] T5.5.3 Add import functionality
- [ ] T5.5.4 Add export format selector (JSON, YAML)
- [ ] T5.5.5 Add merge on import

### T5.6: Benchmark Runner

- [ ] T5.6.1 Create benchmark dialog
- [ ] T5.6.2 Add benchmark type selector
- [ ] T5.6.3 Add run button with progress
- [ ] T5.6.4 Add results comparison
- [ ] T5.6.5 Add export results

### T5.7: Diagnostics

- [ ] T5.7.1 Add system info gatherer
- [ ] T5.7.2 Add error log collector
- [ ] T5.7.3 Add config dumper
- [ ] T5.7.4 Add diagnostic bundle creator
- [ ] T5.7.5 Add copy to clipboard

---

## PHASE 6: POLISH

**Objective**: Final touches and testing

### T6.1: Accessibility

- [ ] T6.1.1 Add ARIA labels to interactive elements
- [ ] T6.1.2 Add keyboard navigation to all widgets
- [ ] T6.1.3 Add focus indicators
- [ ] T6.1.4 Add screen reader support hints

### T6.2: Performance Optimization

- [ ] T6.2.1 Profile dashboard load time
- [ ] T6.2.2 Optimize render cycles
- [ ] T6.2.3 Add lazy loading for heavy tabs
- [ ] T6.2.4 Cache expensive computations

### T6.3: Testing

- [ ] T6.3.1 Add unit tests for data providers
- [ ] T6.3.2 Add unit tests for UI components
- [ ] T6.3.3 Add integration tests for dialogs
- [ ] T6.3.4 Add keyboard shortcut tests

### T6.4: Documentation

- [ ] T6.4.1 Add inline code documentation
- [ ] T6.4.2 Create user guide markdown
- [ ] T6.4.3 Create API reference
- [ ] T6.4.4 Add keyboard shortcuts cheatsheet

### T6.5: Final Review

- [ ] T6.5.1 Run full LSP check - zero errors
- [ ] T6.5.2 Run all tests - all pass
- [ ] T6.5.3 Manual testing of all buttons
- [ ] T6.5.4 Verify all dialogs work
- [ ] T6.5.5 Check all tabs render

---

## TASK DEPENDENCIES MATRIX

```
T0.1 ──┬──> T1.1 ──> T2.1 ──> T3.1 ──> T4.1 ──> T5.1 ──> T6.1
T0.2 ──┘   T1.2 ──> T2.2 ──> T3.2 ──> T4.2 ──> T5.2 ──> T6.2
T0.3 ─────> T1.3 ──> T2.3 ──> T3.3 ──> T4.3 ──> T5.3 ──> T6.3
           T1.4 ──> T2.4 ──> T3.4 ──> T4.4 ──> T5.4 ──> T6.4
           T1.5 ──> T2.5 ──> T3.5 ──> T4.5 ──> T5.5 ──> T6.5
                       T2.6 ──> T3.6 ──> T4.6
                       T2.7 ──> T3.7 ──> T4.7
                                   T4.8
```

---

## RESOURCE ALLOCATION

### Files to Create (32 new files)

```
src/ui/tui/
├── constants.py              # T1.5
├── events.py                # T1.2
├── commands.py              # T1.3
├── dashboard_state.py      # T1.1
├── plugins/
│   ├── __init__.py          # T1.4
│   └── base.py              # T1.4
├── widgets/
│   ├── charts.py            # T3.1
│   ├── tables.py            # T3.2
│   ├── forms.py             # T3.3
│   ├── progress.py          # T3.6
│   └── navigation.py       # T3.7
├── dialogs/
│   ├── __init__.py          # T4.1
│   ├── config_editor.py     # T4.1
│   ├── agent_manager.py     # T4.2
│   ├── memory_explorer.py   # T4.3
│   ├── proxy_manager.py     # T4.4
│   ├── trigger_editor.py    # T4.5
│   ├── activity_log.py     # T4.8
│   └── benchmark_runner.py # T5.6
└── screens/
    └── settings.py         # T4.6

src/dashboard/
├── metrics.py              # T2.2
├── agent_monitor.py       # T2.3
├── memory_interface.py    # T2.4
├── config_manager.py      # T2.6
└── task_manager.py        # T2.7
```

### Files to Modify (4 files)

```
src/ui/tui/ultimate_dashboard.py    # Wire to new data layer
src/dashboard/data_provider.py       # Enhance data access
src/ui/tui/widgets/__init__.py       # Export new widgets
src/ui/tui/screens/__init__.py       # Export new screens
```

---

## RISK ASSESSMENT

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep | High | Lock Phase 1-3 before starting 4-6 |
| LSP errors | Medium | Fix immediately (T0.1) |
| Missing dependencies | Medium | Use stub implementations first |
| Performance issues | Medium | Profile early (T6.2) |
| Testing gaps | High | Add tests in parallel with dev |

---

## EXECUTION ORDER

### Week 1: Phase 0 + Phase 1
- T0.1-T0.3: Cleanup
- T1.1-T1.5: Core infrastructure

### Week 2-3: Phase 2
- T2.1-T2.7: Data layer

### Week 4-5: Phase 3
- T3.1-T3.7: UI components

### Week 6-7: Phase 4
- T4.1-T4.8: Features

### Week 8-9: Phase 5
- T5.1-T5.7: Advanced features

### Week 10: Phase 6
- T6.1-T6.5: Polish

---

*Master Plan Complete - 127 Tasks*  
*N-Xyme MIND Dashboard v2.0*