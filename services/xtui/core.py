"""XTUI Core — main application class."""
import shlex, os, time, textwrap
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings

from .config import load as load_config
from .agents import AgentManager
from .mcp import MCPClient
from .plugins import PluginManager

ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

class XTUI:
    def __init__(self):
        self.config = load_config()
        self.agents = AgentManager()
        self.mcp = MCPClient()
        self.console = Console()
        self.history = []
        self._running = True
        self._cached_tools = {}
        
        # Plugin system
        self.plugins = PluginManager(self, [os.path.expanduser("~/.xtui/plugins")])
        
        # Prompt
        hist_dir = f"{ROOT}/data/xtui"
        os.makedirs(hist_dir, exist_ok=True)
        self.prompt = PromptSession(
            history=FileHistory(f"{hist_dir}/history.txt"),
            auto_suggest=AutoSuggestFromHistory(),
        )
        
        # Key bindings
        self.kb = KeyBindings()
        self._setup_keys()
    
    def _setup_keys(self):
        @self.kb.add("c-c")
        def _(event):
            self._running = False
            event.app.exit()
        
        @self.kb.add("c-d")
        def _(event):
            self._running = False
            event.app.exit()
    
    def _prompt_text(self):
        short = self.agents.current_id().upper()
        fmt = self.config.get("prompt_format", "[{agent_short}]> ")
        return fmt.replace("{agent_short}", short).replace("{agent_name}", self.agents.current_name())
    
    def _completer(self):
        words = ["/help", "/exit", "/quit", "/agents", "/tools", "/plugins"]
        words += [f"/agent {a['id']}" for a in self.agents.list()]
        words += [f"/{t}" for t in ["bash", "read", "write", "edit", "glob", "grep", "ls", "cat", "ps", "whoami"]]
        return WordCompleter(words, sentence=True)
    
    def echo(self, text, style=None):
        if style:
            self.console.print(Text(text, style=style))
        else:
            self.console.print(text)
    
    def panel(self, title, content, style=None):
        s = style or self.config["colors"]["primary"]
        self.console.print(Panel(content, title=title, border_style=s))
    
    def error(self, text):
        self.console.print(f"[{self.config['colors']['error']}]✗ {text}[/]")
    
    def success(self, text):
        self.console.print(f"[{self.config['colors']['secondary']}]✓ {text}[/]")
    
    def show_agents(self):
        t = Table(title="Agents", title_style="bold")
        t.add_column("#", style="dim")
        t.add_column("ID", style="cyan")
        t.add_column("Name")
        t.add_column("Mode")
        for i, a in enumerate(self.agents.list(), 1):
            marker = " ◄" if a["id"] == self.agents.current_id() else ""
            t.add_row(str(i), a["id"] + marker, a["name"], a.get("mode", "subagent"))
        self.console.print(t)
    
    def show_tools(self):
        agent = self.agents.current_name()
        self.console.print(f"[dim]Fetching tools for {agent}...[/]")
        lines = []
        for srv in ["bash", "megatools", "bmad", "nx"]:
            tools = self.mcp.tools_list(srv)
            if tools:
                lines.append(f"  [cyan]{srv}[/]: {', '.join(tools[:10])}")
                if len(tools) > 10:
                    lines[-1] += f" +{len(tools)-10} more"
        self.panel(f"Tools available to {agent}", "\n".join(lines))
    
    def show_plugins(self):
        if not self.plugins.plugins:
            self.echo("No plugins loaded. Add .py files to ~/.xtui/plugins/", "dim")
        else:
            t = Table(title="Plugins")
            t.add_column("Name")
            t.add_column("Description")
            for p in self.plugins.plugins:
                t.add_row(p.name, p.description)
            self.console.print(t)
    
    # ── Command Dispatch ─────────────────────────────────────────
    def cmd_agent(self, args):
        if not args:
            self.show_agents()
            return
        a = self.agents.set(args)
        if a:
            self.success(f"Switched to {a['name']}")
            self.plugins.dispatch("on_agent_switch", a, self)
        else:
            self.error(f"No agent: {args}")
    
    def cmd_bash(self, args):
        if not args:
            self.error("Usage: bash <command>")
            return
        self.echo(f"[dim]Agent: {self.agents.current_name()}[/]")
        r = self.mcp.tool("bash", "bash", {"command": args, "description": "XTUI"}, self.agents.current_name())
        t = (r.get("content") or [{}])[0].get("text", str(r))
        self.echo(t)
    
    def cmd_read(self, args):
        if not args:
            self.error("Usage: read <path>")
            return
        path = os.path.expanduser(args)
        r = self.mcp.tool("megatools", "read_tool", {"filePath": path}, self.agents.current_name())
        t = (r.get("content") or [{}])[0].get("text", "")
        if t.startswith("Error"):
            self.error(t)
        else:
            self.echo(t[:3000])
    
    def cmd_write(self, args):
        parts = shlex.split(args)
        if len(parts) < 2:
            self.error("Usage: write <path> <content>")
            return
        path = os.path.expanduser(parts[0])
        content = " ".join(parts[1:])
        r = self.mcp.tool("megatools", "write_tool", {"filePath": path, "content": content}, self.agents.current_name())
        self.echo((r.get("content") or [{}])[0].get("text", "done"))
    
    def cmd_edit(self, args):
        parts = shlex.split(args)
        if len(parts) < 3:
            self.error("Usage: edit <path> <old> <new>")
            return
        r = self.mcp.tool("megatools", "edit_tool",
            {"filePath": os.path.expanduser(parts[0]), "oldString": parts[1], "newString": parts[2]},
            self.agents.current_name())
        self.echo((r.get("content") or [{}])[0].get("text", "done"))
    
    def cmd_glob(self, args):
        if not args:
            self.error("Usage: glob <pattern>")
            return
        r = self.mcp.tool("megatools", "glob_tool", {"pattern": args}, self.agents.current_name())
        self.echo((r.get("content") or [{}])[0].get("text", ""))
    
    def cmd_grep(self, args):
        parts = shlex.split(args)
        if not parts:
            self.error("Usage: grep <pattern> [path]")
            return
        pat = parts[0]
        path = parts[1] if len(parts) > 1 else ROOT
        r = self.mcp.tool("megatools", "grep_tool", {"pattern": pat, "path": path}, self.agents.current_name())
        self.echo((r.get("content") or [{}])[0].get("text", ""))
    
    def cmd_plugins(self, args):
        self.show_plugins()
    
    def cmd_tools(self, args):
        self.show_tools()
    
    def cmd_help(self, args):
        self.panel("XTUI Commands", """
[cyan]/agent <id|#>[/]   — Switch active agent
[cyan]/bash <cmd>[/]     — Run shell command
[cyan]/read <path>[/]    — Read file
[cyan]/write <p> <c>[/]  — Write file
[cyan]/edit <p> <o> <n>[/] — Edit file (replace)
[cyan]/glob <pat>[/]     — Glob files
[cyan]/grep <pat> [p][/] — Search files
[cyan]/agents[/]         — List agents
[cyan]/tools[/]          — List tools for current agent
[cyan]/plugins[/]        — List loaded plugins
[cyan]/help[/]           — This help
[cyan]/exit[/]           — Quit

[dim]Any unhandled command falls through to bash[/]
        """)
    
    def cmd_exit(self, args):
        self._running = False
    
    def run(self):
        # Startup
        self.plugins.dispatch("on_startup", self)
        self.echo(Panel(
            f"[bold cyan]XTUI[/] — Agent: [green]{self.agents.current_name()}[/]\n"
            f"MCP: bash, megatools, bmad, nx | Plugins: {len(self.plugins.plugins)}\n"
            f"Type [bold]/help[/] for commands",
            border_style="cyan"
        ))
        
        while self._running:
            try:
                text = self.prompt.prompt(
                    self._prompt_text(),
                    completer=self._completer(),
                    key_bindings=self.kb,
                )
            except:
                break
            
            if not text.strip():
                continue
            
            # Dispatch
            parts = shlex.split(text)
            cmd = parts[0].lstrip("/").lower()
            args = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            handler = getattr(self, f"cmd_{cmd}", None)
            if handler:
                handler(args)
            else:
                # Check plugins
                handled = False
                for p in self.plugins.plugins:
                    try:
                        result = p.on_command(cmd, args, self)
                        if result is not None:
                            self.echo(result)
                            handled = True
                            break
                    except:
                        pass
                if not handled:
                    self.error(f"Unknown: /{cmd}. Type /help")
        
        # Shutdown
        self.plugins.dispatch("on_shutdown", self)
        self.mcp.stop_all()
