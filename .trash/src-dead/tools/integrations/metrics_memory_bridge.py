"""
Metrics-Memory Bridge — Connects MetricsStore to memory bank files.

Usage:
    from src.integrations.metrics_memory_bridge import log_metric_to_context, get_metrics_summary, sync_metrics_to_memory

    log_metric_to_context("tokens_used", 1500, "sisyphus")
    summary = get_metrics_summary()
    sync_metrics_to_memory()
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.infrastructure.metrics_store import MetricsStore, get_store

logger = logging.getLogger(__name__)

MEMORY_BANK_DIR = Path(".context/memory_bank")
ACTIVE_CONTEXT_FILE = MEMORY_BANK_DIR / "activeContext.md"


def _get_memory_bank_path(filename: str) -> Path:
    """Get the path to a memory bank file."""
    return MEMORY_BANK_DIR / filename


def _read_memory_file(filename: str) -> Optional[str]:
    """Read content from a memory bank file."""
    path = _get_memory_bank_path(filename)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {filename}: {e}")
    return None


def _write_memory_file(filename: str, content: str) -> bool:
    """Write content to a memory bank file."""
    path = _get_memory_bank_path(filename)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Failed to write {filename}: {e}")
        return False


def log_metric_to_context(
    metric_name: str, value: float, source: str = "system", session_id: str = ""
) -> bool:
    """
    Log a metric to both MetricsStore and memory bank context.

    Args:
        metric_name: Name of the metric (e.g., 'tokens_used', 'latency').
        value: Numeric value of the metric.
        source: Source of the metric (e.g., agent name).
        session_id: Optional session identifier.

    Returns:
        True if logged successfully to both systems.
    """
    store = get_store()
    record_id = store.record_metric(source, metric_name, value, session_id)

    active_context = _read_memory_file("activeContext.md")
    if active_context is None:
        active_context = """---
created: {date}
type: active_context
status: active
---

# Active Context

Project: N-Xyme_MIND
Phase: Development
""".format(date=datetime.now().strftime("%Y-%m-%d"))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = f"- **{timestamp}** [{source}] {metric_name}: {value}\n"

    if "## Recent Metrics" in active_context:
        parts = active_context.split("## Recent Metrics")
        updated = parts[0] + "## Recent Metrics\n" + new_entry + "\n" + parts[1][:500]
    else:
        updated = active_context + f"\n## Recent Metrics\n{new_entry}"

    written = _write_memory_file("activeContext.md", updated)

    if record_id and written:
        logger.info(f"Logged metric: {source}/{metric_name}={value}")
        return True

    return False


def get_metrics_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get a summary of metrics from the store.

    Args:
        hours: Number of hours to look back (default 24).

    Returns:
        Dictionary with metrics summary.
    """
    store = get_store()

    stats = store.get_stats()
    recent_metrics = store.query_metrics(hours=hours)

    sources = set(m.get("source") for m in recent_metrics)
    metrics_by_type = {}
    for m in recent_metrics:
        metric = m.get("metric", "unknown")
        metrics_by_type[metric] = metrics_by_type.get(metric, 0) + 1

    total_value = sum(m.get("value", 0) for m in recent_metrics)

    return {
        "period_hours": hours,
        "total_records": stats.get("metrics", 0),
        "recent_count": len(recent_metrics),
        "sources": list(sources),
        "metrics_by_type": metrics_by_type,
        "total_value": round(total_value, 2),
        "avg_value": round(total_value / len(recent_metrics), 2)
        if recent_metrics
        else 0,
    }


def sync_metrics_to_memory() -> bool:
    """
    Sync current metrics state to memory bank files.

    This function updates memory bank files with current metrics
    for cross-session context awareness.

    Returns:
        True if sync was successful.
    """
    summary = get_metrics_summary(hours=24)

    sync_content = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
type: metrics_sync
---

# Metrics Sync

**Period**: Last {summary["period_hours"]} hours
**Total Records**: {summary["total_records"]}
**Recent Metrics**: {summary["recent_count"]}
**Sources**: {", ".join(summary["sources"]) or "none"}

## By Type
"""
    for metric_type, count in summary.get("metrics_by_type", {}).items():
        sync_content += f"- {metric_type}: {count}\n"

    sync_content += f"""
## Summary
- Total Value: {summary["total_value"]}
- Average: {summary["avg_value"]}
"""

    success = _write_memory_file("metrics_sync.md", sync_content)

    if success:
        logger.info("Metrics synced to memory bank")

    return success


def get_store() -> MetricsStore:
    """Get or create the metrics store instance."""
    return get_store()
