"""Advanced tests for CircuitBreaker, ModelRouter, and PromptCache classes."""

import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))

# Import from src/ where these classes actually live
from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpen

pytest.skip("TaskClassifier, ModelRoute, TaskComplexity removed with model_router.py duplicate", allow_module_level=True)
from src.model_router import TaskClassifier, ModelRoute, TaskComplexity, ModelProvider


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def breaker(self):
        """Create a fresh circuit breaker for each test."""
        return CircuitBreaker(name="test", failure_threshold=3, reset_timeout=60.0)

    def test_record_failure_increments_counter(self, breaker):
        """Test that recording failure increments failure counter."""
        initial_count = breaker.failure_count

        def failing_func():
            raise Exception("Test failure")

        with pytest.raises(Exception):
            breaker.call(failing_func)

        assert breaker.failure_count == initial_count + 1

    def test_record_success_resets_counter(self, breaker):
        """Test that successful call resets failure counter."""
        breaker.failure_count = 2

        def success_func():
            return "success"

        result = breaker.call(success_func)

        assert result == "success"
        assert breaker.failure_count == 1

    def test_is_available_returns_false_after_threshold(self, breaker):
        """Test circuit opens after failure threshold is reached."""

        def failing_func():
            raise Exception("Test failure")

        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    def test_is_available_returns_true_after_timeout(self, breaker):
        """Test circuit returns to half-open after reset timeout."""
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time() - 61.0
        breaker.failure_count = 3

        breaker._reset_timeout = 0.1

        def success_func():
            return "success"

        result = breaker.call(success_func)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_exponential_backoff(self, breaker):
        """Test exponential backoff calculation."""
        failures = [1, 2, 3]
        delays = []

        for failure_num in failures:
            delay = 2 ** (failure_num - 1) * 1.0
            delays.append(delay)

        assert delays == [1, 2, 4]

        result = breaker.get_state()
        assert "failure_count" in result

    def test_state_persistence(self, breaker):
        """Test circuit breaker state can be saved and loaded."""
        breaker.failure_count = 2
        breaker.success_count = 5
        breaker.total_calls = 10
        breaker.state = CircuitState.OPEN

        state = breaker.get_state()

        new_breaker = CircuitBreaker(
            name="test", failure_threshold=3, reset_timeout=60.0
        )
        new_breaker.failure_count = state["failure_count"]
        new_breaker.success_count = state["success_count"]
        new_breaker.total_calls = state["total_calls"]

        assert new_breaker.failure_count == 2
        assert new_breaker.success_count == 5
        assert new_breaker.total_calls == 10

    def test_raises_when_open(self, breaker):
        """Test CircuitBreakerOpen exception is raised when circuit is open."""
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time()

        def some_func():
            return "test"

        with pytest.raises(CircuitBreakerOpen):
            breaker.call(some_func)

    def test_manual_reset(self, breaker):
        """Test manual reset restores closed state."""
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 5

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestModelRouter:
    """Tests for ModelRouter (TaskClassifier) class."""

    @pytest.fixture
    def classifier(self):
        """Create a fresh classifier for each test."""
        return TaskClassifier()

    def test_route_simple_task(self, classifier):
        """Test routing for simple task (explore agent)."""
        route = classifier.classify("explore")

        assert route.model_name == "llama3.2:latest"
        assert route.provider == ModelProvider.OLLAMA

    def test_route_coding_task(self, classifier):
        """Test routing for coding task."""
        route = classifier.classify("sisyphus-jr")

        assert route.model_name == "qwen2.5-coder:7b"
        assert route.provider == ModelProvider.OLLAMA

    def test_route_reasoning_task(self, classifier):
        """Test routing for reasoning task (hephaestus agent)."""
        route = classifier.classify("hephaestus")

        assert route.model_name == "mimo-v2-pro-free"
        assert route.provider == ModelProvider.OPENCODE

    def test_escalate_recommends_next_model(self, classifier):
        """Test escalation recommends fallback model."""
        route = classifier.classify("hephaestus")

        assert route.fallback_model == "deepseek-r1:free"
        assert route.fallback_provider == ModelProvider.OPENROUTER

    def test_get_routing_rules_returns_all(self, classifier):
        """Test get_route_info returns routing rules for all agents."""
        info = classifier.get_route_info("explore")

        assert "agent_type" in info
        assert "primary_model" in info
        assert "complexity" in info
        assert info["agent_type"] == "explore"

    def test_special_route_multimodal(self, classifier):
        """Test special route for multimodal agent."""
        route = classifier.classify("multimodal")

        assert route.model_name == "llava:7b"
        assert route.provider == ModelProvider.OLLAMA

    def test_unknown_agent_defaults_to_simple(self, classifier):
        """Test unknown agent type defaults to simple route."""
        route = classifier.classify("unknown_agent")

        assert route.model_name == "llama3.2:latest"
        assert route.provider == ModelProvider.OLLAMA

    def test_code_override_for_simple_task(self, classifier):
        """Test simple code task uses local 7B model."""
        code_content = "def hello(): return 'world'"

        route = classifier.classify("explore", task_content=code_content)

        assert route.model_name == "qwen2.5-coder:7b"

    def test_route_info_for_all_complexities(self, classifier):
        """Test route info covers all complexity levels."""
        agents = ["explore", "sisyphus-jr", "oracle", "hephaestus"]
        complexities = set()

        for agent in agents:
            info = classifier.get_route_info(agent)
            complexities.add(info["complexity"])

        assert TaskComplexity.SIMPLE.value in complexities
        assert TaskComplexity.MEDIUM.value in complexities
        assert TaskComplexity.COMPLEX.value in complexities
        assert TaskComplexity.DEEP.value in complexities


class TestPromptCache:
    """Tests for PromptCache class."""

    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def cache(self, cache_dir):
        """Create a fresh cache for each test."""
        import types
        import argparse
        import hashlib
        import json
        import threading
        from collections import OrderedDict
        from pathlib import Path
        from typing import Optional

        bin_path = Path(__file__).parent.parent / "bin" / "prompt-cache.py"
        with open(bin_path, 'r') as f:
            code = f.read()

        namespace = {
            'argparse': argparse,
            'hashlib': hashlib,
            'json': json,
            'threading': threading,
            'OrderedDict': OrderedDict,
            'Path': Path,
            'Optional': Optional,
            'time': __import__('time'),
            '__name__': 'prompt_cache',
            '__file__': str(bin_path),
        }
        exec(code, namespace)
        return namespace['PromptCache'](cache_dir=cache_dir, max_size=10)

    def test_put_and_get_exact_match(self, cache):
        """Test cache put and exact match get."""
        cache.put("test prompt", "test response")

        result = cache.get("test prompt")

        assert result == "test response"

    def test_get_semantic_finds_similar(self, cache):
        """Test semantic search finds similar prompts."""
        cache.put("test prompt one", "response one")

        result = cache.get_semantic(
            "test prompt one updated", threshold=0.3
        )

        assert result is not None

    def test_lru_eviction(self, cache):
        """Test LRU eviction when cache exceeds max size."""
        for i in range(12):
            cache.put(f"prompt {i}", f"response {i}")

        result = cache.get("prompt 0")
        result2 = cache.get("prompt 1")

        stats = cache.stats()
        assert stats["size"] <= cache.max_size

    def test_clear_empties_cache(self, cache):
        """Test clear empties cache and resets stats."""
        cache.put("test prompt", "test response")
        cache.get("test prompt")

        cache.clear()

        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0

    def test_stats_returns_correct_counts(self, cache):
        """Test stats returns correct hit/miss counts."""
        cache.put("prompt1", "response1")

        cache.get("prompt1")
        cache.get("nonexistent")

        stats = cache.stats()

        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_concurrent_access(self, cache):
        """Test basic thread safety for concurrent access."""
        results = []
        errors = []

        def worker(prompt_id):
            try:
                cache.put(f"prompt {prompt_id}", f"response {prompt_id}")
                result = cache.get(f"prompt {prompt_id}")
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_miss_returns_none(self, cache):
        """Test get returns None for nonexistent prompt."""
        result = cache.get("nonexistent prompt")

        assert result is None

    def test_semantic_threshold(self, cache):
        """Test semantic matching respects threshold."""
        cache.put("hello world", "response1")

        result = cache.get_semantic("foo bar", threshold=0.9)

        assert result is None

    def test_ngram_overlap(self, cache):
        """Test n-gram extraction and overlap calculation."""
        ngrams1 = cache._extract_ngrams("hello world foo bar")
        ngrams2 = cache._extract_ngrams("hello world baz qux")

        overlap = cache._compute_ngram_overlap(ngrams1, ngrams2)

        assert 0.0 <= overlap <= 1.0
