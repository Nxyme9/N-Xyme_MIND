"""Generative UI — AI component generation"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class GenerativeUI:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.ollama_url = ollama_url
        self.model = model

    def generate_component(self, description: str, framework: str = "react") -> Dict:
        try:
            import httpx

            prompt = f"Generate a {framework} component for: {description}. Return only code, no explanation."
            client = httpx.Client(timeout=60)
            resp = client.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            code = resp.json().get("response", "")
            return {"code": code, "framework": framework, "description": description}
        except Exception as e:
            return {"error": str(e)}

    def suggest_layout(self, components: list) -> Dict:
        return {"suggestion": "grid", "columns": min(3, len(components)), "components": components}
