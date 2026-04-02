#!/usr/bin/env python3
"""Heartbeat Agent - Real-time monitoring and delegation"""

import time
import requests
import json
import logging
import os

logger = logging.getLogger(__name__)

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import GRAPHITI_RPC_URL
except ImportError:
    GRAPHITI_RPC_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")


class HeartbeatAgent:
    def __init__(self, interval=10):
        self.interval = interval
        self.running = True
        self._session = requests.Session()

    def check_global_todos(self):
        """Read global TODOs from Graphiti"""
        try:
            resp = self._session.post(
                GRAPHITI_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "memory/read",
                    "params": {"key": "global-todos"},
                    "id": 1,
                },
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                if "result" in data and data["result"].get("value"):
                    return json.loads(data["result"]["value"])
        except Exception as e:
            logger.debug(f"Failed to check global TODOs: {e}")
        return []

    def check_agent_status(self):
        """Check which agents are idle via Graphiti memory"""
        default_status = {"prometheus": "idle", "atlas": "idle", "sisyphus": "idle"}
        try:
            resp = self._session.post(
                GRAPHITI_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "memory/read",
                    "params": {"key": "agent-status"},
                    "id": 2,
                },
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                if "result" in data and data["result"].get("value"):
                    return json.loads(data["result"]["value"])
        except Exception as e:
            logger.debug(f"Failed to check agent status: {e}")
        return default_status

    def delegate_task(self, task, agent):
        """Delegate task to agent via Graphiti memory"""
        delegation = {
            "task": task,
            "agent": agent,
            "delegated_at": time.time(),
            "status": "delegated",
        }
        try:
            resp = self._session.post(
                GRAPHITI_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "memory/write",
                    "params": {
                        "key": f"delegation/{agent}/{task.get('id', 'unknown')}",
                        "value": json.dumps(delegation),
                    },
                    "id": 3,
                },
                timeout=10,
            )
            if resp.ok:
                print(f"Delegated: {task.get('description', task)} -> {agent}")
                return True
        except Exception as e:
            logger.error(f"Failed to delegate task: {e}")
        return False

    def run(self):
        """Main heartbeat loop"""
        print(f"Heartbeat Agent started (interval: {self.interval}s)")
        while self.running:
            todos = self.check_global_todos()
            pending = [t for t in todos if t["status"] == "pending"]

            if pending:
                print(f"Found {len(pending)} pending tasks")
                agent_status = self.check_agent_status()
                idle_agents = [a for a, s in agent_status.items() if s == "idle"]
                for task in pending:
                    if not idle_agents:
                        print("No idle agents available, waiting...")
                        break
                    agent = idle_agents.pop(0)
                    self.delegate_task(task, agent)

            time.sleep(self.interval)


if __name__ == "__main__":
    agent = HeartbeatAgent(interval=10)
    agent.run()
