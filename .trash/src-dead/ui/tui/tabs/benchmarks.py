"""Benchmarks tab - benchmark history and results."""

import json
from pathlib import Path

# Import from parent module
_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    content = "═══ BENCHMARK HISTORY ═══\n\n"

    # Load benchmark files
    bench_files = sorted(Path(".sisyphus/benchmarks").glob("benchmark-*.json"))

    if not bench_files:
        content += "  No benchmarks recorded yet\n"
        return content

    content += "▸ RECENT RUNS\n"
    for bf in bench_files[-5:]:
        try:
            data = json.loads(bf.read_text())
            ts = bf.name.replace("benchmark-", "").replace(".json", "")[:8]
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            total = passed + failed
            rate = (passed / total * 100) if total > 0 else 0
            content += f"  {ts}  {passed}/{total} passed ({rate:.0f}%)\n"
        except (json.JSONDecodeError, OSError):
            pass

    # Get latest benchmark details
    if bench_files:
        latest = bench_files[-1]
        try:
            data = json.loads(latest.read_text())
            content += "\n▸ LATEST DETAILS\n"
            content += f"  Tests: {data.get('passed', 0)} passed, {data.get('failed', 0)} failed\n"
            content += f"  Duration: {data.get('duration_ms', 0):.0f}ms\n"
            content += f"  Timestamp: {data.get('timestamp', 'N/A')[:19]}\n"
        except (json.JSONDecodeError, OSError):
            pass

    content += "\n═══ QUICK ACTIONS ═══\n"
    content += "  [R] Run benchmark    [L] View last results\n"

    return content
