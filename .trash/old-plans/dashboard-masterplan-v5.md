# N-Xyme MIND Dashboard Masterplan v5.0

## Vision
Transform the dashboard into a **complete, frictionless, ADHD-friendly frontend** that exposes 100% of backend functionality through intuitive navigation, instant feedback, and zero-friction interactions.

## Architecture Decisions

### Navigation Pattern: Command Palette + Sidebar Hybrid
- **Command Palette** (Ctrl+P): Primary navigation — fuzzy search across all panels, configs, actions
- **Sidebar**: Secondary navigation — 11 subsystem views with module counts
- **Keyboard-first**: Every action accessible via 1-2 keystrokes
- **No nested menus**: Max 2 levels deep (sidebar → panel)

### State Management
- **Centralized**: `live_data` dict with all backend stats
- **Background refresh**: 10s interval via thread, non-blocking
- **Auto-save**: All config changes save immediately on change
- **Dirty tracking**: Visual indicator when unsaved changes exist

### Widget Strategy
- **DataTable**: For lists, arrays, tabular data
- **Input**: For text/number editing with auto-save
- **Switch**: For boolean toggles with auto-save
- **Static**: For read-only displays, status bars
- **Button**: For actions, navigation
- **Label**: For section headers, form labels
- **ScrollableContainer**: For long content
- **Horizontal/Vertical**: For layout
- **Header/Footer**: For chrome
- **Toast**: For notifications (add)
- **CommandPalette**: For search/navigation (add)

### Performance Requirements
- **Launch time**: <1s (instant loading state, background data fetch)
- **Panel switch**: <100ms (pre-cached data)
- **Config load**: <500ms (lazy-load on file selection)
- **Auto-save**: <100ms (debounced writes)
- **Refresh interval**: 10s (configurable)
- **Memory usage**: <100MB (streaming data, no full loads)

## Phased Implementation Plan

### Phase 1: Foundation (DONE)
- [x] 11 sidebar views with subsystem stats
- [x] Config Editor (14 JSON files, form-based, auto-save)
- [x] Settings Screen (9 panels, interactive toggles)
- [x] Background refresh (10s interval)
- [x] Dark mode toggle
- [x] 6 keyboard bindings

### Phase 2: Command Palette & Search (NEXT)
**Goal**: One-key access to everything
- [ ] Add `CommandPalette` widget (Ctrl+P)
- [ ] Index all panels, configs, actions, backend functions
- [ ] Fuzzy search across all indexed items
- [ ] Quick actions: restart daemon, flush cache, reset learning, rebuild index
- [ ] Recent items history
- [ ] Keyboard shortcuts reference in palette

**New bindings**: `ctrl+p` command palette
**Estimated effort**: 2-3 hours

### Phase 3: Notification System
**Goal**: Instant feedback on all actions
- [ ] Add `Toast` widget integration
- [ ] System alerts: daemon status changes, Ollama down, memory full
- [ ] Action confirmations: config saved, learning reset, index rebuilt
- [ ] Error notifications: failed saves, connection errors
- [ ] Warning indicators: high memory usage, low disk space
- [ ] Notification center (view all recent notifications)

**Estimated effort**: 1-2 hours

### Phase 4-14: Deepen All Panels
**Goal**: Expose all 900+ backend functions

| Phase | Panel | Modules | Functions | Effort |
|-------|-------|---------|-----------|--------|
| 4 | GPU/Hardware | 12 | 150+ | 2-3h |
| 5 | Message Queue | 2 | 28+ | 1-2h |
| 6 | Observability/Tracing | 6 | 57+ | 3-4h |
| 7 | Security Controls | 9 | 150+ | 4-5h |
| 8 | Memory Deep Dive | 58 | 66+ | 4-5h |
| 9 | Intelligence Deep Dive | 36 | 34+ | 6-8h |
| 10 | Network/VPN | 3 | 40+ | 2-3h |
| 11 | Model Router | 10 | 70+ | 3-4h |
| 12 | Workers | 3 | 40+ | 2-3h |
| 13 | Healing | 1 | 33+ | 2-3h |
| 14 | State Management | 3 | 35+ | 2-3h |

### Phase 15: Polish & ADHD Optimization
**Goal**: Frictionless UX
- [ ] Vim-style navigation (j/k, gg, G, /, ?)
- [ ] Pin favorite panels
- [ ] Custom layouts
- [ ] Widget resizing
- [ ] Built-in help system
- [ ] Keyboard shortcut reference
- [ ] System documentation
- [ ] Export/Import configs, memories, patterns
- [ ] Progress indicators for long operations
- [ ] Error recovery built-in
- [ ] Consistent patterns across all panels
- [ ] Color coding for status (green=ok, yellow=warn, red=error)
- [ ] Status always visible in footer
- [ ] One-key access to any panel (1-9, then letters)
- [ ] Auto-save everywhere
- [ ] No modal dialogs that block workflow

**Estimated effort**: 4-6 hours

## Success Criteria

### Functional
- [ ] 100% of backend functions exposed (900+)
- [ ] All 20+ subsystems have dedicated panels
- [ ] All 14 config files editable with auto-save
- [ ] Command palette searches everything
- [ ] Notifications for all system events
- [ ] Real-time data refresh (10s interval)
- [ ] Export/Import for all configs
- [ ] Audit log viewer
- [ ] Help system with documentation

### Performance
- [ ] Launch time <1s
- [ ] Panel switch <100ms
- [ ] Config load <500ms
- [ ] Auto-save <100ms
- [ ] Memory usage <100MB
- [ ] No blocking operations

### UX/ADHD-Friendly
- [ ] Instant feedback on every action
- [ ] Clear visual hierarchy with color coding
- [ ] Keyboard-first navigation
- [ ] No nested menus deeper than 2 levels
- [ ] Search everything (command palette)
- [ ] Status always visible
- [ ] One-key access to any panel
- [ ] Auto-save everywhere
- [ ] No modal dialogs that block workflow
- [ ] Progress indicators for long operations
- [ ] Error recovery built-in
- [ ] Consistent patterns across all panels

## Total Estimated Effort
- **Phase 2-14**: ~40-55 hours
- **Phase 15**: ~4-6 hours
- **Total**: ~44-61 hours

## Next Steps
1. **Phase 2**: Command Palette & Search (highest impact, lowest effort)
2. **Phase 3**: Notification System (critical for feedback)
3. **Phase 4-14**: Deepen panels (incremental, any order)
4. **Phase 15**: Polish (final touch)
