"""Tests for metrics collector."""

import time
import pytest

from src.tools.observability.metrics import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)


@pytest.fixture(autouse=True)
def reset_collector():
    reset_metrics_collector()
    yield
    reset_metrics_collector()


class TestMetricsCollector:
    def test_counter_inc(self):
        mc = MetricsCollector()
        mc.counter_inc("test_counter")
        mc.counter_inc("test_counter")
        mc.counter_inc("test_counter", 5)

        assert mc._counters["test_counter"] == 7

    def test_gauge_set(self):
        mc = MetricsCollector()
        mc.gauge_set("test_gauge", 42.0)
        assert mc._gauges["test_gauge"] == 42.0

    def test_gauge_inc_dec(self):
        mc = MetricsCollector()
        mc.gauge_set("queue_depth", 5)
        mc.gauge_inc("queue_depth", 2)
        assert mc._gauges["queue_depth"] == 7
        mc.gauge_dec("queue_depth", 3)
        assert mc._gauges["queue_depth"] == 4

    def test_histogram_observe(self):
        mc = MetricsCollector()
        for i in range(10):
            mc.histogram_observe("latency", float(i))

        stats = mc.get_histogram_stats("latency")
        assert stats is not None
        assert stats["count"] == 10
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0
        assert stats["avg"] == 4.5

    def test_histogram_max_limit(self):
        mc = MetricsCollector()
        mc._histogram_max["limited"] = 5
        for i in range(20):
            mc.histogram_observe("limited", float(i))

        assert len(mc._histograms["limited"]) == 5

    def test_timer(self):
        mc = MetricsCollector()
        mc.timer_start("delegation")
        time.sleep(0.01)
        latency = mc.timer_stop("delegation")

        assert latency is not None
        assert latency >= 0.01
        stats = mc.get_histogram_stats("delegation_latency_seconds")
        assert stats is not None
        assert stats["count"] == 1

    def test_timer_stop_without_start(self):
        mc = MetricsCollector()
        result = mc.timer_stop("nonexistent")
        assert result is None

    def test_record_delegation_success(self):
        mc = MetricsCollector()
        mc.record_delegation(
            agent="hephaestus",
            level="L3",
            success=True,
            tokens=5000,
            cost=0.01,
        )

        assert mc._counters["delegations_success_total"] == 1
        assert mc._counters["delegations_total"] == 1
        assert mc._counters["delegations_hephaestus_total"] == 1
        assert mc._counters["delegations_L3_total"] == 1
        assert mc._counters["tokens_total"] == 5000
        assert mc._counters["cost_total"] == 0.01

    def test_record_delegation_failure(self):
        mc = MetricsCollector()
        mc.record_delegation(
            agent="explore",
            level="L2",
            success=False,
        )

        assert mc._counters["delegations_failure_total"] == 1
        assert mc._counters["delegations_total"] == 1

    def test_record_api_error(self):
        mc = MetricsCollector()
        mc.record_api_error("hephaestus", "timeout")

        assert mc._counters["api_errors_total"] == 1
        assert mc._counters["api_errors_timeout_total"] == 1
        assert mc._counters["api_errors_hephaestus_total"] == 1

    def test_set_queue_depth(self):
        mc = MetricsCollector()
        mc.set_queue_depth(10)
        assert mc._gauges["queue_depth"] == 10

    def test_get_all_metrics(self):
        mc = MetricsCollector()
        mc.counter_inc("counter_a", 10)
        mc.gauge_set("gauge_b", 5.5)
        mc.histogram_observe("hist_c", 1.0)
        mc.histogram_observe("hist_c", 2.0)

        metrics = mc.get_all_metrics()
        assert metrics["counters"]["counter_a"] == 10
        assert metrics["gauges"]["gauge_b"] == 5.5
        assert "hist_c" in metrics["histograms"]

    def test_export_prometheus(self):
        mc = MetricsCollector()
        mc.record_delegation("hephaestus", "L3", True, tokens=1000)
        mc.record_delegation("explore", "L2", False)
        mc.record_api_error("hephaestus", "timeout")
        mc.set_queue_depth(3)
        mc.histogram_observe("latency", 0.5)

        output = mc.export_prometheus()

        assert "delegations_total 2" in output
        assert "delegations_success_total 1" in output
        assert "delegations_failure_total 1" in output
        assert 'delegations_by_agent_total{agent="hephaestus"} 1' in output
        assert 'delegations_by_agent_total{agent="explore"} 1' in output
        assert "tokens_total 1000" in output
        assert "api_errors_total 1" in output
        assert 'api_errors_by_type_total{type="timeout"} 1' in output
        assert "queue_depth 3" in output
        assert "latency_count 1" in output
        assert "latency_sum 0.5" in output
        assert "# HELP" in output
        assert "# TYPE" in output

    def test_empty_prometheus_export(self):
        mc = MetricsCollector()
        output = mc.export_prometheus()

        assert "delegations_total 0" in output
        assert "delegations_success_total 0" in output
        assert "delegations_failure_total 0" in output
        assert "tokens_total 0" in output
        assert "cost_total 0" in output
        assert "api_errors_total 0" in output
        assert "queue_depth 0" in output


class TestMetricsCollectorSingleton:
    def test_get_metrics_collector_returns_singleton(self):
        mc1 = get_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is mc2

    def test_reset_metrics_collector(self):
        mc1 = get_metrics_collector()
        reset_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is not mc2
