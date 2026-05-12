from typing import Any

import requests


class AthenaClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def _get(self, endpoint: str) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=2)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "offline"}

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}", json=data, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def get_health(self) -> dict[str, Any]:
        """Check system health."""
        return self._get("/health")

    def get_active_context(self) -> str:
        """Retrieve active context content."""
        data = self._get("/context/active")
        return data.get("content", "Error loading context.")

    def think(self, prompt: str) -> dict[str, Any]:
        """Send a thought to the agent."""
        return self._post("/agent/think", {"prompt": prompt})
