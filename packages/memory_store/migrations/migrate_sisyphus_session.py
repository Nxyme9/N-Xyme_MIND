#!/usr/bin/env python3
"""Migrate session data from .sisyphus to memory_store.

This script migrates:
- state.db (sessions, delegations, agent_performance, results)
- context.db (session_context, session_summary)
- messages.db

Uses dual-write pattern: writes to both legacy .sisyphus (read-only)
and new memory_store during transition.
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from packages.memory_store.stores.session_store import SessionStore

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Source databases - use correct paths
STATE_DB = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.sisyphus/state.db")
CONTEXT_DB = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.sisyphus/context.db")
MESSAGES_DB = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.sisyphus/messages.db")


def migrate_state_db(store: SessionStore) -> dict:
    """Migrate state.db tables."""
    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row

    counts = {}

    # Migrate sessions
    cursor = conn.execute("SELECT * FROM sessions")
    sessions = cursor.fetchall()
    for row in sessions:
        store.store_session(dict(row), dual_write=True)
    counts["sessions"] = len(sessions)
    logger.info(f"Migrated {len(sessions)} sessions")

    # Migrate delegations
    cursor = conn.execute("SELECT * FROM delegations")
    delegations = cursor.fetchall()
    for row in delegations:
        store.store_delegation(dict(row), dual_write=True)
    counts["delegations"] = len(delegations)
    logger.info(f"Migrated {len(delegations)} delegations")

    # Migrate agent_performance
    cursor = conn.execute("SELECT * FROM agent_performance")
    perfs = cursor.fetchall()
    for row in perfs:
        store.store_agent_performance(dict(row))
    counts["agent_performance"] = len(perfs)
    logger.info(f"Migrated {len(perfs)} agent_performance records")

    # Migrate results
    cursor = conn.execute("SELECT * FROM results")
    results = cursor.fetchall()
    for row in results:
        store.store_result(dict(row))
    counts["results"] = len(results)
    logger.info(f"Migrated {len(results)} results")

    conn.close()
    return counts


def migrate_context_db(store: SessionStore) -> dict:
    """Migrate context.db tables."""
    conn = sqlite3.connect(str(CONTEXT_DB))
    conn.row_factory = sqlite3.Row

    counts = {}

    # Migrate session_context
    cursor = conn.execute("SELECT * FROM session_context")
    contexts = cursor.fetchall()
    for row in contexts:
        store.store_session_context(dict(row))
    counts["session_context"] = len(contexts)
    logger.info(f"Migrated {len(contexts)} session_context records")

    # Migrate session_summary
    cursor = conn.execute("SELECT * FROM session_summary")
    summaries = cursor.fetchall()
    for row in summaries:
        store.store_session_summary(dict(row))
    counts["session_summary"] = len(summaries)
    logger.info(f"Migrated {len(summaries)} session_summary records")

    conn.close()
    return counts


def migrate_messages_db(store: SessionStore) -> dict:
    """Migrate messages.db tables."""
    conn = sqlite3.connect(str(MESSAGES_DB))
    conn.row_factory = sqlite3.Row

    # Migrate messages
    cursor = conn.execute("SELECT * FROM messages")
    messages = cursor.fetchall()
    for row in messages:
        store.store_message(dict(row))
    counts = {"messages": len(messages)}
    logger.info(f"Migrated {len(messages)} messages")

    conn.close()
    return counts


def verify_migration(store: SessionStore, source_counts: dict) -> bool:
    """Verify row counts match source."""
    stats = store.stats()

    logger.info("=== Migration Verification ===")
    all_match = True

    for table, expected in source_counts.items():
        actual = stats.get(f"{table}_count", 0)
        status = "✓" if actual == expected else "✗"
        logger.info(f"  {table}: {actual}/{expected} {status}")
        if actual != expected:
            all_match = False

    return all_match


def main():
    """Main migration entry point."""
    logger.info("=== Starting Phase 2 Migration ===")
    logger.info("Source databases:")
    logger.info(f"  - state.db: {STATE_DB}")
    logger.info(f"  - context.db: {CONTEXT_DB}")
    logger.info(f"  - messages.db: {MESSAGES_DB}")

    # Initialize SessionStore
    store = SessionStore()

    # Get source counts for verification
    source_counts = {}

    # Count source records
    for db_path, tables in [
        (STATE_DB, ["sessions", "delegations", "agent_performance", "results"]),
        (CONTEXT_DB, ["session_context", "session_summary"]),
        (MESSAGES_DB, ["messages"]),
    ]:
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    source_counts[table] = count
                except Exception as e:
                    logger.warning(f"Could not count {table}: {e}")
            conn.close()

    logger.info(f"Source counts: {source_counts}")

    # Run migrations
    logger.info("\n=== Migrating state.db ===")
    counts = migrate_state_db(store)

    logger.info("\n=== Migrating context.db ===")
    counts.update(migrate_context_db(store))

    logger.info("\n=== Migrating messages.db ===")
    counts.update(migrate_messages_db(store))

    # Verify
    logger.info("\n=== Verification ===")
    if verify_migration(store, source_counts):
        logger.info("✓ Migration verification PASSED")
    else:
        logger.warning("✗ Migration verification FAILED - counts don't match")

    # Final stats
    logger.info("\n=== Final Statistics ===")
    stats = store.stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("\n=== Phase 2 Migration Complete ===")
    logger.info(
        "Dual-write enabled: All data written to both .sisyphus (read-only) and memory_store"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
