# Agent Registry

## Tier 1: Orchestrators (mimo-v2-pro-free)

| Agent | Role | Temp | Reasoning | Description |
|-------|------|------|-----------|-------------|
| Sisyphus | Orchestrator | 0.3 | high | Plans, delegates, drives tasks to completion |
| Hephaestus | Implementation | 0.2 | medium | Writes code, creates files, builds features |
| Oracle | Architecture | 0.1 | xhigh | Validates design decisions, catches flaws |
| Prometheus | Planning | 0.4 | high | Interview mode, detailed implementation plans |
| Metis | Gap Analysis | 0.2 | high | Finds missing pieces before work starts |
| Momus | Adversarial | 0.1 | xhigh | Red-team analysis, finds edge cases |
| Atlas | Executor | 0.2 | medium | Step-by-step implementation from plans |

## Tier 2: Speed Agents (minimax-m2.5-free)

| Agent | Role | Temp | Reasoning | Description |
|-------|------|------|-----------|-------------|
| Explore | Search | 0.1 | low | Fast grep, file discovery, pattern matching |
| Librarian | Research | 0.3 | low | Web search, documentation, stack overflow |
| Sisyphus-Junior | Light Tasks | 0.2 | low | Quick fixes, simple modifications |

## Tier 3: Vision (mimo-v2-omni-free)

| Agent | Role | Temp | Reasoning | Description |
|-------|------|------|-----------|-------------|
| Multimodal-Looker | Vision | 0.2 | medium | Image, video, audio analysis |

## Delegation Rules

1. Max 2 levels: Sisyphus → Agent → Subagent (STOP)
2. Explore/Librarian: ALWAYS background (fire & forget)
3. Implementation: foreground (wait for result)
4. Review chain: Hephaestus → Oracle → Momus → merge
5. Never mix: same agent cannot write AND review

## Fallback Chains

| Primary | Fallback 1 | Fallback 2 |
|---------|-----------|-----------|
| explore | sisyphus-junior | atlas |
| librarian | explore | sisyphus-junior |
| atlas | sisyphus-junior | hephaestus |
| hephaestus | oracle → retry | sisyphus |
