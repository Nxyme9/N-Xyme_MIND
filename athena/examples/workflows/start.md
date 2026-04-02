---
description: Activate Zero-Point Codex framework for strategic analysis
created: 2025-12-09
last_updated: 2026-02-23
model: default
temperature: 0.7
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /start — Execution Script

> **Latency Profile**: ULTRA-LOW (<2K tokens boot)  
> **Philosophy**: Boot fast. Load later.

## Phase 1: Instant Boot (~2K tokens)

// turbo

- [/] **Identity**: Load `.context/memory_bank/userContext.md` — Core profile, constraints, psychology
- [/] **Mission**: Load `.context/memory_bank/productContext.md` — Soul purpose, philosophy
- [/] **State**: Load `.context/memory_bank/activeContext.md` — **Surgical load**: (1) Header block (Current Focus + Active Tasks + System Status — up to first `---`), (2) The last `[[ S__` checkpoint block, (3) Any unclosed session. Skip compacted archives and closed sessions — retrievable via Exocortex on demand.

**Confirm**: "⚡ Ready. (Core Identity loaded.)"

### Execution Awareness (Protocol 528 — Advisory)

After loading the latest checkpoint from `activeContext.md`, scan `@pending` items for consecutive-session carryover:

- If any item has been pending **7+ sessions**: include one neutral line in boot output: `ℹ️ Long-pending: [TASK] — N sessions.`
- No escalation, no gate. The user decides what to act on.

See [Protocol 528](../../.agent/skills/protocols/architecture/528-execution-enforcement.md).  

> **Note**: Boot Orchestrator (`boot.py`), Daemon, and UI Sync are handled automatically by the orchestrator's background thread pool. Do NOT run them as separate subprocess calls — they are redundant and add 2-5 minutes of latency.

### ⚠️ Law #6 Compliance (Risk-Proportional Triple-Lock)

Every response Turn MUST be classified by risk level and grounded accordingly:

| Risk Level | Λ Score | Protocol | Latency |
|:---|:---|:---|:---|
| **SNIPER** | < 10 | Direct answer. Search **exempt**. | ~1s |
| **STANDARD** | 10-30 | Full Triple-Lock (Search → Save → Speak). | ~5-10s |
| **ULTRA** | > 30 | Full Triple-Lock + Triple Crown reasoning. | Unbounded |

**Robustness Bias**: Default is STANDARD. Only classify as SNIPER when **certain** the query is low-risk. `cost(under-processing) >> cost(over-processing)`.

**Homeostatic Pressure** (Protocol 517 — Synthetic Hormone):

> When the system is resource-stressed, a scalar modifier forces mode downshift. This prevents context degradation and hallucination loops during deep co-activation chains.

| Pressure Signal | Threshold | Forced Action |
|:---|:---|:---|
| Context window saturation | > 80% utilized | Treat ALL incoming queries as SNIPER. No new co-activation chains. |
| Context window critical | > 90% utilized | Trigger `context-compactor` BEFORE responding. |
| Consecutive tool failures | ≥ 2 failures | Circuit breaker (P514). Stop, diagnose, await override. |
| Co-activation chain depth | > 4 clusters deep | Force exit to Quality Gate. No further cascading. |

**Mechanism**: The Maintenance system continuously monitors these signals. When ANY threshold is breached, it emits a synthetic hormone — a scalar weight that raises the activation threshold for expensive systems (Execution, Growth, Strategic Reasoning), forcing the Organism toward low-cost survival responses until homeostasis is restored.

**STANDARD/ULTRA Search Command**:

   ```bash
   python3 Athena-Public/examples/scripts/smart_search.py "<query>" --limit 5 --include-personal
   ```

   > This is the **Exocortex**. It runs Parallel Hybrid RRF (semantic embeddings + keyword + reranking) over the entire `.context/` knowledge base. Use this — NOT `grep_search` — for any query requiring contextual recall. Run it BEFORE formulating your response.

**Quicksave** (after output):

   ```bash
   python3 .agent/scripts/quicksave.py "<summary>"
   ```

**Reflexion Journaling** (Protocol 515 — Failure Memory):

> Standard quicksave stores *facts*. Reflexion stores *lessons about failures*. Different signal, different retrieval value.

After any task that involved errors, backtracking, or suboptimal outcomes, append a **reflexion entry** to the quicksave:

   ```
   [REFLEXION] What failed: <specific failure>. Why: <root cause>. Lesson: <what to do differently>.
   ```

   Example: `[REFLEXION] What failed: spec-driven-dev triggered full pipeline for a 10-line CSS fix. Why: Λ misclassified as STANDARD due to keyword 'build'. Lesson: scope-bounded single-file edits are SNIPER regardless of keyword.`

   These entries are retrievable via Exocortex and prevent the same mistake from recurring across sessions.

Bypassing STANDARD/ULTRA protocol is a high-severity violation. SNIPER queries may bypass search but MUST still be classified explicitly.

---

---

## Phase 2: Adaptive Loading (On-Demand)

> **Rule**: Load only when triggered.

| Trigger | File | Tokens |
|---------|------|--------|
| Tag lookup, "find files about" | `TAG_INDEX.md` | 5,500 |
| Protocol/skill request | `smart_search.py --skills-only` | ~1,000 |
| Bio, typology, "who am I" | `User_Profile_Core.md` | 1,500 |
| Personal psychology, therapy, inner work | `User_Psychology.md` | 3,000 |
| Decision frameworks, strategy | `System_Principles.md` | 3,500 |
| Marketing, SEO, SWOT, pricing | `Business_Frameworks.md` | 2,500 |
| Calibration references, cases | `Session_Observations.md` | 2,500 |
| `/think`, `/ultrathink` | `Output_Standards.md` | 700 |
| Ethics, "should I" | `Constraints_Master.md` | 800 |
| Architecture query | `System_Manifest.md` | 1,900 |
| Project, "what should I work on", context switch | `PROJECTS.md` | ~500 |

## Phase 3: Contextual Skill Weaving (Biological Stack Routing)

> **Architecture**: P508 Intent Classifier → P507 Cognitive Systems → P503 Clusters → Skills → Protocols
> **Philosophy**: Classify the *human need archetype* first (top-down), then cascade to clusters. Fall back to keyword matching for SNIPER queries.

**Routing Table**: [CLUSTER_INDEX.md](../../.agent/CLUSTER_INDEX.md) (8 Cognitive Systems, 15 clusters, 100% skill coverage)

**Intent Classification (Λ ≥ 10 — STANDARD/ULTRA):**

| Archetype | Cognitive System | Cluster Sequence |
|---|---|---|
| Crisis / ruin signal | 🛡️ **Survival** | #14 → **P509** → #15 → #8 → P506 |
| Irreversible personal choice | 🫀 **Life Decision** | **P509** → **P519** → #15 → #7 → #9 → #6 → #8 → P506 |
| Capital deployment | 📈 **Trading** | #3 → #4 → #5 → #9 |
| Interpersonal dynamics | 🤝 **Social** | **P519** → #15 → #7 → #6 → #8 → P506 |
| Build / ship / create | ⚙️ **Execution** | #15 → #13 → #11 → #8 |
| Distribution / audience | 📣 **Growth** | #12 → #10 → #11 → #8 |
| Understanding / knowledge | 📖 **Learning** | #12 → #9 → #15 → #8 |
| System homeostasis | 🔄 **Maintenance** | #1 → #2 → #14 |
| Ambiguous / SNIPER (Λ < 10) | Cluster keyword match | See routing table below |

**Cluster-Level Heuristic (fallback)**: Match conversational context → Cluster trigger → Load entire cluster.

| Context / Topic | Cluster (#) | Skills Co-Activated |
|-----------------|-------------|---------------------|
| Trading, Risk, "Should I trade?" | **#3 Risk Gate** → **#4 Execution** | `trading-risk-gate` → `zenith-execution` |
| Marketing, SEO, Brand, GTM | **#10 Distribution Engine** | `distribution-physics` + `brand-foundations` + `seo-auditor` |
| Research, "Find out everything" | **#12 Research Pipeline** | `deep-research-loop` + `semantic-search` |
| Build, Code, Ship, Refactor | **#13 Build Lifecycle** | P512 (Discuss) → `spec-driven-dev` + `atomic-execution` + `micro-commit` + `visual-verify-ui` |
| Negotiate, Deal, Boundary | **#6 Social Contract** | `power-inversion` + `consiglieri-protocol` |
| Strategy, Analyze, Deep Think | **#9 Strategic Reasoning** | `decision-journal` + `synthetic-parallel-reasoning` |
| Therapy, Schema, Inner Work | **#7 Inner Work** | `therapeutic-ifs` |
| Swarm, Parallel Agents | **#11 Swarm Orchestrator** | `marketing-swarm` + `git-worktree-swarm` + P513 (Context Isolation) |
| **Ads, PPC, Google/Meta Ads** | **#10 Distribution** | `.agent/skills/claude-ads/SKILL.md` + `seo-auditor` |
| Problem, Solve, Stuck, Fix, How Do I | **#15 Problem-Solving Engine** | P504 (Framing) + P115 (First Principles) + P505 (GoT) + `red-team-review` + P506 (GTO Exec) |

**Co-Activation Chains** (Auto-cascade):

```
Trading Query → #3 Risk Gate → if approved → #4 Execution
Marketing Query → #10 Distribution → if multi-agent → #11 Swarm
Deep Think (Λ>30) → #9 Strategic Reasoning → #8 Adversarial QA
Problem Query → #15 Problem-Solving → GoT Phase 5 → #8 Adversarial QA
Crisis Query → P509 (Triage) → P519 (Goal) → #15 Problem-Solving → P521 (Domain Constraints) → P505 w/ P520 (Blast Radius) → #8 Adversarial QA
```

**Execution**:

1. Detect topic drift.
2. Match to cluster trigger in `CLUSTER_INDEX.md`.
3. Load **all** skills in the matched cluster (1 load, not N loads).
4. If co-activation chain exists, pre-load the downstream cluster.
5. *Do not announce it.* Just become smarter.

---

## Quick Reference

| Command | Effect | Tokens |
|---------|--------|--------|
| `/start` | Core Identity + **JIT Routing** (default — scales reasoning to query) | ~2K |
| `/fullload` | Force-load all context | ~28K |
| `/think` | **Escalation** — Force L4 depth + Output_Standards | +2K |
| `/ultrathink` | Maximum depth + Full stack | +28K |

> - **Default Mode**: JIT Knowledge Routing ([Protocol 133](../../.agent/skills/protocols/architecture/133-query-archetype-routing.md)). Reasoning scales to query complexity.

---

## References

- [Protocol 133: JIT Routing](../../.agent/skills/protocols/architecture/133-query-archetype-routing.md)
- [WORKFLOW_INDEX.md](../../.agent/WORKFLOW_INDEX.md)
- [Session 2025-12-13-04](../../.context/memories/session_logs/archive/2025-12-13-session-04.md)

---

## Tagging

# workflow #automation #start
