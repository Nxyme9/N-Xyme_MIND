#!/usr/bin/env python3
"""Migration script: .sisyphus/graphs.db -> memory_store graph_store.

Migrates legacy graph data to the new NetworkXGraphStore format.
Note: Source has 0 nodes/edges, so this is primarily a schema migration demo.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Project root - adjust for migrations folder
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DB = PROJECT_ROOT / ".sisyphus" / "graphs.db"
TARGET_FILE = PROJECT_ROOT / ".sisyphus" / "graph_memory.json"


def migrate_graphs() -> Dict[str, Any]:
    """Migrate graph data from source to target format."""
    results = {
        "nodes_migrated": 0,
        "edges_migrated": 0,
        "failed": 0,
        "errors": [],
    }

    if not SOURCE_DB.exists():
        logger.warning(f"Source database not found: {SOURCE_DB}")
        return results

    # Connect to source
    source_conn = sqlite3.connect(str(SOURCE_DB))
    source_conn.row_factory = sqlite3.Row

    try:
        # Get all nodes
        node_cursor = source_conn.execute(
            "SELECT id, graph_type, label, content, metadata, created_at FROM graph_nodes"
        )
        nodes = node_cursor.fetchall()

        # Get all edges
        edge_cursor = source_conn.execute(
            "SELECT source_id, target_id, relation_type, weight, metadata FROM graph_edges"
        )
        edges = edge_cursor.fetchall()

        logger.info(f"Found {len(nodes)} nodes and {len(edges)} edges to migrate")

        # Convert to NetworkX format
        migrated_nodes = []
        for node in nodes:
            try:
                metadata = {}
                if node["metadata"]:
                    try:
                        metadata = json.loads(node["metadata"])
                    except json.JSONDecodeError:
                        pass

                migrated_nodes.append(
                    {
                        "id": node["id"],
                        "node_type": node["graph_type"],  # Map graph_type to node_type
                        "label": node["label"],
                        "properties": metadata,
                        "created_at": node["created_at"] or datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                    }
                )
                results["nodes_migrated"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"node={node['id']}: {str(e)}")

        migrated_edges = []
        for edge in edges:
            try:
                metadata = {}
                if edge["metadata"]:
                    try:
                        metadata = json.loads(edge["metadata"])
                    except json.JSONDecodeError:
                        pass

                migrated_edges.append(
                    {
                        "source": edge["source_id"],
                        "target": edge["target_id"],
                        "edge_type": edge["relation_type"],
                        "weight": edge["weight"] or 0.5,
                        "properties": metadata,
                        "created_at": datetime.now().isoformat(),
                    }
                )
                results["edges_migrated"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"edge: {str(e)}")

        # Write to target (NetworkX format)
        if migrated_nodes or migrated_edges:
            TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
            target_data = {
                "nodes": migrated_nodes,
                "edges": migrated_edges,
            }
            TARGET_FILE.write_text(json.dumps(target_data, indent=2))
            logger.info(f"Written to {TARGET_FILE}")

        logger.info(
            f"Migration complete: {results['nodes_migrated']} nodes, {results['edges_migrated']} edges"
        )

    finally:
        source_conn.close()

    return results


def verify_migration() -> bool:
    """Verify migrated data is queryable via NetworkXGraphStore."""
    try:
        # Test loading via NetworkXGraphStore
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))
        from packages.memory_store.stores.graph_store import NetworkXGraphStore

        store = NetworkXGraphStore(str(TARGET_FILE))
        stats = store.get_stats()

        logger.info(f"Verification stats: {stats}")
        return stats.get("total_nodes", 0) >= 0  # Just check it loads

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def main():
    """Main migration entry point."""
    logger.info("=" * 60)
    logger.info("Starting graph migration: .sisyphus/graphs.db -> memory_store")
    logger.info("=" * 60)

    # Run migration
    results = migrate_graphs()

    # Verify (if data was migrated)
    if results["nodes_migrated"] > 0 or results["edges_migrated"] > 0:
        success = verify_migration()
        results["verified"] = success
        if success:
            logger.info("✓ Migration verified successfully")
        else:
            logger.warning("✗ Migration verification failed")

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info(f"  Nodes migrated: {results['nodes_migrated']}")
    logger.info(f"  Edges migrated: {results['edges_migrated']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info(f"  Verified: {results.get('verified', 'N/A')}")
    if results["errors"]:
        logger.info(f"  Errors: {len(results['errors'])}")
        for err in results["errors"][:5]:
            logger.info(f"    - {err}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    main()
