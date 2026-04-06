"""Tests for bin/model_config.py - under 100 lines."""

import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))
from model_config import ModelConfig


@pytest.fixture(autouse=True)
def clean_env():
    orig = {
        k: os.environ.get(k)
        for k in [
            "OLLAMA_MODEL",
            "DEFAULT_CODING_MODEL",
            "PRIMARY_MODEL",
            "FALLBACK_MODEL",
            "OFFLINE_MODEL",
        ]
    }
    for k in orig:
        if orig[k] is None:
            os.environ.pop(k, None)
    yield
    for k, v in orig.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class TestDefaults:
    def test_default_ollama(self):
        assert ModelConfig().OLLAMA_MODEL == "llama3.2:3b"

    def test_default_coding(self):
        assert ModelConfig().DEFAULT_CODING_MODEL == "qwen2.5-coder:7b"

    def test_default_primary(self):
        assert ModelConfig().PRIMARY_MODEL == "opencode/qwen3.6-plus-free"

    def test_default_fallback(self):
        assert ModelConfig().FALLBACK_MODEL == "opencode/minimax-m2.5-free"

    def test_default_offline(self):
        assert ModelConfig().OFFLINE_MODEL == "ollama/llama3.2:3b"


class TestEnvOverrides:
    def test_override_single(self):
        os.environ["OLLAMA_MODEL"] = "custom:latest"
        assert ModelConfig().OLLAMA_MODEL == "custom:latest"

    def test_override_multiple(self):
        os.environ["PRIMARY_MODEL"] = "custom/primary"
        os.environ["FALLBACK_MODEL"] = "custom/fallback"
        c = ModelConfig()
        assert c.PRIMARY_MODEL == "custom/primary"
        assert c.FALLBACK_MODEL == "custom/fallback"


class TestGetModel:
    def test_coding(self):
        assert ModelConfig().get_model("coding") == "qwen2.5-coder:7b"

    def test_simple(self):
        assert ModelConfig().get_model("simple") == "opencode/qwen3.6-plus-free"

    def test_complex(self):
        assert ModelConfig().get_model("complex") == "opencode/qwen3.6-plus-free"

    def test_offline(self):
        assert ModelConfig().get_model("offline") == "ollama/llama3.2:3b"

    def test_default(self):
        assert ModelConfig().get_model("default") == "opencode/qwen3.6-plus-free"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            ModelConfig().get_model("invalid")

    def test_case_insensitive(self):
        c = ModelConfig()
        assert c.get_model("CODING") == c.get_model("coding")


class TestToDict:
    def test_all_keys(self):
        d = ModelConfig().to_dict()
        assert set(d.keys()) == {
            "OLLAMA_MODEL",
            "DEFAULT_CODING_MODEL",
            "PRIMARY_MODEL",
            "FALLBACK_MODEL",
            "OFFLINE_MODEL",
        }


class TestValidate:
    def test_valid_true(self):
        assert ModelConfig().validate() is True

    def test_empty_false(self, clean_env):
        os.environ["PRIMARY_MODEL"] = ""
        assert ModelConfig().validate() is False
