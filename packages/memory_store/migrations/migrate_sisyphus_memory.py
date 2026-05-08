#!/usr/bin/env python3
"""Migration script: .sisyphus/memory.db -> memory_store.

Migrates legacy memory data to the new memory_store schema.
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
SOURCE_DB = PROJECT_ROOT / ".sisyphus" / "memory.db"
TARGET_DB = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"


def generate_memory_id(original_id: int, content: str) -> str:
    """Generate a unique memory ID from original ID and content hash."""
    import hashlib

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"legacy_memory_{original_id}_{content_hash}"


def migrate_memories() -> Dict[str, Any]:
    """Migrate memories from source to target database."""
    results = {
        "migrated": 0,
        "failed": 0,
        "errors": [],
    }

    if not SOURCE_DB.exists():
        logger.warning(f"Source database not found: {SOURCE_DB}")
        return results

    # Connect to source
    source_conn = sqlite3.connect(str(SOURCE_DB))
    source_conn.row_factory = sqlite3.Row

    # Connect to target
    target_conn = sqlite3.connect(str(TARGET_DB))
    target_conn.row_factory = sqlite3.Row

    try:
        # Get all memories from source
        cursor = source_conn.execute(
            "SELECT id, content, kind, scope, metadata_json, created_at FROM memories"
        )
        rows = cursor.fetchall()

        logger.info(f"Found {len(rows)} memories to migrate")

        for row in rows:
            try:
                # Generate new ID (target uses TEXT PRIMARY KEY)
                memory_id = generate_memory_id(row["id"], row["content"])

                # Parse metadata
                metadata = {}
                if row["metadata_json"]:
                    try:
                        metadata = json.loads(row["metadata_json"])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata for id={row['id']}")

                # Add migration source info
                metadata["migrated_from"] = "sisyphus_memory"
                metadata["original_id"] = row["id"]
                metadata["migration_timestamp"] = datetime.now().isoformat()

                # Insert into target (use target's schema)
                target_conn.execute(
                    """INSERT INTO memories 
                       (id, content, kind, scope, tier, meta_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (
                        memory_id,
                        row["content"],
                        row["kind"],
                        row["scope"],
                        "short_term",  # Default tier
                        json.dumps(metadata),
                        row["created_at"],
                    ),
                )
                results["migrated"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"id={row['id']}: {str(e)}")
                logger.error(f"Failed to migrate memory id={row['id']}: {e}")

        target_conn.commit()
        logger.info(
            f"Migration complete: {results['migrated']} migrated, {results['failed']} failed"
        )

    finally:
        source_conn.close()
        target_conn.close()

    return results


def verify_migration(migrated_count: int) -> bool:
    """Verify migrated data is queryable."""
    try:
        target_conn = sqlite3.connect(str(TARGET_DB))
        target_conn.row_factory = sqlite3.Row

        # Check migrated memories
        cursor = target_conn.execute(
            """SELECT COUNT(*) as cnt FROM memories 
               WHERE meta_json LIKE '%sisyphus_memory%'"""
        )
        row = cursor.fetchone()
        found_count = row["cnt"] if row else 0

        # Sample a few records
        cursor = target_conn.execute(
            """SELECT id, content, kind, scope, meta_json FROM memories 
               WHERE meta_json LIKE '%sisyphus_memory%' LIMIT 3"""
        )
        samples = cursor.fetchall()

        target_conn.close()

        logger.info(f"Verification: Found {found_count} migrated memories")
        for sample in samples:
            logger.info(
                f"  Sample: id={sample['id'][:40]}..., kind={sample['kind']}, scope={sample['scope']}"
            )

        return found_count == migrated_count

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def main():
    """Main migration entry point."""
    logger.info("=" * 60)
    logger.info("Starting memory migration: .sisyphus/memory.db -> memory_store")
    logger.info("=" * 60)

    # Run migration
    results = migrate_memories()

    # Verify
    if results["migrated"] > 0:
        success = verify_migration(results["migrated"])
        results["verified"] = success
        if success:
            logger.info("✓ Migration verified successfully")
        else:
            logger.warning("✗ Migration verification mismatch")

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info(f"  Migrated: {results['migrated']}")
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
