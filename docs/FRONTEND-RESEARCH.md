# N-Xyme MIND Frontend Options Research

## Executive Summary

This research compiles all viable open source frontend options for creating a branded UI layer around N-Xyme MIND v0.1. The options are evaluated against requirements for ASCII art logo display, custom footer/branding, MCP integration, agent status visualization, health checks, trigger status, and VPN status monitoring.

---

## 1. TUI Frameworks (Python)

### 1.1 Textual

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/textualize/textual |
| **Stars** | 35,181 |
| **License** | MIT |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes - supports rich text, panels, ASCII |
| **Custom Footer/Branding** | ✅ Yes - footer, header, sidebar components |
| **MCP Integration** | ⚠️ Medium - can run subprocess, wrap OpenCode |
| **Agent Status** | ✅ Yes - can build custom status widgets |
| **Health Checks** | ✅ Yes - supports async refresh, data binding |
| **Trigger Status** | ✅ Yes - custom widgets |
| **VPN Status** | ✅ Yes - custom widgets |
| **Complexity** | Medium - declarative API, good docs |

**Integration Notes**: Textual is the most powerful Python TUI framework. It can run OpenCode as a subprocess and render a branded dashboard around it. Supports ASCII art natively via the `Text` class. Perfect for N-Xyme MIND's Python ecosystem.

**Example Capability**:
```python
from textual.app import App
from textual.widgets import Static

class NxymeDashboard(App):
    def compose(self):
        yield Static("""
╔══════════════════════════════════════════╗
║     N-Xyme MIND v0.1                    ║
║     AI Coding Workspace                 ║
╚══════════════════════════════════════════╝
        """, markup=True)
```

---

### 1.2 Rich

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/textualize/rich |
| **Stars** | 55,934 |
| **License** | MIT |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes - primary feature |
| **Custom Footer/Branding** | ✅ Yes - console.print with styling |
| **MCP Integration** | ⚠️ Medium - output formatting only |
| **Agent Status** | ✅ Yes - progress bars, status panels |
| **Health Checks** | ✅ Yes - live panels |
| **Trigger Status** | ✅ Yes - tables, panels |
| **VPN Status** | ✅ Yes - tables, panels |
| **Complexity** | Low - simple API |

**Integration Notes**: Rich is a terminal printing library, not a full TUI framework. Best used for branding output within scripts. Can be combined with Textual for enhanced visuals.

---

### 1.3 Blessings / Ncurses

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/pythony-microsoft/blessings (deprecated) |
| **License** | MIT |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes |
| **Custom Footer/Branding** | ✅ Yes |
| **MCP Integration** | ⚠️ Low - legacy, limited features |
| **Complexity** | High - complex API |

**Integration Notes**: Blessings is largely superseded by Rich/Textual. Not recommended for new projects.

---

## 2. TUI Frameworks (Go)

### 2.1 Bubble Tea

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/charmbracelet/bubbletea |
| **Stars** | 41,021 |
| **License** | MIT |
| **Language** | Go |
| **ASCII Art Logo** | ✅ Yes - excellent text rendering |
| **Custom Footer/Branding** | ✅ Yes - full layout system |
| **MCP Integration** | ✅ Yes - can wrap OpenCode subprocess |
| **Agent Status** | ✅ Yes - custom views |
| **Health Checks** | ✅ Yes - timer-based refresh |
| **Trigger Status** | ✅ Yes - custom views |
| **VPN Status** | ✅ Yes - custom views |
| **Complexity** | Medium - Elm-inspired architecture |

**Integration Notes**: Bubble Tea is the most popular Go TUI framework. Excellent for building a dedicated wrapper around OpenCode. The Charm ecosystem (lip-gloss, bubbly) provides additional styling.

---

### 2.2 Termui

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/gizak/termui |
| **Stars** | 5,200+ |
| **License** | MIT |
| **Language** | Go |
| **ASCII Art Logo** | ✅ Yes |
| **Custom Footer/Branding** | ✅ Yes |
| **MCP Integration** | ⚠️ Medium - basic widgets |
| **Complexity** | Low-Medium |

**Integration Notes**: Simpler than Bubble Tea, good for dashboards.

---

### 2.3 Clui

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/secana/clui |
| **Stars** | ~500 |
| **License** | MIT |
| **Language** | Go |
| **ASCII Art Logo** | ✅ Yes |
| **Custom Footer/Branding** | ✅ Yes |
| **Complexity** | Low |

**Integration Notes**: Lightweight, simpler than Termui.

---

## 3. TUI Frameworks (JavaScript/TypeScript)

### 3.1 Ink (React for CLI)

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/vadimdemedes/ink |
| **Stars** | 36,510 |
| **License** | MIT |
| **Language** | TypeScript |
| **ASCII Art Logo** | ✅ Yes - React components |
| **Custom Footer/Branding** | ✅ Yes |
| **MCP Integration** | ✅ Yes - JavaScript ecosystem |
| **Agent Status** | ✅ Yes - React state |
| **Health Checks** | ✅ Yes - useInterval |
| **Trigger Status** | ✅ Yes |
| **VPN Status** | ✅ Yes |
| **Complexity** | Low-Medium - React patterns |

**Integration Notes**: Ink uses React to build CLI apps. If your team knows React, this is the fastest path. Can wrap OpenCode subprocess.

---

### 3.2 Pastel

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/vadimdemedes/pastel |
| **Stars** | 2,361 |
| **License** | MIT |
| **Language** | TypeScript |
| **ASCII Art Logo** | ✅ Yes |
| **Custom Footer/Branding** | ✅ Yes |
| **Complexity** | Low |

**Integration Notes**: Framework built on top of Ink, similar to Next.js for CLIs.

---

## 4. Web Frontends for AI Coding Tools

### 4.1 Open WebUI

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/Open-WebUI/Open-WebUI |
| **Stars** | 129,892 |
| **License** | MIT |
| **Language** | Python/Svelte |
| **ASCII Art Logo** | ✅ Yes - can customize logo |
| **Custom Footer/Branding** | ✅ Yes - themes, custom CSS |
| **MCP Integration** | ✅ Yes - extensive MCP support |
| **Agent Status** | ✅ Yes |
| **Health Checks** | ⚠️ Limited - server status only |
| **Trigger Status** | ❌ No - not designed for triggers |
| **VPN Status** | ❌ No |
| **Complexity** | High - full web app deployment |

**Integration Notes**: Open WebUI is primarily an Ollama/OpenAI web interface. Not ideal for wrapping OpenCode - it's a complete chat UI. Could be used as a separate frontend if N-Xyme MIND exposes an API.

---

### 4.2 LibreChat

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/danny-avila/LibreChat |
| **Stars** | 35,100 |
| **License** | MIT |
| **Language** | TypeScript |
| **ASCII Art Logo** | ✅ Yes - logo customization |
| **Custom Footer/Branding** | ✅ Yes |
| **MCP Integration** | ✅ Yes - MCP support |
| **Agent Status** | ✅ Yes |
| **Health Checks** | ⚠️ Limited |
| **Trigger Status** | ❌ No |
| **VPN Status** | ❌ No |
| **Complexity** | High |

**Integration Notes**: Similar to Open WebUI - a chat interface. Not ideal for terminal-focused branding.

---

### 4.3 Continue.dev

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/continuedev/continue |
| **Stars** | 25,000+ |
| **License** | MIT |
| **Language** | TypeScript |
| **ASCII Art Logo** | ✅ Yes - VS Code extension |
| **Custom Footer/Branding** | ✅ Yes |
| **MCP Integration** | ✅ Yes - first-class MCP |
| **Agent Status** | ✅ Yes |
| **Complexity** | Medium |

**Integration Notes**: Continue is a VS Code extension for AI coding. OpenCode already provides similar functionality - this would be an alternative, not a wrapper.

---

### 4.4 Aider

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/Aider-AI/aider |
| **Stars** | 42,761 |
| **License** | Apache 2.0 |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes - terminal-based |
| **Custom Footer/Branding** | ⚠️ Limited |
| **MCP Integration** | ✅ Yes |
| **Agent Status** | ✅ Yes |
| **Complexity** | Low |

**Integration Notes**: Aider is an AI pair programming tool in the terminal. Similar to OpenCode in concept - direct competitor, not a wrapper.

---

## 5. Terminal Multiplexers with Branding

### 5.1 Zellij

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/zellij-org/zellij |
| **Stars** | 30,900 |
| **License** | MIT |
| **Language** | Rust |
| **ASCII Art Logo** | ✅ Yes - welcome screen |
| **Custom Footer/Branding** | ✅ Yes - status bar, layout |
| **MCP Integration** | ⚠️ Indirect - run OpenCode in pane |
| **Agent Status** | ⚠️ Limited - status bar only |
| **Health Checks** | ⚠️ Limited |
| **Trigger Status** | ⚠️ Limited |
| **VPN Status** | ⚠️ Limited |
| **Complexity** | Medium |

**Integration Notes**: Zellij can run OpenCode in a pane while showing status in the status bar. Layouts can be predefined for branded sessions.

---

### 5.2 tmux

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/tmux/tmux |
| **Stars** | N/A (GNU project) |
| **License** | BSD |
| **Language** | C |
| **ASCII Art Logo** | ✅ Yes - status bar, window names |
| **Custom Footer/Branding** | ✅ Yes - status bar, tmux.conf |
| **MCP Integration** | ⚠️ Indirect - run OpenCode in window |
| **Agent Status** | ⚠️ Limited - via set-status/script |
| **Health Checks** | ⚠️ Limited |
| **Trigger Status** | ⚠️ Limited |
| **VPN Status** | ⚠️ Limited |
| **Complexity** | Low-Medium |

**Integration Notes**: tmux is the standard terminal multiplexer. Can run OpenCode and display status in the status bar using custom scripts. Extensive customization via `.tmux.conf`.

**Example Branding**:
```bash
# ~/.tmux.conf
set -g status-left "#[fg=green]N-Xyme MIND#[default]"
set -g status-right "#[fg=yellow]VPN: #{VPN_STATUS}#[default]"
```

---

## 6. AI Agent Observability Dashboards

### 6.1 Langfuse

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/langfuse/langfuse |
| **Stars** | 24,100 |
| **License** | MIT |
| **Language** | TypeScript/PostgreSQL |
| **ASCII Art Logo** | ❌ Web UI |
| **Custom Footer/Branding** | ⚠️ Limited - Enterprise |
| **MCP Integration** | ✅ Yes - SDK |
| **Agent Status** | ✅ Yes - traces, sessions |
| **Health Checks** | ✅ Yes - self-hosted dashboard |
| **Trigger Status** | ⚠️ Indirect - traces |
| **VPN Status** | ❌ No |
| **Complexity** | High - full deployment |

**Integration Notes**: Langfuse provides LLM observability. Can be integrated with N-Xyme MIND for tracing agent operations. Self-hostable.

---

### 6.2 Arize Phoenix

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/Arize-ai/phoenix |
| **Stars** | 9,074 |
| **License** | Apache 2.0 (Elastic 2.0 for Python SDK) |
| **Language** | Python/TypeScript |
| **ASCII Art Logo** | ❌ Web UI |
| **Custom Footer/Branding** | ❌ No |
| **MCP Integration** | ✅ Yes - OpenTelemetry |
| **Agent Status** | ✅ Yes - traces |
| **Health Checks** | ✅ Yes |
| **Trigger Status** | ⚠️ Indirect |
| **VPN Status** | ❌ No |
| **Complexity** | High |

**Integration Notes**: Phoenix is an observability platform. Integrates via OpenTelemetry - can trace N-Xyme MIND operations.

---

## 7. MCP-Compatible Frontends

### 7.1 MCP-UI

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/MCP-UI-Org/mcp-ui |
| **Stars** | 4,588 |
| **License** | Not specified (check before use) |
| **Language** | TypeScript |
| **ASCII Art Logo** | ✅ Yes |
| **Custom Footer/Branding** | ✅ Yes - UI over MCP |
| **MCP Integration** | ✅ Yes - primary feature |
| **Agent Status** | ✅ Yes |
| **Complexity** | Medium |

**Integration Notes**: MCP-UI is designed specifically to create UI over MCP. Could be extended for N-Xyme MIND status display.

---

### 7.2 Model Context Protocol (Official)

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/modelcontextprotocol/typescript-sdk |
| **Stars** | 12,092 |
| **License** | MIT (for SDK) |
| **Language** | TypeScript |
| **MCP Integration** | ✅ Yes - first-class |

**Integration Notes**: The official MCP SDK can be used to build custom frontends that connect to MCP servers.

---

## 8. ASCII Art / Terminal Branding Tools

### 8.1 art (Python)

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/sepandhaghighi/art |
| **Stars** | 2,454 |
| **License** | MIT |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes - 200+ fonts |
| **Custom Footer/Branding** | ✅ Yes - text generation |

**Integration Notes**: Generates ASCII art from text. Can generate N-Xyme MIND logo in various fonts.

---

### 8.2 python-ascii_magic

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/LeandroBarone/python-ascii_magic |
| **Stars** | 167 |
| **License** | MIT |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes - image to ASCII |

**Integration Notes**: Converts images to ASCII art. Can create custom logos.

---

### 8.3 asciify-them

| Property | Value |
|----------|-------|
| **GitHub** | https://github.com/ndrscalia/asciify-them |
| **Stars** | 238 |
| **License** | NOASSERTION (check) |
| **Language** | Python |
| **ASCII Art Logo** | ✅ Yes |

---

## 9. Summary Matrix

| Option | GitHub | Stars | License | ASCII Logo | Custom Footer | MCP | Agent Status | Health | Trigger | VPN | Complexity |
|--------|--------|-------|---------|------------|---------------|-----|--------------|--------|---------|-----|------------|
| **Textual** | textualize/textual | 35.1k | MIT | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | Medium |
| **Rich** | textualize/rich | 55.9k | MIT | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | Low |
| **Bubble Tea** | charmbracelet/bubbletea | 41k | MIT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Medium |
| **Ink** | vadimdemedes/ink | 36.5k | MIT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Low-Medium |
| **Zellij** | zellij-org/zellij | 30.9k | MIT | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Medium |
| **tmux** | tmux/tmux | N/A | BSD | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Low |
| **Open WebUI** | Open-WebUI/Open-WebUI | 129.9k | MIT | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | High |
| **LibreChat** | danny-avila/LibreChat | 35.1k | MIT | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | High |
| **Langfuse** | langfuse/langfuse | 24.1k | MIT | ❌ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ❌ | High |
| **Phoenix** | Arize-ai/phoenix | 9k | Apache | ❌ | ❌ | ✅ | ✅ | ✅ | ⚠️ | ❌ | High |
| **MCP-UI** | MCP-UI-Org/mcp-ui | 4.6k | Check | ✅ | ✅ | ✅ | ✅ | - | - | - | Medium |
| **art** | sepandhaghighi/art | 2.4k | MIT | ✅ | ✅ | - | - | - | - | - | Low |
| **Aider** | Aider-AI/aider | 42.7k | Apache | ✅ | ⚠️ | ✅ | ✅ | - | - | - | Low |

---

## 10. Recommended Architecture for N-Xyme MIND

### Option A: Textual Wrapper (Recommended)

**Stack**: Textual + Rich + art

**Approach**:
1. Build a Textual dashboard app that runs OpenCode as a subprocess
2. Use `art` library to generate N-Xyme ASCII logo on startup
3. Display agent status, trigger status, VPN status in dedicated panels
4. Run in a side pane while OpenCode runs in the main area

**Complexity**: Medium | **Control**: High

```python
# conceptual架构
class NxymeDashboard(App):
    async def on_mount(self):
        # Generate ASCII logo
        from art import text2art
        logo = text2art("N-Xyme MIND", font="block")
        
        # Run OpenCode subprocess
        self.opencode_process = await subprocess_exec("opencode", ...)
```

---

### Option B: Bubble Tea Wrapper

**Stack**: Bubble Tea (Go) + lip-gloss

**Approach**:
1. Build a Go TUI that wraps OpenCode
2. Display status in header/footer
3. Communicate with N-Xyme MIND via IPC

**Complexity**: Medium | **Control**: High

---

### Option C: tmux + Script Integration

**Stack**: tmux + shell scripts + art

**Approach**:
1. Define tmux layout with N-Xyme branding in status bar
2. Run OpenCode in main pane
3. Use scripts to poll status and display in status bar

**Complexity**: Low | **Control**: Medium

---

### Option D: Ink (React) Dashboard

**Stack**: Ink + React patterns

**Approach**:
1. Build React-based CLI dashboard
2. Run OpenCode as child process
3. Display status via React state

**Complexity**: Low-Medium | **Control**: High

---

## 11. Next Steps

1. **Prototype**: Build a minimal Textual wrapper that:
   - Displays ASCII logo on startup
   - Runs OpenCode in a subprocess
   - Shows placeholder status panels

2. **Integrate Status**:
   - Read trigger status from `triggers.json`
   - Read VPN status from VPN rotator
   - Poll health endpoints

3. **Polish Branding**:
   - Custom color scheme (N-Xyme colors)
   - Custom fonts via `art` library
   - Animated status indicators

---

*Research completed: April 2026*
*Sources: GitHub repositories, official documentation*
