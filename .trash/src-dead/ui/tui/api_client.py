#!/usr/bin/env python3
"""API Client — Connects TUI to Catalyst REST API"""

import httpx
from typing import Optional, Dict, Any, List

BASE_URL = "http://localhost:8100"  # Catalyst API server


class CatalystAPI:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30)

    def health(self) -> dict:
        return self.client.get(f"{self.base_url}/health").json()

    # Brain
    def route_task(
        self,
        intent_type: str,
        complexity: str = "MED",
        risk: str = "LOW",
        has_fact_claims: bool = False,
    ) -> dict:
        return self.client.post(
            f"{self.base_url}/brain/route",
            json={
                "intent_type": intent_type,
                "complexity": complexity,
                "risk": risk,
                "has_fact_claims": has_fact_claims,
            },
        ).json()

    def classify_claim(self, text: str) -> dict:
        return self.client.post(
            f"{self.base_url}/brain/evidence/classify", json={"text": text}
        ).json()

    def evaluate_verdict(self, claims: list) -> dict:
        return self.client.post(
            f"{self.base_url}/brain/critic/evaluate", json={"claims": claims}
        ).json()

    def select_loop(
        self, task_description: str, intent_type: str = "UNKNOWN", risk: str = "LOW"
    ) -> dict:
        return self.client.post(
            f"{self.base_url}/brain/loop/select",
            json={
                "task_description": task_description,
                "intent_type": intent_type,
                "risk": risk,
            },
        ).json()

    def memory_search(self, query: str, layer: str = "semantic") -> list:
        return self.client.post(
            f"{self.base_url}/brain/memory/search",
            json={"query": query, "layer": layer},
        ).json()

    def memory_store(self, key: str, value: str, layer: str = "working") -> dict:
        return self.client.post(
            f"{self.base_url}/brain/memory/store",
            json={"key": key, "value": value, "layer": layer},
        ).json()

    def memory_stats(self) -> dict:
        return self.client.get(f"{self.base_url}/brain/memory/stats").json()

    # Tool Execution (NEW)
    def execute_message(
        self,
        message: str,
        model: str = "llama3.2:3b",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        """Execute a message through BrainBridge with tool execution.

        Args:
            message: User message to process
            model: Ollama model to use (default: llama3.2:3b)
            conversation_history: Optional list of previous messages

        Returns:
            Dict with type (text/tool_calls), content, and optional executed tools
        """
        payload: Dict[str, Any] = {"message": message, "model": model}
        if conversation_history:
            payload["conversation_history"] = conversation_history

        return self.client.post(f"{self.base_url}/brain/execute", json=payload).json()

    # System
    def pm2_status(self) -> dict:
        return self.client.get(f"{self.base_url}/system/pm2").json()

    def gpu_status(self) -> dict:
        return self.client.get(f"{self.base_url}/system/gpu").json()

    def graphiti_health(self) -> dict:
        return self.client.get(f"{self.base_url}/system/graphiti").json()

    def pm2_restart(self, service: str) -> dict:
        return self.client.post(f"{self.base_url}/system/pm2/restart/{service}").json()

    # Audio
    def generate_audio(
        self, text: str, voice: str = "es-ES-AlvaroNeural", auto_play: bool = True
    ) -> dict:
        return self.client.post(
            f"{self.base_url}/audio/generate",
            json={"text": text, "voice": voice, "auto_play": auto_play},
        ).json()

    def play_audio(self, file_path: str) -> dict:
        return self.client.post(
            f"{self.base_url}/audio/play", json={"file_path": file_path}
        ).json()

    def list_audio(self) -> list:
        return self.client.get(f"{self.base_url}/audio/list").json()

    def list_voices(self) -> list:
        return self.client.get(f"{self.base_url}/audio/voices").json()
