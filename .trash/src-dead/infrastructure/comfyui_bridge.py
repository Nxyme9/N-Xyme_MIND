"""ComfyUI Bridge — AI image generation pipeline"""

import json, logging, httpx
from typing import Dict, List

logger = logging.getLogger(__name__)


class ComfyUIBridge:
    def __init__(self, api_url: str = "http://127.0.0.1:8188"):
        self.api_url = api_url
        self._http_client = None

    def _get_client(self, timeout: float = 30.0) -> httpx.Client:
        """Get or create persistent HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=timeout)
        return self._http_client

    def close(self):
        """Cleanup HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()

    def queue_prompt(self, workflow: Dict) -> Dict:
        try:
            client = self._get_client()
            resp = client.post(f"{self.api_url}/prompt", json={"prompt": workflow})
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_history(self, prompt_id: str) -> Dict:
        try:
            client = self._get_client()
            resp = client.get(f"{self.api_url}/history/{prompt_id}")
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_image(self, filename: str, subfolder: str = "", type: str = "output") -> bytes:
        try:
            client = self._get_client()
            resp = client.get(
                f"{self.api_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": type},
            )
            return resp.content
        except Exception as e:
            return b""

    def list_models(self) -> List[str]:
        try:
            client = self._get_client(timeout=10.0)
            resp = client.get(f"{self.api_url}/object_info")
            return list(resp.json().keys())
        except Exception:
            return []
