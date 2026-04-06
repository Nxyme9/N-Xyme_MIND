#!/usr/bin/env python3
"""Test graceful degradation when Ollama is down.

Covers:
1) local-router.py is_local_available() returns False
2) model-fallback.py skips local and goes to cloud fallback
3) model-selector.py --local shows warning
4) model-router.py routes to cloud when local unavailable
"""

import importlib.util
import json
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "bin"))

# Load local-router module
_local_router_spec = importlib.util.spec_from_file_location(
    "local_router_degradation",
    os.path.join(PROJECT_ROOT, "bin", "local-router.py"),
)
_local_router_mod = importlib.util.module_from_spec(_local_router_spec)
sys.modules["local_router_degradation"] = _local_router_mod
_local_router_spec.loader.exec_module(_local_router_mod)
LocalRouter = _local_router_mod.LocalRouter

# Load model-fallback module
_fallback_spec = importlib.util.spec_from_file_location(
    "model_fallback_degradation",
    os.path.join(PROJECT_ROOT, "bin", "model-fallback.py"),
)
_fallback_mod = importlib.util.module_from_spec(_fallback_spec)
sys.modules["model_fallback_degradation"] = _fallback_mod
_fallback_spec.loader.exec_module(_fallback_mod)
ModelFallback = _fallback_mod.ModelFallback


def _run_main_with_args(module, args, monkeypatch):
    """Run a module's main() with patched sys.argv and captured stdout."""
    monkeypatch.setattr(sys, "argv", [module.__file__ or "script"] + args)
    captured = StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    try:
        module.main()
    except SystemExit:
        pass
    return captured.getvalue()


class TestLocalRouterOllamaDown:
    """Test 1: local-router.py is_local_available() returns False when Ollama is down."""

    @pytest.fixture
    def router(self):
        return LocalRouter(ollama_url="http://localhost:11434")

    @patch("local_router_degradation.requests.get")
    def test_is_local_available_returns_false_on_connection_refused(self, mock_get, router):
        import requests as req
        mock_get.side_effect = req.ConnectionError("Connection refused")
        assert router.is_local_available() is False
        mock_get.assert_called_once()

    @patch("local_router_degradation.requests.get")
    def test_is_local_available_returns_false_on_timeout(self, mock_get, router):
        import requests as req
        mock_get.side_effect = req.Timeout()
        assert router.is_local_available() is False

    @patch("local_router_degradation.requests.get")
    def test_is_local_available_returns_false_on_503(self, mock_get, router):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        assert router.is_local_available() is False

    @patch("local_router_degradation.requests.get")
    def test_is_local_available_returns_false_on_request_exception(self, mock_get, router):
        import requests as req
        mock_get.side_effect = req.RequestException("Ollama not running")
        assert router.is_local_available() is False

    @patch("local_router_degradation.requests.get")
    def test_cli_health_exits_1_when_ollama_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        captured = StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        monkeypatch.setattr(sys, "argv", ["local-router.py", "--health"])
        with pytest.raises(SystemExit) as exc_info:
            _local_router_mod.main()
        assert exc_info.value.code == 1
        assert "unavailable" in captured.getvalue().lower()

    @patch("local_router_degradation.requests.get")
    def test_cli_health_json_shows_false_when_ollama_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        captured = StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        monkeypatch.setattr(sys, "argv", ["local-router.py", "--health", "--format", "json"])
        with pytest.raises(SystemExit):
            _local_router_mod.main()
        data = json.loads(captured.getvalue())
        assert data["available"] is False


class TestModelFallbackSkipsLocal:
    """Test 2: model-fallback.py skips local and goes to cloud fallback when Ollama is down."""

    @pytest.fixture
    def minimal_config(self):
        return {
            "openrouter/deepseek/deepseek-r1": {
                "name": "DeepSeek R1",
                "tier": "Premium",
                "api_key_env": "OPENROUTER_API_KEY",
                "base_url": "https://openrouter.ai/api/v1",
                "timeout": 60,
            },
            "opencode/qwen3.6-plus-free": {
                "name": "Qwen3.6 Plus",
                "tier": "Zen",
                "api_key_env": "OPENCODE_API_KEY",
                "base_url": "https://api.opencode.ai/v1",
                "timeout": 60,
            },
            "ollama/llama3.2:3b": {
                "name": "Llama 3.2 3B",
                "tier": "Local",
                "api_key_env": "OLLAMA_API_KEY",
                "base_url": "http://localhost:11434/v1",
                "timeout": 60,
            },
        }

    @patch.object(ModelFallback, "_load_local_router")
    def test_fallback_skips_local_when_unavailable(self, mock_load_local, minimal_config):
        mock_local_router = MagicMock()
        mock_local_router.is_local_available.return_value = False
        mock_module = MagicMock()
        mock_module.LocalRouter.return_value = mock_local_router
        mock_load_local.return_value = mock_module

        fallback = ModelFallback(model_config=minimal_config)

        call_order = []

        def mock_call_side_effect(model, prompt):
            call_order.append(model)
            return {"success": True, "response": "cloud response", "model": model}

        with patch.object(fallback, "_validate_api_key", return_value=True), \
             patch.object(fallback, "call_model", side_effect=mock_call_side_effect):
            result = fallback.call_with_fallback(
                "simple task",
                model_list=["openrouter/deepseek/deepseek-r1", "opencode/qwen3.6-plus-free"],
            )

            mock_local_router.is_local_available.assert_called_once()
            assert result["success"] is True
            assert "openrouter/deepseek/deepseek-r1" in call_order

    @patch.object(ModelFallback, "_load_local_router")
    def test_fallback_logs_local_unavailable(self, mock_load_local, minimal_config, caplog):
        mock_local_router = MagicMock()
        mock_local_router.is_local_available.return_value = False
        mock_module = MagicMock()
        mock_module.LocalRouter.return_value = mock_local_router
        mock_load_local.return_value = mock_module

        fallback = ModelFallback(model_config=minimal_config)

        with patch.object(fallback, "_validate_api_key", return_value=True), \
             patch.object(fallback, "call_model") as mock_call:
            mock_call.return_value = {"success": True, "response": "ok", "model": "opencode/qwen3.6-plus-free"}
            with caplog.at_level("INFO"):
                fallback.call_with_fallback("hello", model_list=["opencode/qwen3.6-plus-free"])

        assert any("local" in msg.lower() and "not available" in msg.lower() for msg in caplog.messages)

    @patch.object(ModelFallback, "_load_local_router")
    def test_fallback_proceeds_with_cloud_only_when_all_local_fail(self, mock_load_local, minimal_config):
        mock_local_router = MagicMock()
        mock_local_router.is_local_available.return_value = True
        mock_local_router.classify.return_value = "simple"
        mock_local_router.get_local_models.return_value = ["llama3.2:3b"]
        mock_module = MagicMock()
        mock_module.LocalRouter.return_value = mock_local_router
        mock_load_local.return_value = mock_module

        fallback = ModelFallback(model_config=minimal_config)

        def mock_call_side_effect(model, prompt):
            if model.startswith("ollama/"):
                raise Exception("Connection refused")
            return {"success": True, "response": "cloud response", "model": model}

        with patch.object(fallback, "_validate_api_key", return_value=True), \
             patch.object(fallback, "call_model", side_effect=mock_call_side_effect):
            result = fallback.call_with_fallback(
                "simple task",
                model_list=["ollama/llama3.2:3b", "opencode/qwen3.6-plus-free"],
            )

            assert result["success"] is True
            assert "opencode/qwen3.6-plus-free" in result["model"]


class TestModelSelectorLocalWarning:
    """Test 3: model-selector.py --local shows warning when Ollama is down."""

    def _load_selector_module(self):
        spec = importlib.util.spec_from_file_location(
            "model_selector_deg",
            os.path.join(PROJECT_ROOT, "bin", "model-selector.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["model_selector_deg"] = mod
        sys.modules["local_router"] = _local_router_mod
        spec.loader.exec_module(mod)
        return mod

    @patch("local_router_degradation.requests.get")
    def test_selector_local_flag_falls_back_to_cloud_when_ollama_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_selector_module()
        monkeypatch.setattr(mod, "local_router", None)
        monkeypatch.setenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free")
        output = _run_main_with_args(mod, ["--local", "--task", "explain this code"], monkeypatch)
        assert "opencode/minimax-m2.5-free" in output.strip()

    @patch("local_router_degradation.requests.get")
    def test_selector_local_json_shows_local_unavailable(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_selector_module()
        monkeypatch.setattr(mod, "local_router", None)
        output = _run_main_with_args(mod, ["--local", "--task", "fix bug", "--format", "json"], monkeypatch)
        data = json.loads(output)
        assert data["local_available"] is False
        assert data["local"] is True

    @patch("local_router_degradation.requests.get")
    def test_selector_offline_flag_uses_ollama_model_even_when_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_selector_module()
        output = _run_main_with_args(mod, ["--offline", "--task", "explain this", "--format", "json"], monkeypatch)
        data = json.loads(output)
        assert "ollama" in data["model"]


class TestModelRouterCloudFallback:
    """Test 4: model-router.py routes to cloud when local unavailable."""

    def _load_router_module(self):
        spec = importlib.util.spec_from_file_location(
            "model_router_deg",
            os.path.join(PROJECT_ROOT, "bin", "model-router.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["model_router_deg"] = mod
        sys.modules["local_router"] = _local_router_mod
        spec.loader.exec_module(mod)
        return mod

    @patch("local_router_degradation.requests.get")
    def test_router_routes_to_cloud_when_local_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_router_module()
        monkeypatch.setenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free")
        output = _run_main_with_args(mod, ["--task", "explain this function", "--format", "json"], monkeypatch)
        data = json.loads(output)
        assert data["local"] is False
        assert "minimax-m2.5-free" in data["model"]

    @patch("local_router_degradation.requests.get")
    def test_router_rules_shows_local_unavailable(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_router_module()
        output = _run_main_with_args(mod, ["--rules", "--format", "json"], monkeypatch)
        data = json.loads(output)
        assert data["local"]["available"] is False

    @patch("local_router_degradation.requests.get")
    def test_router_medium_task_routes_to_cloud_when_local_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_router_module()
        monkeypatch.setenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
        output = _run_main_with_args(mod, ["--task", "fix this bug in the code", "--format", "json"], monkeypatch)
        data = json.loads(output)
        assert data["local"] is False

    @patch("local_router_degradation.requests.get")
    def test_router_text_output_no_local_routing_when_down(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()
        mod = self._load_router_module()
        output = _run_main_with_args(mod, ["--task", "explain this"], monkeypatch)
        assert "Local routing" not in output


class TestGracefulDegradationIntegration:
    """Integration tests: full degradation chain when Ollama is down."""

    def _load_selector_module(self):
        spec = importlib.util.spec_from_file_location(
            "model_selector_deg_int",
            os.path.join(PROJECT_ROOT, "bin", "model-selector.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["model_selector_deg_int"] = mod
        sys.modules["local_router"] = _local_router_mod
        spec.loader.exec_module(mod)
        return mod

    def _load_router_module(self):
        spec = importlib.util.spec_from_file_location(
            "model_router_deg_int",
            os.path.join(PROJECT_ROOT, "bin", "model-router.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["model_router_deg_int"] = mod
        sys.modules["local_router"] = _local_router_mod
        spec.loader.exec_module(mod)
        return mod

    @patch("local_router_degradation.requests.get")
    def test_full_chain_local_down_all_components_agree(self, mock_get, monkeypatch):
        import requests as req
        mock_get.side_effect = req.ConnectionError()

        router = LocalRouter(ollama_url="http://localhost:11434")
        assert router.is_local_available() is False

        selector_mod = self._load_selector_module()
        monkeypatch.setattr(selector_mod, "local_router", None)
        selector_output = _run_main_with_args(
            selector_mod, ["--local", "--task", "explain this", "--format", "json"], monkeypatch,
        )
        selector_data = json.loads(selector_output)
        assert selector_data["local_available"] is False

        router_mod = self._load_router_module()
        router_output = _run_main_with_args(
            router_mod, ["--task", "explain this", "--format", "json"], monkeypatch,
        )
        router_data = json.loads(router_output)
        assert router_data["local"] is False

    @patch.object(ModelFallback, "_load_local_router")
    def test_fallback_circuit_breaker_records_local_failure(self, mock_load_local):
        mock_local_router = MagicMock()
        mock_local_router.is_local_available.return_value = True
        mock_local_router.classify.return_value = "simple"
        mock_local_router.get_local_models.return_value = ["llama3.2:3b"]
        mock_module = MagicMock()
        mock_module.LocalRouter.return_value = mock_local_router
        mock_load_local.return_value = mock_module

        fallback = ModelFallback(model_config={
            "ollama/llama3.2:3b": {
                "name": "Llama 3.2 3B",
                "tier": "Local",
                "api_key_env": None,
                "base_url": "http://localhost:11434/v1",
                "timeout": 60,
            },
        })

        with patch.object(fallback, "call_model", side_effect=Exception("Connection refused")):
            fallback.call_with_fallback("simple task", model_list=["ollama/llama3.2:3b"])

        assert fallback.circuit_breaker.failures.get("ollama/llama3.2:3b", 0) >= 1
