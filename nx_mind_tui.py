#!/usr/bin/env python3
"""
N-Xyme MIND TUI - Terminal User Interface
=======================================
Synthesized from OpenCode TUI (best parts) + OMO/BMAD patterns
Provides interactive chat, orchestration, and agent management.

Usage:
    nx-mind-tui           # Start TUI
    nx-mind-tui --help  # Show help
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Optional rich terminal - will use simple CLI if not available
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Project paths
PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
sys.path.insert(0, PROJECT_ROOT)

from packages.nx_mcp.nx_delegate import nx_delegate
from packages.orchestration.weighted_injector import inject_weighted


class NXMindTUI:
    """N-Xyme MIND Terminal UI"""

    def __init__(self):
        self.sessions = []
        self.current_session = None
        self.session_history = []
        self.messages = []
        self.agent_busy = False
        self.show_help = False
        self.show_quit = False
        self.show_sessions = False
        self.show_themes = False
        self.show_models = False
        self.current_theme = "dark"
        self.selected_model = "minimax-m2.5-free"

    def add_message(self, role: str, content: str):
        """Add message to chat"""
        self.messages.append({"role": role, "content": content, "timestamp": None})

    async def send_message(self, text: str):
        """Send message to agent"""
        self.add_message("user", text)
        self.agent_busy = True

        try:
            # Route via nx_delegate
            result = nx_delegate(text)

            # Simulate agent response
            response = f"[{result['agent']}] Level {result['level']}/5 | Conf {result['confidence'] * 100:.0f}% | {result['strategy_used']}\n\n{result['reason']}"
            self.add_message("assistant", response)

        except Exception as e:
            self.add_message("system", f"Error: {e}")
        finally:
            self.agent_busy = False

    def render_chat(self):
        """Render chat messages"""
        lines = []
        for msg in self.messages[-50:]:  # Last 50 messages
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                lines.append(f"➤ {content}")
            elif role == "assistant":
                lines.append(f"▸ {content}")
            else:
                lines.append(f"● {content}")

        return "\n".join(lines) if lines else "[Start a conversation...]"

    def render_status(self):
        """Render status bar"""
        agents = ["hephaestus", "oracle", "explore", "librarian"]
        return f" nx-mind | sessions: {len(self.sessions)} | model: {self.selected_model} | agents: {', '.join(agents)} | theme: {self.current_theme}"

    def run_with_rich(self, user_input: str):
        """Run with rich formatting"""
        if not RICH_AVAILABLE:
            asyncio.run(self.send_message(user_input))
            return

        console = Console()
        console.print("\n[bold cyan]➤[/bold cyan] " + user_input)

        asyncio.run(self.send_message(user_input))

        # Show response
        if self.messages:
            last_msg = self.messages[-1]
            console.print(f"[bold green]▸[/bold green] {last_msg['content']}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="N-Xyme MIND TUI")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark")
    parser.add_argument("--model", default="minimax-m2.5-free")
    parser.add_argument("--prompt", "-p", help="Run single prompt and exit")
    args = parser.parse_args()

    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                       ║
║   █▀█ █▀█ █▀█ █▀█ █▀█   N-Xyme MIND   █▀█ █▀█ █▀█   ║
║   █��▄ █▄▄ █▄▄ █▄▄             █▄▄ █▄▄ █▄▄   ║
║                                                       ║
║   Your Personal AI System                    v1.0.0   ║
║                                                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                       ║
║   Commands:                                        ║
║     exit/quit   Quit                                ║
║     Ctrl+C    Quit                                ║
║     help      Show this message                   ║
║                                                       ║
║   Type your task and press Enter to begin...          ║
║                                                       ║
╚═══════════════════════════════════════════════════════════╝
    """)

    tui = NXMindTUI()

    # Single prompt mode
    if args.prompt:
        asyncio.run(tui.send_message(args.prompt))
        if tui.messages:
            print(tui.messages[-1]["content"])
        return

    # Interactive loop
    while True:
        try:
            user_input = input("\n➤ ").strip()

            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 Goodbye!")
                break

            if user_input.lower() == "help":
                print("""
Available commands:
  exit/quit   - Exit the TUI
  help      - Show this message
  clear     - Clear chat history
""")
                continue

            if user_input.lower() == "clear":
                tui.messages = []
                print("Chat cleared.")
                continue

            if not user_input:
                continue

            # Run async
            asyncio.run(tui.send_message(user_input))

            # Show response
            if tui.messages:
                print("\n" + tui.messages[-1]["content"])
            print()

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
