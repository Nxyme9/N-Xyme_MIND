#!/usr/bin/env python3
"""
N-Xyme Research Companion
Background agent that watches, researches, and stores findings.
Runs on local LLM (free, no API costs).
"""

import json
import os
import logging
import time
import subprocess
import requests
import psutil
from datetime import datetime
from pathlib import Path

# Config
OLLAMA_MODEL = "llama3.2:3b-instruct-q4_K_M"  # Fast, free

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import GRAPHITI_RPC_URL as GRAPHITI_URL, OLLAMA_URL
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CHECK_INTERVAL = 300  # 5 minutes
CATALYST_DIR = Path(__file__).parent.parent.resolve()
NOTEPAD_DIR = CATALYST_DIR / ".sisyphus" / "notepads" / "research-companion"

# Ensure notepad dir exists
NOTEPAD_DIR.mkdir(parents=True, exist_ok=True)


class ResearchCompanion:
    def __init__(self):
        self.last_git_hash = None
        self.last_pm2_status = None
        self.anomaly_count = 0
        print(f"[{self.now()}] Research Companion started")
        print(f"  Model: {OLLAMA_MODEL}")
        print(f"  Check interval: {CHECK_INTERVAL}s")
        print(f"  Notepad: {NOTEPAD_DIR}")

    def now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === WATCHERS ===

    def watch_git(self):
        """Check for new commits."""
        try:
            r = subprocess.run(
                ["git", "log", "-1", "--format=%H %s"],
                capture_output=True,
                text=True,
                cwd=str(CATALYST_DIR),
            )
            if r.returncode == 0:
                current = r.stdout.strip()
                if current != self.last_git_hash:
                    self.last_git_hash = current
                    return {"type": "git_commit", "data": current}
        except Exception as e:
            logging.error(f"watch_git failed: {e}")
        return None

    def watch_pm2(self):
        """Check PM2 process health."""
        try:
            r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
            if r.returncode == 0:
                processes = json.loads(r.stdout)
                issues = []
                for p in processes:
                    if p.get("pm2_env", {}).get("status") != "online":
                        issues.append(f"{p['name']}: {p['pm2_env']['status']}")
                    if p.get("pm2_env", {}).get("restart_time", 0) > 5:
                        issues.append(f"{p['name']}: {p['pm2_env']['restart_time']} restarts")
                if issues:
                    return {"type": "pm2_health", "data": issues}
        except Exception as e:
            logging.error(f"watch_pm2 failed: {e}")
        return None

    def watch_resources(self):
        """Check resource usage."""
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)

            alerts = []
            if mem.percent > 85:
                alerts.append(f"RAM at {mem.percent}% ({mem.available // (1024**3)}GB free)")
            if cpu > 90:
                alerts.append(f"CPU at {cpu}%")

            # Check GPU
            r = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split(", ")
                gpu_util = int(parts[0])
                vram_used = int(parts[1])
                vram_total = int(parts[2])
                vram_free = vram_total - vram_used

                if vram_free > 6000:
                    alerts.append(f"GPU has {vram_free}MB free VRAM - can load more models")
                if gpu_util < 10:
                    alerts.append(f"GPU at {gpu_util}% - massively underutilized")

            if alerts:
                return {"type": "resources", "data": alerts}
        except Exception as e:
            logging.error(f"watch_resources failed: {e}")
        return None

    def watch_ollama(self):
        """Check Ollama model status."""
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            models = r.json().get("models", [])
            loaded = len(models)

            # Check if any model is loaded in VRAM
            r2 = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
            active = r2.json().get("models", [])

            if not active:
                return {
                    "type": "ollama",
                    "data": ["No models loaded in VRAM - pre-load for faster responses"],
                }
        except Exception as e:
            logging.error(f"watch_ollama failed: {e}")
        return None

    # === RESEARCHER ===

    def research(self, signal):
        """Deep-think about a signal using local LLM."""
        prompt = f"""You are a research companion for a developer with ADHD. Analyze this signal and provide actionable insights.

Signal: {json.dumps(signal, indent=2)}

Provide:
1. What this means (1 sentence)
2. Why it matters (1 sentence)
3. What to do about it (1-3 bullet points)
4. Priority (low/medium/high)

Be concise. No fluff. Focus on actionable insights."""

        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=30,
            )

            response = r.json().get("message", {}).get("content", "")
            return response
        except Exception as e:
            return f"Research failed: {e}"

    # === STORAGE ===

    def store_in_graphiti(self, name, content):
        """Store finding in Graphiti knowledge graph."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "graphiti_add_episode",
                    "arguments": {
                        "name": name,
                        "episode_body": content,
                        "source": "research-companion",
                        "source_description": f"Auto-research at {self.now()}",
                    },
                },
            }
            requests.post(GRAPHITI_URL, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"store_in_graphiti failed: {e}")

    def store_in_notepad(self, category, content):
        """Append to notepad file."""
        try:
            notepad_file = NOTEPAD_DIR / f"{category}.md"
            timestamp = self.now()
            entry = f"\n## [{timestamp}] {category.title()}\n{content}\n"

            with open(notepad_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logging.error(f"store_in_notepad failed: {e}")

    # === MAIN LOOP ===

    def run_once(self):
        """One check cycle."""
        signals = []

        # Collect signals
        git_signal = self.watch_git()
        if git_signal:
            signals.append(git_signal)

        pm2_signal = self.watch_pm2()
        if pm2_signal:
            signals.append(pm2_signal)

        resource_signal = self.watch_resources()
        if resource_signal:
            signals.append(resource_signal)

        ollama_signal = self.watch_ollama()
        if ollama_signal:
            signals.append(ollama_signal)

        # Research and store
        for signal in signals:
            print(f"[{self.now()}] Signal: {signal['type']}")

            insight = self.research(signal)

            # Store
            self.store_in_graphiti(f"research-{signal['type']}", insight)
            self.store_in_notepad(signal["type"], insight)

            print(f"[{self.now()}] Insight stored")

    def run(self):
        """Main loop."""
        print(f"\n{'=' * 50}")
        print(f"  RESEARCH COMPANION RUNNING")
        print(f"  Press Ctrl+C to stop")
        print(f"{'=' * 50}\n")

        while True:
            try:
                self.run_once()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                print(f"\n[{self.now()}] Research Companion stopped")
                break
            except Exception as e:
                print(f"[{self.now()}] Error: {e}")
                time.sleep(60)  # Back off on error


if __name__ == "__main__":
    companion = ResearchCompanion()
    companion.run()
