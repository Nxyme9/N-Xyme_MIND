"""Tests for benchmark.py."""

import json
import pytest
import tempfile
from pathlib import Path
from src.intelligence.benchmark import run_benchmark, TEST_CASES


class TestBenchmark:
    def test_run_benchmark(self, tmp_path):
        result = run_benchmark(root_dir=tmp_path, verbose=False)
        assert "total_tests" in result
        assert "passed" in result
        assert "failed" in result
        assert "accuracy" in result
        assert "results" in result
        assert result["total_tests"] == len(TEST_CASES)

    def test_benchmark_saves_file(self, tmp_path):
        result = run_benchmark(root_dir=tmp_path, verbose=False)
        benchmark_dir = tmp_path / ".sisyphus" / "benchmarks"
        assert benchmark_dir.exists()
        json_files = list(benchmark_dir.glob("benchmark-*.json"))
        assert len(json_files) == 1

        with open(json_files[0]) as f:
            saved = json.load(f)
        assert saved["total_tests"] == result["total_tests"]

    def test_benchmark_results_format(self, tmp_path):
        result = run_benchmark(root_dir=tmp_path, verbose=False)
        for r in result["results"]:
            assert "task" in r
            assert "expected_level" in r
            assert "actual_level" in r
            assert "confidence" in r
            assert "reason" in r
            assert "time_ms" in r
            assert "status" in r
            assert r["status"] in ("pass", "fail")

    def test_benchmark_accuracy_calculation(self, tmp_path):
        result = run_benchmark(root_dir=tmp_path, verbose=False)
        expected_accuracy = result["passed"] * 100 // result["total_tests"]
        assert result["accuracy"] == expected_accuracy

    def test_benchmark_timing(self, tmp_path):
        result = run_benchmark(root_dir=tmp_path, verbose=False)
        assert result["total_time_ms"] > 0
        assert result["avg_time_ms"] > 0
        assert result["avg_time_ms"] <= result["total_time_ms"]

    def test_test_cases_count(self):
        assert len(TEST_CASES) == 10

    def test_test_cases_have_required_fields(self):
        for test in TEST_CASES:
            assert "task" in test
            assert "expected_level" in test
            assert "expected_agent" in test
            assert 1 <= test["expected_level"] <= 5
