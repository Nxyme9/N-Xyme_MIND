---
type: system-knowledge
status: active
date: 2026-04-09
tags: [system, catalyst, agents, bmad, jarvis]
related: [[ARCHIVE_Overview], [N-XYME_MIND_Golden_Spine]]
rating: 10
---

# N-XYME CATALYST SYSTEM

## 1. AGENT DEFINITIONS (11 Specialized Agents)

| Agent | Role | Model | Responsibility |
|-------|------|-------|----------------|
| **Sisyphus** | Primary orchestrator | mimo-v2-pro-free | Delegates tasks |
| **Prometheus** | Plan builder | mimo-v2-pro-free | Creates implementation plans |
| **Hephaestus** | Implementation | mimo-v2-omni-free | Writes code, builds features |
| **Oracle** | Architecture review | mimo-v2-pro-free | Design decisions, Q&A |
| **Momus** | Adversarial review | mimo-v2-pro-free | Red-teaming, critical analysis |
| **Explore** | Codebase search | minimax-m2.5-free | Finds files, patterns |
| **Librarian** | External research | minimax-m2.5-free | Web search, docs |
| **Metis** | Pre-planning | mimo-v2-pro-free | Gap analysis |
| **Atlas** | Plan executor | minimax-m2.5-free | Executes plans step-by-step |
| **Sisyphus-Junior** | Trivial fixes | minimax-m2.5-free | Typos, version bumps |
| **Multimodal-looker** | Image/video | mimo-v2-omni-free | Visual content |

## 2. BMAD Workflow (4 Phases, 9 Roles)

### Phases
1. **Analysis** — research (domain/market/technical)
2. **Planning** — PRD, UX design
3. **Solutioning** — architecture, epics
4. **Implementation** — code, review, test

### Role Mappings
| BMAD Role | Catalyst Agent | Model |
|-----------|----------------|-------|
| analyst | oracle | mimo-v2-pro |
| architect | hephaestus | mimo-v2-pro |
| dev | hephaestus | mimo-v2-pro |
| pm | prometheus | mimo-v2-pro |
| sm | atlas | mimo-v2-pro |
| qa | sisyphus-junior | qwen2.5-coder |
| tech-writer | companion | llama3.2 |
| ux-designer | multimodal-looker | mimo-v2-pro |

## 3. Jarvis Voice AI

### Architecture
```
jarvis/
├── engine/     # ear (STT), mouth (TTS), eye (Vision), brain (LLM)
├── agent/      # 40+ tools, memory, security, scheduler
├── skills/     # Browser, Desktop, System, Sites automation
├── adhd/       # Focus, tracking, vibeguard
└── ui/         # Dashboard, notifications
```

### Voice Commands
- "Hey Jarvis" — Wake up
- "Goodbye/Stop/Bye" — Shutdown

## 4. MCP Servers (13+)

| Category | Servers |
|----------|---------|
| Local | Ollama (:11435), GitHub (:12001), Git (:12002), SQLite (:12003) |
| Web | Playwright (:12010), Puppeteer (:12011), Fetch (:12012), Brave (:12013), Exa (:12014) |
| Utility | Context7 (:12020), Grep_app (:12021), Obsidian (:12022), Shadcn (:12023) |

---

*Source: `/mnt/WIN_LIBRARY/_NXYME_ARCHIVE/00_N-Xyme_CATALYST/`*
