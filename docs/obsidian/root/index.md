# N-Xyme MIND System

Personal AI coding workspace powered by OpenCode + OMO multi-agent orchestration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        N-Xyme MIND                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │ Orchestration │   │ Intelligence  │   │ Memory Core  │            │
│  │   Layer     │   │   Layer      │   │   Layer      │            │
│  │             │   │              │   │              │            │
│  │ • Agent Loop │   │ • Routing    │   │ • Storage    │            │
│  │ • Catalyst   │   │ • Circuit    │   │ • Retrieval  │            │
│  │ • Triggers   │   │   Breakers   │   │ • Cognitive  │            │
│  │ • Workflows  │   │ • Fallback   │   │   Processes  │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │Learning Eng.│   │Infrastructure│   │  Local LLM  │            │
│  │   Layer     │   │   Layer      │   │   Layer     │            │
│  │             │   │              │   │              │            │
│  │ • Q-Learning│   │ • Proxy      │   │ • GGUF Infra│            │
│  │ • Meta-Lear.│   │ • Spine      │   │ • Inference │            │
│  │ • Routing   │   │ • Monitoring │   │ • Tool Call │            │
│  │ • A/B Test  │   │ • Resilience │   │ • Benchmark │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
│                                                                  │
│  ┌─────────────┐                                                │
│  │    Data     │   (Models, schemas, configurations)            │
│  └─────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## System Configuration

- **Frontend**: OpenCode TUI (v1.3.13)
- **Agent Layer**: OMO v3.14.0 (11 agents, 9 categories)
- **MCP Layer**: 4 global MCPs (sequential-thinking, memory, context7, filesystem)
- **Engine**: CATALYST (234 Python modules) + athena framework
- **VPN**: rotator.py with 9 provider plugins
- **Local Inference**: GGUF llama-server with GPU acceleration

## Agents

| Agent | Model | Role |
|-------|-------|------|
| Sisyphus | minimax-m2.5-free | Primary orchestrator - plans, delegates, drives tasks |
| Catalyst | minimax-m2.5-free | Master orchestrator - FLOW/FRICTION state detection |
| Hephaestus | minimax-m2.5-free | Implementation - writes code, creates files |
| Oracle | minimax-m2.5-free | Architecture review - validates design decisions |
| Explore | minimax-m2.5-free | Codebase search - grep, file discovery |
| Librarian | minimax-m2.5-free | External research - web search, docs |
| Prometheus | minimax-m2.5-free | Strategic planning - interview mode |
| Metis | minimax-m2.5-free | Gap analysis - finds missing pieces |
| Momus | minimax-m2.5-free | Adversarial review - red-team analysis |
| Atlas | minimax-m2.5-free | Plan executor - step-by-step implementation |
| Sisyphus-Junior | minimax-m2.5-free | Light tasks - quick fixes |
| Multimodal-Looker | minimax-m2.5-free | Vision agent - image/video/audio |

## Layers

- [[orchestration/index|Orchestration]] - Agent loops, workflows, triggers
- [[intelligence/index|Intelligence]] - Routing, circuit breakers
- [[memory_core/index|Memory Core]] - Storage, retrieval, cognitive processes
- [[learning_engine/index|Learning Engine]] - RL, meta-learning
- [[infrastructure/index|Infrastructure]] - Proxies, spine, monitoring
- [[local_llm/index|Local LLM]] - GGUF inference
- [[data/index|Data]] - Data models

## Quick Start

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source env.sh
bash n-xyme-mind.sh
```

## Health Checks

```bash
bash bin/health-l0-blink.sh  # <1s pre-flight
bash bin/health-l1-pulse.sh  # <10s service check
bash bin/health-l2-vitals.sh # <60s deep integrity
```