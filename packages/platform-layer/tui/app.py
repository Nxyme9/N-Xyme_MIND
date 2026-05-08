"""Terminal UI application entry point."""
#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, DataTable, Input, Log, Label
from textual import work
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tui.api_client import CatalystAPI


class CatalystDashboard(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]
    api = CatalystAPI()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Catalyst Dashboard - Q=Quit R=Refresh", id="status")
        with Horizontal(id="main"):
            with Vertical(classes="panel"):
                yield Label("Agents")
                yield Button("PM2 Status", id="btn_pm2", variant="primary")
                yield DataTable(id="agent_table")
            with Vertical(classes="panel"):
                yield Label("Brain")
                yield Button("Route", id="btn_route", variant="primary")
                yield Button("Classify", id="btn_classify")
                yield Static("", id="brain_out")
            with Vertical(classes="panel"):
                yield Label("Audio")
                yield Button("Play Last", id="btn_play", variant="primary")
                yield Button("List", id="btn_list")
                yield Input(placeholder="Narrate...", id="narrate_in")
                yield Button("Narrate", id="btn_narrate", variant="success")
        yield Log(id="log", auto_scroll=True)
        yield Footer()

    def on_mount(self):
        self.refresh_pm2()

    def action_refresh(self):
        self.refresh_pm2()

    @work(exclusive=True)
    async def refresh_pm2(self):
        try:
            pm2 = self.api.pm2_status()
            if pm2.get("status") == "ok":
                t = self.query_one("#agent_table", DataTable)
                t.clear()
                t.add_columns("Name", "Status")
                for p in pm2.get("processes", []):
                    t.add_row(p.get("name", "?"), p.get("pm2_env", {}).get("status", "?"))
                self.query_one("#log", Log).write_line(f"PM2: {pm2.get('count', 0)} services")
        except Exception as e:
            self.query_one("#log", Log).write_line(f"Error: {e}")

    @work(exclusive=True)
    async def on_button_pressed(self, event):
        log = self.query_one("#log", Log)
        if event.button.id == "btn_pm2":
            self.refresh_pm2()
        elif event.button.id == "btn_route":
            r = self.api.route_task("ARCH_SPEC", "HIGH", "MED", True)
            self.query_one("#brain_out").update(
                f"Target: {r.get('target')}\nReason: {r.get('reason')}"
            )
            log.write_line(f"Route: {r.get('target')}")
        elif event.button.id == "btn_classify":
            r = self.api.classify_claim("The API returns 200 OK")
            self.query_one("#brain_out").update(f"Type: {r.get('claim_type')}")
            log.write_line(f"Classify: {r.get('claim_type')}")
        elif event.button.id == "btn_play":
            audio = self.api.list_audio()
            if audio:
                self.api.play_audio(audio[0]["path"])
                log.write_line(f"Playing: {audio[0]['name']}")
        elif event.button.id == "btn_list":
            audio = self.api.list_audio()
            log.write_line(f"{len(audio)} narrations")
        elif event.button.id == "btn_narrate":
            text = self.query_one("#narrate_in", Input).value
            if text:
                r = self.api.generate_audio(text, auto_play=True)
                log.write_line(f"Generated: {r.get('file')}")


if __name__ == "__main__":
    CatalystDashboard().run()
