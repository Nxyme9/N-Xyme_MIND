"""
NxRotator - Maximum Throughput Aggregator
==========================================

Self-learning API key rotation system with:
- Multi-key rotation (6 OpenRouter keys)
- Direct connection (proxies are dead)
- SQLite-based learning from outcomes
- Auto-failover on rate limits (429)
- Real-time metrics dashboard

Usage:
    python -m nx_rotator.cli test
    python -m nx_rotator.cli dashboard
    python -m nx_rotator.cli metrics
"""

from .core.aggregator import NxRotator

__version__ = "1.0.0"
__all__ = ["NxRotator"]
