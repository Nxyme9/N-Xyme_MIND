# CATALYST Integration Guide

> **Last Updated**: 2026-04-03 | **Status**: Ready

---

## Overview

BMAD CATALYST workflows are the strategic planning engine of N-Xyme_MIND. They provide structured approaches for:
- Full pipeline orchestration (bmad-catalyst-chain)
- Memory integration (bmad-memory)
- Error resilience patterns (bmad-resilience)

---

## Available Workflows

### 1. bmad-catalyst-chain

**Purpose**: Full pipeline orchestrator — runs BMAD phases in sequence with memory, review, and error handling.

**Location**: `_bmad/catalyst/workflows/bmad-catalyst-chain/`

**Phases**:
1. Memory Recall — Check Graphiti for context
2. BMAD Analysis — brainstorm → market → domain
3. BMAD Planning — product brief → PRD
4. BMAD Solutioning — architecture → sprint plan
5. Bridge — Sprint plan → Athena queue
6. Execution — Agents execute queued tasks
7. Review — Oracle + Momus validate
8. Memory Consolidate — Store learnings to Graphiti

**Usage**:
```bash
# Load the skill and run
cd _bmad/catalyst/workflows/bmad-catalyst-chain
cat steps/step-01-detect-phase.md
```

---

### 2. bmad-memory

**Purpose**: Memory integration with Graphiti for episodic recall.

**Location**: `_bmad/catalyst/workflows/bmad-memory/`

**Features**:
- Context injection
- Session memory
- Cross-session knowledge graph

---

### 3. bmad-resilience

**Purpose**: Error handling patterns and recovery workflows.

**Location**: `_bmad/catalyst/workflows/bmad-resilience/`

**Features**:
- Retry patterns
- Fallback chains
- Circuit breakers

---

## Integration with OpenCode

### As Skills

BMAD workflows can be loaded as skills in OpenCode:

1. Copy workflow to `~/.opencode/skills/`
2. Update `opencode.json` to include skill path
3. Use in prompts: "Use bmad-catalyst-chain workflow"

### As Reference

For now, BMAD workflows are reference material. To use:

1. Read the SKILL.md in each workflow
2. Follow the phase steps manually
3. Use output as input to other agents

---

## Quick Start

```bash
# List available CATALYST workflows
ls -la _bmad/catalyst/workflows/

# View catalyst-chain workflow
cat _bmad/catalyst/workflows/bmad-catalyst-chain/SKILL.md

# View memory workflow  
cat _bmad/catalyst/workflows/bmad-memory/SKILL.md

# View resilience workflow
cat _bmad/catalyst/workflows/bmad-resilience/SKILL.md
```

---

## Future Integration

Planned: Create OpenCode command to invoke CATALYST workflows:
```bash
opencode --catalyst bmad-catalyst-chain
```

---

*CATALYST Integration v1.0 | N-Xyme_MIND*