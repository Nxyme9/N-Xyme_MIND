---
description: Maximum depth mode — v4.1 (HITL Optional Bypass)
created: 2025-12-12
last_updated: 2026-03-02
---
# /ultrathink — Execution Script (v4.1)

> **Version**: 4.1 (HITL Optional Bypass)
> **Refactored**: 2026-03-02 (Added Manual Gemini Sandbox execution path)
> **Breaking Change**: Script execution is now *optional*, allowing users to execute the parallel tracks manually via the Gemini UI to save API credit costs. Single-pass essays within a single LLM context window are still a protocol violation.

---

> [!CAUTION]
> **ENFORCEMENT CONTRACT**: You MUST NOT write a single-pass essay. The entire point of `/ultrathink` is that reasoning happens across **multiple independent channels**, not inside a single LLM context window. A single LLM checking its own homework will hit a quality ceiling. However, the automated script execution is optional; you may orchestrate the tracks manually via the Human-in-the-Loop sandbox.

---

## When to Use

| Query Complexity | Workflow |
|------------------|----------|
| **Λ ≤ 30** | Direct answer. No workflow needed. |
| **Λ 31-60** | `/think` — Internal CoT only (no script). |
| **Λ > 60 or high-stakes** | **`/ultrathink`** — Internal CoT + mandatory parallel orchestrator. |

**Rule**: `/think` = deep reasoning within a single context window (cheap, fast).
`/ultrathink` = `/think` PLUS 4 parallel external tracks for adversarial cross-checking (expensive, slow, required)—either via automated API or manual user execution.

---

## Phase 1: Prime (Context Gathering)

1. **Semantic Search** (MANDATORY):

    ```bash
    python3 scripts/smart_search.py "<extract keywords from query>" --limit 5
    ```

    - Capture the top results. These become the `--context-file` input for Phase 2.

2. **Internal CoT** (MANDATORY):
    Before dispatching the orchestrator, perform the Deep Thought Protocol internally:
    - [ ] **Deconstruct**: Break request into atomic axioms.
    - [ ] **Lateral Prism**: Generate 3 distinct angles (e.g., Domain View, Risk View, First Principles View).
    - [ ] **Plan**: Draft step-by-step logic.
    - [ ] **Critical Review**: Hunt for hallucinations/flaws. Backtrack if found.
    - [ ] **Synthesis**: Combine the lateral views into a preliminary hypothesis.

3. **Build Context File** (MANDATORY):
    Write a context file to `/tmp/ultrathink_context.md` containing:
    - The preliminary hypothesis from step 2
    - Relevant semantic search results from step 1
    - Any active session state or user constraints that apply

---

## Phase 2: Execute (Parallel Orchestrator)

> [!IMPORTANT]
> **This parallel track execution is NOT optional.** However, the *method* of execution is. Ensure you and the user agree on the Option before proceeding.

### Option A: The Automated Orchestrator (High API Cost)

```bash
python3 scripts/parallel_orchestrator.py "<the user's query>" \
  --context-file /tmp/ultrathink_context.md \
  --output .context/state/ultrathink/ultrathink_$(date +%Y%m%d_%H%M%S).md \
  --json
```

**Wait for the script to finish.** Read the output file.

### Option B: The HITL Manual Sandbox (Zero API Cost)

If the user prefers to preserve API credits, use the Human-in-the-Loop (HITL) bypass.

1. Athena produces a structured synthesis prompt containing the 4 track prompts mapped to the `ultrathink_context.md`.
2. Athena places this large prompt inside a markdown `text` code block.
3. The user copies the text, pastes it into their native Gemini Advanced UI, and runs it natively.
4. The user pastes the Gemini output back into the Athena chat to feed the deposit phase.

---

## Phase 3: Deposit (Synthesis & Persistence)

1. **Read the output file** from Phase 2 (or the pasted user response if using Option B).
2. **Present to user**: Format the synthesis into a clean, structured response. Include:
   - The convergence score and number of iterations
   - Key points of agreement across tracks
   - Resolved conflicts
   - Risk integration from the Adversarial track
   - Final recommendation with confidence level
3. **Log**: Save the exchange for future reference.
4. **Auto-Document**: If the analysis produced a novel insight or framework, file it as a case study or protocol.

---

## Stability Controls (v4.1)

| Trigger | Action |
|---------|--------|
| **Convergence Score ≥ 85** | **OUTPUT**. (Adversarial Gate Passed) |
| **Iterations > 3** | **HALT**. (Cost Cap) |
| **Ruin Risk Detected** | **ESCALATE**. (Track B Veto — present risk to user immediately) |
| **Script fails to execute** | **REPORT**. (Do NOT simulate. Tell user the script failed and why.) |
| **User opts for Option B** | **GENERATE PROMPT**. (Produce HITL prompt and wait for pasted output.) |

---

## Tagging

`#workflow` `#safety` `#ultrathink` `#v4.1` `#parallel-orchestrator` `#hitl-bypass`
