# Memory Panel
"""Memory system panel content generator."""

from typing import Any


def get_content(dashboard: Any) -> str:
    """Get memory panel content.

    Args:
        dashboard: Dashboard instance with live_data attribute

    Returns:
        Panel content string
    """
    d = dashboard.live_data
    m = d.get("memory", {})
    idx = d.get("indexed", {})
    router = d.get("router", {})

    content = f"""MEMORY SYSTEM (58 modules)

Core Components
  Sources: {m.get("total_sources", 0)} | Enabled: {m.get("enabled_count", 0)} | Failed: {m.get("failed_count", 0)}
  Files: {idx.get("total_files", 0)} | Chunks: {idx.get("indexed_chunks", idx.get("total_chunks", 0))}
  Router Backends: {router.get("backends", 0)} | {", ".join(router.get("backend_names", [])[:5])}

By Drive:"""
    for k, v in idx.get("by_drive", {}).items():
        content += f"\n  - {k}: {v}"

    content += "\n\nBy Type:"
    for k, v in idx.get("by_type", {}).items():
        content += f"\n  - {k}: {v}"

    content += f"""

Knowledge Graph: {d.get("kg_entities", 0)} entities, {d.get("kg_relationships", 0)} relationships
Priority Engine: {d.get("priority_count", 0)} items | Projects: {", ".join(d.get("priority_projects", [])[:5])}

Modules (58):
  Core: mcp_server.py, mcp_server_v2.py, daemon.py, config.py, registry.py
  Storage: vector_index.py (34 funcs), knowledge_graph.py (24 funcs), priority_engine.py (21 funcs)
  Connectors: connectors.py (20 funcs), file_connector.py, file_content_connector.py
  Indexing: embeddings.py (16 funcs), embedding_pipeline.py (15 funcs), indexer.py, drive_embedder.py
  Memory Types: semantic.py, episodic.py, working.py, procedural.py, memory_types.py
  Scanning: drive_scanner.py, multi_drive_scanner.py, scan_scheduler.py, scan_config.py, file_watcher.py
  Retrieval: memory_relevance.py, memory_extractor.py, content_extractor.py, content_extractors.py
  Health: health_monitor.py, self_healer.py, auto_recovery.py, integrity_checker.py
  Lifecycle: retention_policy.py, memory_age.py, memory_freshness.py, session_lifecycle.py, sleep_engine.py
  Advanced: synthesizer.py, topic_model.py, context_awareness.py, activity_tracker.py, preference_model.py
  Events: event_log.py, event_bus_consumer.py
  Migration: migrator.py (60 funcs), migration_runner.py
  File Registry: file_registry.py, metadata_extractor.py, memory_files.py, file_rr.py"""

    return content
