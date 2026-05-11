# N-Xyme MIND Frontend - Phase 2 Masterplan (55 Remaining Features)

## Overview
After completing Phase 1 (most critical features), **55 features remain** across all 5 pages. This document prioritizes them for implementation.

---

## Chat Page - Remaining (8 features)

### Not Yet Implemented:
- [ ] Copy message button (on each message)
- [ ] Edit/regenerate message
- [ ] Import conversation
- [ ] Share conversation (generate shareable link)
- [ ] Message timestamp toggle (show/hide timestamps)

### UI Improvements:
- [ ] Conversation sidebar should persist collapsed state
- [ ] Export conversation should include metadata (date, model used)
- [ ] Voice input should show recording duration

---

## Memory Page - Remaining (12 features)

### Graph & Visualization:
- [ ] Real-time node updates (simulated with setInterval)
- [ ] Fullscreen mode for graph
- [ ] Zoom to selected node
- [ ] Mini-map (small map showing full graph)

### Data Operations:
- [ ] Bulk select memories (checkboxes)
- [ ] Bulk delete selected memories
- [ ] Memory export (JSON) - download all memories
- [ ] Memory import (upload JSON file)

### Graph Interaction:
- [ ] Edge labels (show relationship type on edges)
- [ ] Node context menu (right-click): Edit, Delete, Pin, Connect

---

## Orchestration Page - Remaining (15 features)

### Real-time Updates (Priority 1):
- [ ] WebSocket connection setup (mock server)
- [ ] Agent status live updates (status changes in real-time)
- [ ] Task progress streaming (progress bar updates)
- [ ] Connection status indicator (connected/disconnected badge)

### Task Management:
- [ ] Drag-drop task reordering in queue
- [ ] Task dependencies (link tasks together)
- [ ] Task due date/time picker
- [ ] Bulk task operations (select multiple, delete, move)

### Queue Management:
- [ ] Export queue (JSON download)
- [ ] Import queue (JSON upload)
- [ ] Clear completed tasks button
- [ ] Queue statistics (total, pending, completed, failed)

### Visualization:
- [ ] Zoom to selected node (when clicking task)
- [ ] Auto-arrange nodes button (clean layout)

---

## Dashboard Page - Remaining (7 features)

### Metrics:
- [ ] Metric comparison (vs last period - "up 12% from last week")
- [ ] Interactive chart - click on bar shows details

### Activity Feed:
- [ ] Real-time activity stream (auto-update every 5s)
- [ ] Activity details expand (click to see full details)
- [ ] Clear activity log button
- [ ] Activity timestamp relative ("2 minutes ago")

### Quick Actions:
- [ ] Keyboard shortcuts help in quick actions area

---

## Settings Page - Remaining (6 features)

### System:
- [ ] Backup settings (download JSON)
- [ ] Restore settings (upload JSON)

### API & Keys:
- [ ] Key permissions (read-only, full access toggle)
- [ ] Usage statistics (API calls this month, tokens used)

### Agents:
- [ ] Agent test button (test agent connectivity)

---

## Cross-Cutting (7 features)

### Global:
- [ ] Error boundaries (wrap pages in error boundary component)
- [ ] Global loading state (full-screen loading overlay)
- [ ] Network status indicator (offline/online badge)

### Responsive:
- [ ] Touch gesture support (swipe to navigate on mobile)
- [ ] Pull-to-refresh on mobile

### Data Persistence:
- [ ] Settings sync to localStorage (all settings tabs)
- [ ] Export all user data (ZIP with all localStorage data)

---

## Implementation Priority

### P0 (This Week):
1. Chat: Copy + Edit message
2. Orchestration: WebSocket + real-time updates
3. Dashboard: Real-time activity stream
4. Settings: Backup/restore

### P1 (Next Week):
1. Memory: Bulk operations + export/import
2. Orchestration: Queue management
3. Dashboard: Metric comparison
4. Cross-cutting: Error boundaries

### P2 (Following Week):
1. Memory: Mini-map, fullscreen
2. Settings: Permissions, usage stats
3. Responsive: Touch gestures
4. Polish: Network indicator, loading states

---

## Technical Notes

### WebSocket Mock
Since we don't have a real backend, implement a mock WebSocket:
```typescript
// Use setInterval to simulate real-time updates
// Dispatch fake events every 2-5 seconds
```

### Data Export
All export functions should:
- Use `URL.createObjectURL(blob)` for download
- Include timestamp in filename
- Be JSON format for data, CSV for metrics

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Features remaining | 0 |
| Build errors | 0 |
| TypeScript errors | 0 |
| Mobile responsive | All pages |

---

## Next Action

Proceed with P0 items (WebSocket, Copy/Edit message, Real-time activity, Backup/Restore)