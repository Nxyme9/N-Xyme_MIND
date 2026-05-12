---
stepsCompleted: []
inputDocuments:
  - "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/_bmad-output/planning-artifacts/prd.md"
workflowType: 'architecture'
---

# Architecture Decision Document: N-Xyme MIND Anthropic Leak Integration

**Project:** N-Xyme MIND Anthropic Leak Integration  
**Date:** 2026-04-27  
**Architect:** N-Xyme System  
**Status:** Draft

---

## 1. Architecture Principles

### 1.1 Design Principles

| Principle | Application |
|-----------|--------------|
| **Extensibility** | New skills and tools can be added without modifying core |
| **Composability** | Skills and tools combine to form complex workflows |
| **Backward Compatibility** | Existing N-Xyme APIs remain stable |
| **Layered Architecture** | Clear separation between presentation, orchestration, agent, MCP, skill, tool layers |

### 1.2 Architecture Patterns

- **Step-file Architecture:** Used for BMAD workflows (disciplined execution)
- **Agent Tool Pattern:** Subagent spawning with memory snapshots
- **Task State Machine:** CRUD operations for task lifecycle
- **Skill Loader Pattern:** Dynamic skill registration and execution

---

## 2. System Architecture

### 2.1 Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                      │
│  [TUI] [Web Dashboard] [CLI Commands (101)]               │
├─────────────────────────────────────────────────────────────┤
│                    ORCHESTRATION LAYER                      │
│  [BMAD Workflows: brainstorming, prd, sprint, dev, review] │
├─────────────────────────────────────────────────────────────┤
│                      AGENT LAYER                            │
│  [Sisyphus] [Hephaestus+] [Oracle] [Explore] [Librarian]  │
│  [NEW: verificationAgent, debugAgent, schedulerAgent]    │
├─────────────────────────────────────────────────────────────┤
│                       MCP LAYER                             │
│  [nx-learning] [nx-intelligence] [nx-memory] [nx-session+] │
│  [nx-brain] [nx-orchestration] [NEW: nx-analytics]      │
│  [NEW: nx-voice] [NEW: nx-mcp-manager]                  │
├─────────────────────────────────────────────────────────────┤
│                      SKILL LAYER                            │
│  [NEW: /batch, /remember, /debug, /verify, /simplify]   │
│  [NEW: /stuck, /loop, /skillify, /keybindings, /updateConfig]│
├─────────────────────────────────────────────────────────────┤
│                      TOOL LAYER                              │
│  [BashTool] [FileTool] [GrepTool] [LSPTool]               │
│  [NEW: AgentTool, Task*, Team*, Schedule*, Remote*]     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Layer | Component | Responsibility |
|-------|-----------|-----------------|
| Presentation | TUI | User interaction via OpenCode |
| Presentation | Web Dashboard | Visual status monitoring |
| Presentation | CLI Commands | Command-line interface |
| Orchestration | BMAD Workflows | Method execution, phase management |
| Agent | Sisyphus | Primary orchestration |
| Agent | Hephaestus | Implementation (enhanced with AgentTool) |
| Agent | Oracle | Architecture review |
| Agent | NEW Agents | Verification, debugging, scheduling |
| MCP | nx-session | Session pools + task management |
| MCP | nx-memory | Memory storage and retrieval |
| MCP | nx-learning | Q-Learning routing |
| MCP | nx-analytics | Usage tracking (NEW) |
| MCP | nx-voice | Speech-to-text (NEW) |
| Skill | Skill Loader | Dynamic skill registration |
| Skill | Individual Skills | /batch, /remember, etc. |
| Tool | Tool Registry | Tool discovery and execution |
| Tool | AgentTool | Subagent spawning |

---

## 3. Integration Points

### 3.1 AgentTool Integration

```
Hephaestus (existing)
    ↓ extends
Hephaestus+ (with AgentTool)
    ├── spawn_subagent(memory_snapshot)
    ├── list_subagents()
    ├── kill_subagent(subagent_id)
    └── built_in_subagents: [explore, plan, verify, general]
```

### 3.2 Task Management Integration

```
nx-session MCP (existing)
    └── Extended with:
        ├── POST /tasks/create
        ├── GET /tasks/list
        ├── POST /tasks/{id}/stop
        ├── PATCH /tasks/{id}
        ├── GET /tasks/{id}
        └── GET /tasks/{id}/output
```

### 3.3 Skill Layer Integration

```
Skill Loader (new)
    ├── register_skill(skill_name, skill_path)
    ├── execute_skill(skill_name, args)
    ├── list_skills()
    └── Skill Format (BMAD):
        ├── skill.yaml
        ├── workflow.md
        └── steps-*/
```

---

## 4. Data Flow Diagrams

### 4.1 Skill Execution Flow

```
User: "/batch spawn 5 agents"
    ↓
CLI Layer (commands.ts)
    ↓
Skill Loader → /batch skill
    ↓
AgentTool.spawn_subagent() × 5 (parallel)
    ↓
Each subagent → Hephaestus instance
    ↓
Results aggregated → Skill output
    ↓
User receives aggregated results
```

### 4.2 Task Lifecycle Flow

```
User: "create task: build feature X"
    ↓
CLI → TaskCreateTool
    ↓
nx-session MCP → POST /tasks/create
    ↓
Task State Machine: [pending → running]
    ↓
Task executes → Hephaestus
    ↓
[completed/failed] → User notified
```

---

## 5. API Contracts

### 5.1 AgentTool API

```typescript
interface AgentTool {
  spawn_subagent(config: SubagentConfig): SubagentId
  list_subagents(): Subagent[]
  kill_subagent(id: SubagentId): void
  get_subagent_status(id: SubagentId): Status
}

interface SubagentConfig {
  name: string
  memory_snapshot?: MemorySnapshot
  built_in_type?: 'explore' | 'plan' | 'verify' | 'general'
  max_duration_ms?: number
}
```

### 5.2 Task Management API

```typescript
interface TaskAPI {
  create_task(req: CreateTaskRequest): TaskId
  list_tasks(): Task[]
  get_task(id: TaskId): TaskDetail
  update_task(id: TaskId, updates: TaskUpdate): void
  stop_task(id: TaskId): void
  get_task_output(id: TaskId): Output
}

interface Task {
  id: TaskId
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  created_at: timestamp
  updated_at: timestamp
  result?: any
}
```

### 5.3 Skill API

```typescript
interface SkillLoader {
  register_skill(skill: SkillDefinition): void
  execute_skill(name: string, args: SkillArgs): Promise<SkillResult>
  list_skills(): SkillInfo[]
}

interface SkillDefinition {
  name: string
  description: string
  actions: SkillAction[]
}
```

---

## 6. Security Architecture

### 6.1 Security Layers

| Layer | Security Mechanism |
|-------|-------------------|
| MCP | Authentication (McpAuthTool) |
| Bridge | JWT authentication |
| OAuth | External service auth |
| Skills | Sandboxed execution |

### 6.2 Security Requirements

- All MCP communications authenticated
- Bridge system uses JWT with expiration
- OAuth flow for external integrations
- Skills run in isolated context

---

## 7. Deployment Architecture

### 7.1 Component Deployment

```
┌─────────────────────────────────────────────┐
│              N-Xyme MIND Server             │
│  ┌─────────────────────────────────────┐  │
│  │ MCP Layer (Python/FastAPI)          │  │
│  │ - nx-session (port 3000)            │  │
│  │ - nx-learning (port 3000)           │  │
│  │ - nx-memory (port 3000)            │  │
│  │ - nx-analytics (NEW)                │  │
│  │ - nx-voice (NEW)                   │  │
│  └─────────────────────────────────────┘  │
│  ┌─────────────────────────────────────┐  │
│  │ Skill Layer (TypeScript)            │  │
│  │ - skill loader                      │  │
│  │ - 18 bundled skills                │  │
│  └─────────────────────────────────────┘  │
│  ┌─────────────────────────────────────┐  │
│  │ Tool Layer (TypeScript)             │  │
│  │ - 44 tool directories              │  │
│  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 7.2 Scalability

- **Horizontal:** Multiple MCP instances
- **Vertical:** GPU-accelerated inference
- **Caching:** FAISS for memory retrieval

---

## 8. Quality Assurance

### 8.1 Testing Strategy

| Test Type | Coverage | Tool |
|-----------|----------|------|
| Unit | Skills, Tools | pytest/jest |
| Integration | MCP APIs | Postman |
| E2E | Full workflows | Playwright |
| Performance | Load testing | k6 |

### 8.2 Quality Gates

1. **Architecture Review:** `bmad-check-implementation-readiness`
2. **Code Review:** `bmad-code-review`
3. **Test Coverage:** >80% for new features

---

## 9. Migration Plan

### 9.1 Phase Migration

| Phase | Components | Migration Strategy |
|-------|------------|---------------------|
| Phase 1 | AgentTool, Task CRUD | Blue-green deployment |
| Phase 2 | Skills | Feature flags |
| Phase 3 | Services | Gradual rollout |

### 9.2 Rollback Plan

- Each feature behind feature flag
- Instant rollback via config change
- Database migrations backward-compatible

---

## 10. Open Questions & Decisions

| Question | Decision Needed | Resolution |
|----------|-----------------|-------------|
| Voice provider? | STT backend | Defer - use mock initially |
| Bridge implementation? | Cross-editor | Defer to Phase 2 |
| 101 commands priority? | Command order | Top 20 first |

---

**Architecture Status:** Draft  
**Document Owner:** N-Xyme System  
**Next:** `bmad-check-implementation-readiness`