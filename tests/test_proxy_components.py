"""Comprehensive tests for all proxy components."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.proxy.api_key_pool import APIKey, APIKeyPool, api_key_pool
from src.infrastructure.proxy.vpn_ip_pool import VPNIP, VPNIPPool, vpn_ip_pool
from src.infrastructure.proxy.router_brain import RouterBrain, router_brain, MODEL_CAPABILITIES
from src.infrastructure.proxy.cost_optimizer import CostTracker, cost_tracker
from src.infrastructure.proxy.learning_engine import LearningEngine, learning_engine
from src.infrastructure.proxy.intelligent_router import IntelligentRouter, intelligent_router


class TestAPIKeyPool:
    def test_add_and_get_key(self):
        pool = APIKeyPool()
        pool.add_key("test", "sk-test-123", rpm=60)
        key = pool.get_best_key("test")
        assert key is not None
        assert key.key == "sk-test-123"

    def test_rate_limiting(self):
        key = APIKey("test", "sk-test", rpm_limit=2)
        key.record_request(100)
        key.record_request(100)
        assert not key.is_available()

    def test_cooldown_on_failure(self):
        key = APIKey("test", "sk-test")
        key.record_failure("rate_limit")
        assert key.cooldown_until > time.time()

    def test_recovery_after_cooldown(self):
        key = APIKey("test", "sk-test")
        key.record_failure("rate_limit")
        key.cooldown_until = time.time() - 1
        assert key.is_available()

    def test_rotate_on_429(self):
        pool = APIKeyPool()
        pool.add_key("test", "sk-1", rpm=60)
        pool.add_key("test", "sk-2", rpm=60)
        key1 = pool.get_best_key("test")
        next_key = pool.rotate_on_429("test", key1)
        assert next_key is not None
        assert next_key is not key1


class TestVPNIPPool:
    def test_add_and_get_ip(self):
        pool = VPNIPPool()
        pool.add_ip("127.0.0.1", 1080, "test")
        ip = pool.get_best_ip()
        assert ip is not None
        assert ip.port == 1080

    def test_ban_on_403(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("403")
        assert ip.is_banned
        assert not ip.is_available()

    def test_cooldown_on_429(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("429")
        assert ip.cooldown_until > time.time()

    def test_recovery_after_cooldown(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_failure("429")
        ip.cooldown_until = time.time() - 1
        assert ip.is_available()

    def test_latency_tracking(self):
        ip = VPNIP("127.0.0.1", 1080, "test")
        ip.record_success(100.0)
        ip.record_success(200.0)
        assert ip.avg_latency_ms > 0
        assert ip.total_successes == 2


class TestRouterBrain:
    def test_detect_coding(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Write a Python function")
        assert "coding" in cats

    def test_detect_reasoning(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Explain why this works")
        assert "reasoning" in cats

    def test_detect_creative(self):
        brain = RouterBrain()
        cats = brain._detect_categories("Write a short story")
        assert "creative" in cats

    def test_complexity_short(self):
        brain = RouterBrain()
        assert brain._estimate_complexity("What is 2+2?") == "simple"

    def test_complexity_long(self):
        brain = RouterBrain()
        long = "Analyze the security implications of JWT in microservices with distributed tracing"
        assert brain._estimate_complexity(long) == "complex"

    def test_analyze_request(self):
        brain = RouterBrain()
        decision = brain.analyze_request("Write a Python function")
        assert "best_model" in decision
        assert "categories" in decision
        assert "complexity" in decision

    def test_model_capabilities(self):
        assert "qwen3.6-plus" in MODEL_CAPABILITIES
        assert "minimax-m2.5" in MODEL_CAPABILITIES


class TestCostOptimizer:
    def test_record_usage(self):
        tracker = CostTracker()
        tracker.record_usage("test", 100, 50, 500.0, True)
        stats = tracker.get_model_stats("test")
        assert stats["total_requests"] == 1
        assert stats["success_rate"] == 1.0

    def test_select_cheapest(self):
        tracker = CostTracker()
        tracker.record_usage("model-a", 100, 50, 100.0, True)
        best = tracker.select_cheapest(min_quality=0.5)
        assert best is not None

    def test_free_models_zero_cost(self):
        tracker = CostTracker()
        for model in ["qwen3.6-plus", "minimax-m2.5"]:
            stats = tracker.get_model_stats(model)
            assert stats["cost_per_1m_input"] == 0.0


class TestLearningEngine:
    def test_record_outcome(self):
        engine = LearningEngine(db_path="/tmp/test_learn.db")
        engine.record_outcome(123, "coding", "medium", "qwen3.6-plus", "opencode", "127.0.0.1:1080", 100, 50, 500.0, True)
        stats = engine.get_stats()
        assert stats["total_requests"] >= 1

    def test_get_best_model(self):
        engine = LearningEngine(db_path="/tmp/test_learn2.db")
        for _ in range(10):
            engine.record_outcome(123, "coding", "medium", "qwen3.6-plus", "opencode", "127.0.0.1:1080", 100, 50, 500.0, True, quality_score=0.9)
        best = engine.get_best_model_for("coding", "medium")
        assert best is not None


class TestIntelligentRouter:
    def test_select_route(self):
        router = IntelligentRouter()
        route = router.select_route("Write a Python function")
        assert "model" in route
        assert "provider" in route
        assert "vpn_ip" in route
        assert "analysis" in route

    def test_record_success(self):
        router = IntelligentRouter()
        route = router.select_route("Test")
        router.record_success(route, 100, 50, 500.0)
        assert router._request_count >= 1

    def test_record_failure(self):
        router = IntelligentRouter()
        route = router.select_route("Test")
        router.record_failure(route, "rate_limit", 100.0)
        assert router._request_count >= 1

    def test_get_status(self):
        router = IntelligentRouter()
        status = router.get_status()
        assert "total_requests" in status
        assert "vpn_ips" in status
        assert "learning" in status
