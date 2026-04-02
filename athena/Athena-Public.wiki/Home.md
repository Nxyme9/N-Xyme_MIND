# 🏛️ Welcome to Project Athena

> **The Linux OS for AI Agents**
> Open Source · Sovereign · Model-Agnostic

*Last Updated: 2026-03-21 · v9.5.7*

Athena is not an AI Agent. It is the **Operating System** they run on.

Just as Linux provides the kernel, file system, and permissions for applications to run, Athena provides **persistent memory, scheduling, governance, and self-optimization** for AI models (Claude, Gemini, GPT, Llama) to operate as continuous agents.

| OS Layer | Linux | Athena |
|----------|-------|--------|
| **Kernel** | Hardware abstraction | Memory persistence + retrieval (VectorRAG, Supabase) |
| **File System** | ext4, NTFS | Markdown files, session logs, tag index |
| **Scheduler** | cron, systemd | Heartbeat daemon, daily briefing, auto-indexing |
| **Shell** | bash, zsh | MCP Tool Server, `/start`, `/end`, `/think` |
| **Permissions** | chmod, users/groups | 4-level capability tokens + Secret Mode |
| **Package Manager** | apt, yum | Protocols, skills, workflows |

**You own the data** (Markdown files on your machine, git-versioned). You only **rent the intelligence** (LLM API calls). Switch models tomorrow and your memory stays exactly where it is.

> [!TIP]
> **Before you begin, ask yourself**: *"How do I want Athena to best help me in my daily life?"* — This is the guiding principle. Everything else exists to serve your answer. See [Your First Session](../docs/YOUR_FIRST_SESSION.md) for the full guide.

---

## ⚡ The Core Loop

```
🟢 Lightweight:  Just chat → /end           (~2K tokens)
🔴 Full Boot:    /start → Work → /end       (~10K tokens)
⚫ Deep Boot:    /ultrastart → Work → /ultraend   (~20K tokens)
```

1. **Boot (`/start` or `/ultrastart`)**: Loads Core Identity (2K–20K tokens depending on mode) and relevant context.
2. **Work**: Collaborate with AI to solve problems. Every exchange auto-saves.
3. **Commit (`/end`)**: Summarizes the session, extracts decisions, updates long-term memory.
4. **Compounding**: Next boot starts *smarter*. By session 100, it stops being generic and starts thinking like **you**.

---

## 🚀 Quick Start (5 Minutes)

| Step | Action |
|:-----|:-------|
| **1. Get an IDE** | [Antigravity](https://antigravity.google/) · [Cursor](https://cursor.com) · [Kilo Code](https://kilocode.ai/) · [Roo Code](https://roocode.com/) · [Claude Code](https://docs.anthropic.com/en/docs/claude-code) |
| **2. Clone** | `git clone https://github.com/winstonkoh87/Athena-Public.git && cd Athena-Public` |
| **3. Open & Type `/start`** | The AI reads the repo structure and boots |
| **4. Type `/tutorial`** | Athena gives you a guided walkthrough and builds your personal profile |

Or use [GitHub Codespaces](https://codespaces.new/winstonkoh87/Athena-Public) for zero-setup cloud boot.

> See [Getting Started](Getting-Started) for detailed instructions.

---

## 🗺️ Navigation

| Page | Description |
|:-----|:------------|
| **🚀 [Getting Started](Getting-Started)** | Installation, first boot, workspace modes, CLI commands |
| **📖 [Your First Session](../docs/YOUR_FIRST_SESSION.md)** | The intent-first onboarding guide |
| **🏗️ [Architecture](Architecture-Overview)** | OS layers, Hybrid RAG, MCP Server, Tech Stack |
| **⚡ [Workflows](Workflow-Reference)** | `/start`, `/end`, `/think`, `/refactor` and 60+ commands |
| **🎯 [Use Cases](Use-Cases)** | Decision-making, research, planning, meta-thinking |
| **📈 [The Compounding Effect](The-Compounding-Effect)** | Why Athena gets smarter over time |
| **🧠 [Philosophy](Philosophy)** | Own the state. Rent the intelligence. |
| **❓ [FAQ](FAQ)** | Privacy, cost, models, and comparisons |

---

## 📊 Community

- **1M+** Reddit Views · **#1 All-Time** on r/ChatGPT · **#2 All-Time** on r/GeminiAI
- **148+** Protocols · **540+** Scripts · **60+** Slash Workflows
- **MIT Licensed** · [Main Repository](https://github.com/winstonkoh87/Athena-Public)
