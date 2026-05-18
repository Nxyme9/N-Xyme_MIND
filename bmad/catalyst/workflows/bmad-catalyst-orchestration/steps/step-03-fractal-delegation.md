# Step 3: Fractal Delegation

**Goal:** Execute fractal delegation with depth tracking for multi-agent workflows

---

## Fractal Delegation Pattern

Fractal delegation spawns sub-agents recursively with depth tracking to handle complex multi-agent workflows.

### Delegation Depth Levels

- **Depth 0 (Root):** Main orchestration agent (Sisyphus)
- **Depth 1:** Primary sub-agents (Hephaestus, Oracle, Explore)
- **Depth 2:** Secondary agents spawned by primary agents
- **Depth 3:** Tertiary agents (limited, for complex tasks only)
- **Depth 4:** Maximum allowed - stop delegation here

### Max Depth Rules
- L1-L2 tasks: max depth 1
- L3 tasks: max depth 2
- L4 tasks: max depth 3
- L5 tasks: max depth 4 (with explicit approval)

---

## Execution

<step n="3.1" goal="Analyze task complexity">
<action>Assess task complexity (L1-L5)</action>
<action>Determine max delegation depth based on complexity</action>
<action>Store as {{max_depth}}</action>
</step>

<step n="3.2" goal="Identify sub-tasks">
<action>Decompose task into independent work units</action>
<action>Identify dependencies between units</action>
<action>Group independent units for parallel execution</action>
</step>

<step n="3.3" goal="Spawn sub-agents">
<action>For each work unit, determine appropriate agent</action>
<action>Spawn agents with depth tracking: current_depth + 1</action>
<action>Track all spawned agents in {{delegation_tree}}</action>
<action>Set timeout based on task complexity</action>
</step>

<step n="3.4" goal="Manage agent lifecycle">
<action>Monitor agent completion status</action>
<action>Handle timeouts and failures</action>
<action>Collect results from completed agents</action>
<action>Aggregate results for parent agent</action>
</step>

<step n="3.5" goal="Track delegation depth">
<action>Maintain depth counter throughout workflow</action>
<action>Block delegation beyond max_depth</action>
<action>Log all delegation decisions to .sisyphus/delegation-log.jsonl</action>
</step>

---

## Agent Selection Matrix

| Task Type | Primary Agent | Depth | Parallel |
|-----------|---------------|-------|----------|
| Implementation | Hephaestus | 1-3 | false |
| Code review | Oracle | 1-2 | true |
| Research | Explore | 1-2 | true |
| Documentation | bmad-document-project | 1-2 | false |
| QA/Tests | bmad-qa-generate-e2e-tests | 1-2 | false |
| Planning | Prometheus | 1-2 | false |
| Architecture | Oracle | 2-3 | false |

---

## Output

- **delegation_tree:** {depth: [agents], ...}
- **delegation_results:** {agent_id: {status, output, duration_ms}}
- **max_depth_reached:** number
- **blocked_delegations:** [list of blocked attempts with reason]