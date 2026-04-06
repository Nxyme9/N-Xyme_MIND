"""
Ollama Manager — Model lifecycle management for local Ollama inference.

Handles model loading, unloading, health checking, and automatic model
selection based on VRAM availability and demand patterns.

Usage:
    manager = OllamaManager()
    manager.health_check()
    manager.load_model("qwen2.5-coder:7b")
    manager.auto_manage_models(["llama3.2:latest", "qwen2.5-coder:7b"], vram_manager)
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    import urllib.request
    import urllib.error
    import json as _json

    httpx = None

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Metadata about a single Ollama model."""

    name: str
    size: int = 0  # bytes
    digest: str = ""
    modified_at: str = ""
    format: str = ""
    family: str = ""
    parameter_size: str = ""
    quantization_level: str = ""


@dataclass
class LoadedModel:
    """A model currently loaded in VRAM."""

    name: str
    size: int = 0  # bytes
    digest: str = ""
    expires_at: str = ""


class OllamaManager:
    """
    Manages Ollama model lifecycle: load, unload, health, auto-selection.

    Integrates with a VRAM manager for memory-aware decisions.
    All methods handle errors gracefully — never raise on network failures.

    Args:
        ollama_url: Base URL of the Ollama server (default: http://localhost:11434)
        idle_timeout_minutes: Minutes before unused models are eligible for unload (default: 30)

    Example:
        manager = OllamaManager()
        if manager.health_check():
            manager.load_model("qwen2.5-coder:7b")
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        idle_timeout_minutes: int = 30,
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.idle_timeout_minutes = idle_timeout_minutes
        self._client: Optional[Any] = None
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is not None:
                return self._client
            if httpx is not None:
                self._client = httpx.Client(
                    base_url=self.ollama_url,
                    timeout=10.0,
                )
        return self._client

    def _get(self, path: str) -> tuple[bool, Any]:
        """
        Perform a GET request. Returns (success, data_or_error).
        Works with httpx or stdlib urllib.
        """
        url = f"{self.ollama_url}{path}"
        try:
            if httpx is not None:
                client = self._get_client()
                resp = client.get(path)
                resp.raise_for_status()
                return True, resp.json()
            else:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return True, _json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning(f"Ollama GET {url} failed: {exc}")
            return False, str(exc)

    def _post(self, path: str, payload: dict, timeout: int = 30) -> tuple[bool, Any]:
        """
        Perform a POST request. Returns (success, data_or_error).
        Works with httpx or stdlib urllib.
        """
        url = f"{self.ollama_url}{path}"
        try:
            if httpx is not None:
                client = self._get_client()
                resp = client.post(path, json=payload, timeout=timeout)
                resp.raise_for_status()
                return True, resp.json()
            else:
                data = _json.dumps(payload).encode()
                req = urllib.request.Request(
                    url, data=data, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read().decode()
                    return True, _json.loads(body) if body else {}
        except Exception as exc:
            logger.warning(f"Ollama POST {url} failed: {exc}")
            return False, str(exc)

    # ── Public API ──────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """
        Check if the Ollama server is running and reachable.

        Sends GET /api/tags and returns True if the response is 200.

        Returns:
            True if Ollama is healthy, False otherwise.
        """
        ok, _ = self._get("/api/tags")
        if ok:
            logger.info("Ollama health check passed")
        else:
            logger.warning("Ollama health check failed")
        return ok

    def get_loaded_models(self) -> List[LoadedModel]:
        """
        Return models currently loaded in VRAM.

        Sends GET /api/ps and parses the response.

        Returns:
            List of LoadedModel dataclasses. Empty list on failure.
        """
        ok, data = self._get("/api/ps")
        if not ok:
            return []
        models = []
        for entry in (data.get("models") or []):
            models.append(
                LoadedModel(
                    name=entry.get("name", ""),
                    size=entry.get("size", 0),
                    digest=entry.get("digest", ""),
                    expires_at=entry.get("expires_at", ""),
                )
            )
        logger.debug(f"Loaded models: {[m.name for m in models]}")
        return models

    def get_available_models(self) -> List[ModelInfo]:
        """
        Return all models pulled/available on the Ollama server.

        Sends GET /api/tags and parses model metadata.

        Returns:
            List of ModelInfo dataclasses. Empty list on failure.
        """
        ok, data = self._get("/api/tags")
        if not ok:
            return []
        models = []
        for entry in (data.get("models") or []):
            details = entry.get("details", {})
            models.append(
                ModelInfo(
                    name=entry.get("name", ""),
                    size=entry.get("size", 0),
                    digest=entry.get("digest", ""),
                    modified_at=entry.get("modified_at", ""),
                    format=details.get("format", ""),
                    family=details.get("family", ""),
                    parameter_size=details.get("parameter_size", ""),
                    quantization_level=details.get("quantization_level", ""),
                )
            )
        logger.debug(f"Available models: {[m.name for m in models]}")
        return models

    def load_model(self, model: str, keep_alive: str = "-1", timeout: int = 120) -> bool:
        """
        Load a model into VRAM.

        Sends a minimal POST /api/generate request with an empty prompt
        to trigger model loading. The model stays in VRAM per keep_alive.

        Args:
            model: Model name (e.g. "qwen2.5-coder:7b")
            keep_alive: Duration to keep model loaded.
                        "-1" = permanent, "30m" = 30 minutes, "0" = unload after request.
            timeout: Request timeout in seconds (default: 120).

        Returns:
            True if the model loaded successfully, False otherwise.
        """
        logger.info(f"Loading model '{model}' (keep_alive={keep_alive}, timeout={timeout}s)")
        ok, data = self._post(
            "/api/generate",
            {
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": keep_alive,
            },
            timeout=timeout,
        )
        if ok:
            logger.info(f"Model '{model}' loaded successfully")
        else:
            logger.error(f"Failed to load model '{model}': {data}")
        return ok

    def unload_model(self, model: str, timeout: int = 120) -> bool:
        """
        Unload a model from VRAM.

        Sends POST /api/generate with keep_alive=0 to force unloading.

        Args:
            model: Model name to unload.
            timeout: Request timeout in seconds (default: 120).

        Returns:
            True if the model was unloaded (or was not loaded), False on error.
        """
        logger.info(f"Unloading model '{model}' (timeout={timeout}s)")
        ok, data = self._post(
            "/api/generate",
            {
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
            timeout=timeout,
        )
        if ok:
            logger.info(f"Model '{model}' unloaded")
        else:
            logger.error(f"Failed to unload model '{model}': {data}")
        return ok

    def ensure_model_loaded(self, model: str) -> bool:
        """
        Check if a model is loaded; load it if not.

        Args:
            model: Model name to ensure is in VRAM.

        Returns:
            True if the model is loaded after this call, False otherwise.
        """
        loaded = self.get_loaded_models()
        loaded_names = {m.name for m in loaded}

        if model in loaded_names:
            logger.debug(f"Model '{model}' already loaded")
            return True

        logger.info(f"Model '{model}' not loaded — loading now")
        return self.load_model(model)

    def get_model_info(self, model: str) -> dict:
        """
        Return detailed metadata for a specific model.

        Sends POST /api/show to get model size, parameters, template, etc.

        Args:
            model: Model name to inspect.

        Returns:
            Dict with model metadata. Empty dict on failure.
        """
        ok, data = self._post("/api/show", {"model": model})
        if not ok:
            logger.warning(f"Could not get info for model '{model}': {data}")
            return {}

        result = {
            "name": model,
            "model_info": data.get("model_info", {}),
            "parameters": data.get("parameters", ""),
            "template": data.get("template", ""),
            "modelfile": data.get("modelfile", ""),
        }
        return result

    def auto_manage_models(
        self,
        required_models: List[str],
        vram_manager: Optional[Any] = None,
    ) -> dict:
        """
        Intelligently manage models based on requirements and VRAM.

        Loads all required models that fit in VRAM.
        Unloads models that are loaded but not required.
        If VRAM is insufficient, loads models in priority order.

        Args:
            required_models: List of model names that must be loaded.
            vram_manager: Optional object with methods:
                - get_total_vram() -> int (bytes)
                - get_used_vram() -> int (bytes)
                - get_available_vram() -> int (bytes)
                If None, loads all required models without memory checks.

        Returns:
            Dict with keys:
                - loaded: list of models successfully loaded
                - unloaded: list of models successfully unloaded
                - skipped: list of models that could not be loaded (VRAM full)
                - errors: list of error messages
        """
        result: Dict[str, list] = {
            "loaded": [],
            "unloaded": [],
            "skipped": [],
            "errors": [],
        }

        if not self.health_check():
            result["errors"].append("Ollama server is not running")
            return result

        currently_loaded = self.get_loaded_models()
        loaded_names = {m.name for m in currently_loaded}
        loaded_sizes = {m.name: m.size for m in currently_loaded}

        required_set = set(required_models)

        # ── Unload models that are no longer required ──────────────
        for model_name in loaded_names:
            if model_name not in required_set:
                if self.unload_model(model_name):
                    result["unloaded"].append(model_name)
                    logger.info(f"Auto-manage: unloaded unused model '{model_name}'")
                else:
                    result["errors"].append(f"Failed to unload '{model_name}'")

        # ── Load required models ──────────────────────────────────
        for model_name in required_models:
            if model_name in loaded_names and model_name not in result["unloaded"]:
                result["loaded"].append(model_name)
                continue

            model_size = self._estimate_model_size(model_name)

            if vram_manager is not None:
                available = self._get_vram_available(vram_manager)
                if model_size > available:
                    result["skipped"].append(model_name)
                    result["errors"].append(
                        f"Insufficient VRAM for '{model_name}': "
                        f"need {model_size:,} bytes, have {available:,} bytes"
                    )
                    logger.warning(
                        f"Skipping '{model_name}' — not enough VRAM "
                        f"(need {model_size:,}, have {available:,})"
                    )
                    continue

            if self.load_model(model_name):
                result["loaded"].append(model_name)
            else:
                result["skipped"].append(model_name)
                result["errors"].append(f"Failed to load '{model_name}'")

        logger.info(
            f"Auto-manage complete: "
            f"loaded={result['loaded']}, unloaded={result['unloaded']}, "
            f"skipped={result['skipped']}"
        )
        return result

    # ── Internal helpers ────────────────────────────────────────────────

    def _estimate_model_size(self, model: str) -> int:
        """
        Estimate model size in bytes.
        Tries /api/show first, falls back to known defaults.
        """
        info = self.get_model_info(model)
        model_info = info.get("model_info", {})
        size = model_info.get("total_size", 0)
        if size > 0:
            return size

        defaults = {
            "llama3.2:latest": 2_000_000_000,
            "llama3.2:1b": 1_300_000_000,
            "llama3.2:3b": 2_000_000_000,
            "qwen2.5-coder:7b": 4_700_000_000,
            "qwen2.5-coder:1.5b": 1_000_000_000,
            "qwen3:8b": 5_000_000_000,
            "qwen3:1.7b": 1_100_000_000,
            "llava:7b": 4_700_000_000,
            "llava:13b": 8_000_000_000,
            "deepseek-r1:free": 4_700_000_000,
            "mimo-v2-pro-free": 8_000_000_000,
        }
        default_size = defaults.get(model, 4_000_000_000)
        if model not in defaults:
            logger.warning(
                "Unknown model '%s' — using default size %.1f GB",
                model,
                default_size / 1_000_000_000,
            )
        return default_size

    @staticmethod
    def _get_vram_available(vram_manager: Any) -> int:
        """Safely query available VRAM from a manager object."""
        for method_name in ("get_available_vram", "available_vram", "free_vram"):
            method = getattr(vram_manager, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception as exc:
                    logger.warning(f"VRAM manager.{method_name}() failed: {exc}")
        return 0

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "OllamaManager":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("Ollama Manager — Demo")
    print("=" * 60)

    with OllamaManager() as manager:
        print(f"\n1. Health check (Ollama at {manager.ollama_url})")
        healthy = manager.health_check()
        print(f"   Status: {'ONLINE' if healthy else 'OFFLINE'}")

        if not healthy:
            print("\n   Ollama is not running. Start it with:")
            print("   ollama serve")
            print(
                "\n   The module is still functional — it will work once Ollama is up."
            )

        print("\n2. Available models")
        available = manager.get_available_models()
        if available:
            for m in available:
                size_mb = m.size / (1024 * 1024) if m.size else "?"
                print(f"   - {m.name} ({size_mb} MB, {m.parameter_size})")
        else:
            print("   (none — or Ollama is offline)")

        print("\n3. Currently loaded models")
        loaded = manager.get_loaded_models()
        if loaded:
            for m in loaded:
                size_mb = m.size / (1024 * 1024) if m.size else "?"
                print(f"   - {m.name} ({size_mb} MB, expires: {m.expires_at})")
        else:
            print("   (none loaded)")

        print("\n4. Model info for 'llama3.2:latest'")
        info = manager.get_model_info("llama3.2:latest")
        if info:
            print(f"   Name: {info['name']}")
            print(f"   Parameters: {info.get('parameters', 'N/A')}")
        else:
            print("   (unavailable)")

        print("\n5. Auto-manage demo (require llama3.2:latest)")
        result = manager.auto_manage_models(["llama3.2:latest"])
        print(f"   Loaded:   {result['loaded']}")
        print(f"   Unloaded: {result['unloaded']}")
        print(f"   Skipped:  {result['skipped']}")
        if result["errors"]:
            print(f"   Errors:   {result['errors']}")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)
