# Skill Template

> **Purpose**: Standard format for creating agent skills in `.agent/skills/[skill-name]/SKILL.md`.
> **Usage**: Create a directory under `.agent/skills/`, then add a `SKILL.md` file following this format.

---

## YAML Frontmatter (Required)

Every skill **must** begin with YAML frontmatter enclosed in `---` delimiters:

```yaml
---
name: [skill-name]
description: [One-line description of what this skill does]
argument-hint: "[example invocation]"
allowed-tools:
  - Bash
  - Read
  - Write
auto-invoke: false
model: default
user-invocable: true
---
```

### Frontmatter Fields

| Field | Required | Description |
|:---|:---|:---|
| `name` | ✅ | Unique skill identifier (kebab-case, e.g., `deep-research-loop`) |
| `description` | ✅ | Short description shown in skill listings |
| `argument-hint` | Optional | Example usage pattern (e.g., `"analyze <topic>"`) |
| `allowed-tools` | Optional | Which tools this skill may use (`Bash`, `Read`, `Write`, `Search`) |
| `auto-invoke` | Optional | If `true`, the agent loads this skill automatically when context matches |
| `model` | Optional | LLM model override |
| `user-invocable` | Optional | If `true`, user can trigger directly; if `false`, agent-only |

---

## Skill Body

### Title & Description

```markdown
# [Skill Display Name]

[2-3 sentence description of what this skill does and why it exists.]
```

### Triggers

```markdown
## Triggers

[Natural language patterns that should activate this skill]

- "[trigger phrase 1]"
- "[trigger phrase 2]"
- "[trigger phrase 3]"
```

### Core Mechanics

```markdown
## Core Mechanics

1. [Step 1: What the skill does first]
2. [Step 2: Processing / analysis]
3. [Step 3: Output / deliverable]
```

### Reference Paths

```markdown
## Reference Paths

- [Link to related protocols, scripts, or documentation]
```

---

## Example: Minimal Skill

```markdown
---
name: red-team-review
description: Adversarial review of plans, code, or strategies. Finds flaws before they become failures.
argument-hint: "red team <plan or decision>"
allowed-tools:
  - Read
  - Write
auto-invoke: false
model: default
user-invocable: true
---

# Red Team Review

An adversarial analysis framework that systematically attacks assumptions, identifies failure modes, and stress-tests plans before execution.

## Triggers

- "What could go wrong with this?"
- "Red team this plan"
- "Find the flaws"
- "Pre-mortem"

## Core Mechanics

1. **Identify Assumptions**: Extract all implicit and explicit assumptions from the plan.
2. **Attack Surface Mapping**: For each assumption, generate 2-3 failure scenarios.
3. **Probability Assessment**: Estimate likelihood and impact of each failure.
4. **Mitigation Proposals**: For high-risk failures, propose defensive actions.
5. **Verdict**: Summarize with a Go / No-Go / Conditional recommendation.

## Output Format

| Assumption | Attack Vector | Likelihood | Impact | Mitigation |
|:---|:---|:---|:---|:---|
| [Assumption] | [How it fails] | Low/Med/High | Low/Med/High | [Fix] |

## Reference Paths

- `.agent/skills/red-team-review/SKILL.md`
- `examples/protocols/decision/75-synthetic-parallel-reasoning.md`
```

---

## Directory Structure

A skill lives in its own directory under `.agent/skills/`:

```
.agent/skills/
└── my-skill/
    ├── SKILL.md          # Required: Main instruction file
    ├── scripts/          # Optional: Helper scripts
    ├── examples/         # Optional: Reference implementations
    └── resources/        # Optional: Additional files or assets
```

## Conventions

1. **Directory naming**: Use kebab-case matching the `name` field (e.g., `deep-research-loop/`)
2. **SKILL.md is mandatory**: The agent discovers skills by scanning for `SKILL.md` files
3. **Self-contained**: A skill should work with only the information in its directory
4. **Single responsibility**: One skill = one capability. Compose complex behaviors by chaining skills
5. **Tagging**: End with relevant tags for indexing by `generate_skill_index.py`

---

## Tagging

# skill #template #agent-architecture
