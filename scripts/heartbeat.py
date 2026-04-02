#!/usr/bin/env python3
"""
Heartbeat Monitor for Idle Agent System

Checks global memory for TODOs and agent status files.
If idle agent + pending work → logs recommendation to wake.
Runs every 5 minutes using Ollama (llama3.2:3b) for analysis.
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import OLLAMA_URL
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Centralized config
CONFIG = {
    "ollama_url": OLLAMA_URL,
    "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
    "agents_dir": Path(__file__).parent.parent / "configs" / "agents",
    "memory_dir": Path(__file__).parent.parent / "memory",
    "heartbeat_interval": int(os.getenv("HEARTBEAT_INTERVAL", "300")),  # 5 minutes
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
}

# Setup logging
logging.basicConfig(
    level=getattr(logging, CONFIG["log_level"]),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "heartbeat.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def load_agent_status(agent_name: str) -> Optional[Dict]:
    """Load agent status from JSON file."""
    status_file = CONFIG["agents_dir"] / f"{agent_name}-status.json"
    try:
        with open(status_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Status file not found: {status_file}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {status_file}: {e}")
        return None


def get_all_agent_statuses() -> Dict[str, Dict]:
    """Get status for all agents."""
    agents = ["prometheus", "atlas", "sisyphus"]
    statuses = {}
    for agent in agents:
        status = load_agent_status(agent)
        if status:
            statuses[agent] = status
    return statuses


def get_pending_todos() -> List[Dict]:
    """Check global memory for pending TODOs."""
    todos = []
    memory_dir = CONFIG["memory_dir"]

    if not memory_dir.exists():
        logger.warning(f"Memory directory not found: {memory_dir}")
        return todos

    # Look for TODO files in memory directory
    for todo_file in memory_dir.glob("**/*todo*.json"):
        try:
            with open(todo_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    todos.extend([t for t in data if t.get("status") == "pending"])
                elif isinstance(data, dict) and data.get("status") == "pending":
                    todos.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading {todo_file}: {e}")

    return todos


def analyze_with_ollama(prompt: str) -> Optional[str]:
    """Send prompt to Ollama for analysis."""
    try:
        response = requests.post(
            f"{CONFIG['ollama_url']}/api/generate",
            json={
                "model": CONFIG["ollama_model"],
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        return None


def recommend_wake_agent(idle_agents: List[str], pending_todos: List[Dict]) -> Optional[str]:
    """Use Ollama to recommend which agent to wake."""
    if not idle_agents or not pending_todos:
        return None

    prompt = f"""Given these idle agents: {", ".join(idle_agents)}
And these pending TODOs: {json.dumps(pending_todos[:5], indent=2)}

Which agent should be woken up and why? Respond with just the agent name and a brief reason."""

    response = analyze_with_ollama(prompt)
    return response


def run_heartbeat():
    """Main heartbeat loop."""
    logger.info("Starting heartbeat monitor...")

    while True:
        try:
            logger.info("Running heartbeat check...")

            # Get agent statuses
            statuses = get_all_agent_statuses()
            idle_agents = [
                agent for agent, status in statuses.items() if status.get("status") == "idle"
            ]

            # Get pending TODOs
            pending_todos = get_pending_todos()

            logger.info(f"Found {len(idle_agents)} idle agents, {len(pending_todos)} pending TODOs")

            # If we have idle agents and pending work, recommend wake
            if idle_agents and pending_todos:
                recommendation = recommend_wake_agent(idle_agents, pending_todos)
                if recommendation:
                    logger.info(f"RECOMMENDATION: {recommendation}")
                    # Could add notification logic here (webhook, file write, etc.)

            # Sleep until next heartbeat
            time.sleep(CONFIG["heartbeat_interval"])

        except KeyboardInterrupt:
            logger.info("Heartbeat monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in heartbeat loop: {e}")
            time.sleep(60)  # Wait a minute before retrying


if __name__ == "__main__":
    # Ensure logs directory exists
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    run_heartbeat()
