# Multi-Machine Sync Patterns Research

Research conducted: April 2026

## 1. Existing Tools' Approaches

### Claude Code / Claude Sync

Claude Code handles multi-machine sync through several community tools and patterns:

| Tool | Approach | Source |
|------|----------|--------|
| **Claude Sync** (claude-sync.com) | Push/pull sessions between machines via cloud | [Claude Sync](https://claude-sync.com/) |
| **claude-session-sync** (GitHub) | MCP server for cross-machine session sync | [silverdolphin863/claude-session-sync](https://github.com/silverdolphin863/claude-session-sync) |
| **claude-cross-machine-sync** | Shell scripts for settings, memory, episodic memory | [robertogogoni/claude-cross-machine-sync](https://github.com/robertogogoni/claude-cross-machine-sync) |
| **Git Worktree Mode** | Parallel sessions via git worktrees | [Claude Code Worktrees Guide](https://claudefa.st/blog/guide/development/worktree-guide) |

**Key Insight**: Claude Code stores session data locally. No native cross-machine sync exists - community has built tools around this limitation.

### Cursor IDE

| Status | Details |
|--------|---------|
| **No Official Sync** | Users request feature; no native multi-machine support |
| **Workarounds** | Symlink to cloud storage (Dropbox/iCloud), git-versioned settings |
| **Team Sync** | Some settings sync via shared AI rules in team workspaces |

**Key Insight**: Cursor lacks session sync entirely. Settings sync is a requested feature since 2026.

---

## 2. Git-Based Sync Patterns

### Git Worktree Pattern

Best practice for parallel AI sessions on same machine:

```bash
# Create isolated worktree for each session
git worktree add /path/to/session-{id} -b session-{id}
```

**Advantages**:
- Complete isolation between sessions
- No file conflicts
- Each worktree has independent HEAD

**Source**: [Git Worktree Merge Conflicts in AI Agents](https://docs.bswen.com/blog/2026-03-12-git-worktree-merge-conflicts-agents)

### Conflict Prevention Strategies

| Strategy | Description |
|----------|-------------|
| **Linear History** | Prefer rebase over merge to prevent conflict branches |
| **Rerere** | Git's recorded re-resolution (`git config rerere.enabled true`) |
| **Topic Branches** | Each feature/task gets isolated branch |
| **File Locking** | Lock specific files during active work |

**Source**: [Conflict Resolution Patterns](https://www.grizzlypeaksoftware.com/library/conflict-resolution-patterns-and-strategies-gb8im62r)

### Recommended Git Workflow for AI Workspaces

1. **Main branch**: Production-ready code
2. **Session branches**: Each machine/session works on isolated branch
3. **Periodic merge**: Sync via PR/merge requests
4. **Rerere enabled**: Automates repeated conflict resolution

---

## 3. Conflict Resolution Strategies

### Three-Way Merge

Standard Git merge uses three-way merge:
- Common ancestor (base)
- Local changes (ours)
- Remote changes (theirs)

```bash
git merge --no-ff session-branch
# If conflicts: manual resolution + commit
```

### Git Rerere (Recorded Re-resolution)

**Benefit**: Remembers how you resolved conflicts, auto-applies on repeat:

```bash
git config rerere.enabled true
git rerere()
# On repeated conflict: git automatically applies previous resolution
```

### For AI Agent Systems

| Scenario | Resolution Strategy |
|----------|-------------------|
| Independent files | Auto-merge (no conflicts) |
| Same file, different sections | Auto-merge with concatenation |
| Same file, same lines | Require human review |
| Binary files | Last-write-wins |

---

## 4. Real-Time vs Periodic Sync

### Comparison

| Aspect | Real-Time | Periodic (Batch) |
|--------|-----------|------------------|
| **Consistency** | Eventual/Strong | Snapshot-based |
| **Complexity** | High (CRDT/OT required) | Low (file transfer) |
| **Network** | Continuous required | Intermittent OK |
| **Conflict Frequency** | Higher (concurrent edits) | Lower (sequential) |
| **Latency** | Seconds | Minutes/Hours |

### Technologies

**Real-Time Sync**:
- **CRDT** (Conflict-free Replicated Data Types) - Merge without conflicts
- **Operational Transform** - Google Docs approach
- **WebSocket** - Live connection

**Periodic Sync**:
- **Pull-based** - Client fetches when ready
- **Push-based** - Server pushes on schedule
- **Git-based** - Traditional push/pull model

### Source: [Real-Time Data Sync Architectures](https://www.askantech.com/real-time-data-sync-distributed-systems-crdt-operational-transform-event-sourcing/)

---

## 5. Recommended Patterns for N-Xyme_MIND

### Architecture Decision

Based on research, recommend **Git-Based Periodic Sync** with the following components:

```
┌─────────────────────────────────────────────────┐
│                  N-Xyme_MIND                    │
├─────────────────────────────────────────────────┤
│  Session Storage (JSON)                         │
│      ↓ push          pull ↓                     │
│  Git Repository (sync-branch)                  │
│      ↓ merge         push ↓                     │
│  Remote (GitHub/Gitea)                         │
└─────────────────────────────────────────────────┘
```

### Recommended Pattern

1. **Session Format**: JSON files in `sessions/` directory
2. **Sync Trigger**: Manual + periodic (on session end)
3. **Conflict Resolution**:
   - File-level isolation (each session = separate JSON)
   - For shared state: last-write-wins with timestamp
4. **Branching Model**:
   - `main`: Production state
   - `machines/{hostname}`: Per-machine branch
   - `sync`: Integration branch for merges

### Implementation Checklist

- [ ] Session JSON schema with timestamps
- [ ] Git-based sync script with push/pull
- [ ] Conflict detection (git status check)
- [ ] Merge strategy: prefer local or remote (configurable)
- [ ] Cleanup stale branches older than N days

---

## 6. References

### Tools
- Claude Sync: https://claude-sync.com/
- claude-session-sync: https://github.com/silverdolphin863/claude-session-sync
- claude-cross-machine-sync: https://github.com/robertogogoni/claude-cross-machine-sync

### Git Patterns
- Conflict Resolution Patterns: https://www.grizzlypeaksoftware.com/library/conflict-resolution-patterns-and-strategies-gb8im62r
- Git Worktree for AI Agents: https://docs.bswen.com/blog/2026-03-12-git-worktree-merge-conflicts-agents

### Sync Architectures
- Real-Time Sync Guide: https://www.askantech.com/real-time-data-sync-distributed-systems-crdt-operational-transform-event-sourcing/
- Batch vs Real-Time: https://intelligex.ai/blog/batch-vs-real-time-data-sync-which-is-right-for-your-business/

### Cursor Settings
- Sync Workarounds: https://dredyson.com/syncing-cursor-ide-settings-i-tested-4-methods-the-ultimate-comparison-guide/

---

*Research completed for Sprint 5: Multi-Machine Sync implementation*
