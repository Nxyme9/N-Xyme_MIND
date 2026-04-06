"""Memory Migration Framework.

Ported from ant-source-code-main/migrations/
Provides a structured migration system for memory databases.
Each migration is a Python module with up() and down() functions.

Pattern: Migrations are stored in src/memory/migrations/ and are
applied in order based on their filename prefix (001_*, 002_*, etc.).
Migration state is tracked in a _migrations table in each database.
"""

from __future__ import annotations

import importlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """A single database migration."""

    id: int
    name: str
    up: Callable[[sqlite3.Connection], None]
    down: Callable[[sqlite3.Connection], None]
    applied_at: str | None = None


@dataclass
class MigrationResult:
    """Result of running migrations."""

    applied: int
    skipped: int
    errors: list[str]
    total_time_ms: float


class MigrationRunner:
    """Runs database migrations in order."""

    def __init__(self, db_path: Path, migrations_dir: Path | None = None):
        """Initialize migration runner.

        Args:
            db_path: Path to the SQLite database.
            migrations_dir: Directory containing migration modules.
                Defaults to src/memory/migrations/
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir or (Path(__file__).parent / "migrations")
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Create _migrations table if it doesn't exist."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def get_applied_migrations(self) -> list[tuple[int, str, str]]:
        """Get list of already applied migrations."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT id, name, applied_at FROM _migrations ORDER BY id"
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def discover_migrations(self) -> list[Migration]:
        """Discover migration modules in the migrations directory."""
        migrations = []

        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        applied = {row[0] for row in self.get_applied_migrations()}

        for filepath in sorted(self.migrations_dir.glob("*.py")):
            if filepath.name.startswith("_"):
                continue

            # Parse migration ID from filename (001_add_table.py → 1)
            try:
                migration_id = int(filepath.name.split("_")[0])
            except (ValueError, IndexError):
                logger.warning(f"Skipping invalid migration filename: {filepath.name}")
                continue

            if migration_id in applied:
                continue

            name = filepath.stem
            module_name = f"src.memory.migrations.{filepath.stem}"

            try:
                module = importlib.import_module(module_name)
                up_fn = getattr(module, "up", None)
                down_fn = getattr(module, "down", None)

                if up_fn is None:
                    logger.warning(f"Migration {name} has no up() function")
                    continue

                migrations.append(
                    Migration(
                        id=migration_id,
                        name=name,
                        up=up_fn,
                        down=down_fn or (lambda conn: None),
                    )
                )
            except ImportError as e:
                logger.warning(f"Failed to import migration {name}: {e}")

        return migrations

    def run_migrations(self, target: int | None = None) -> MigrationResult:
        """Run all pending migrations up to target.

        Args:
            target: Migration ID to run up to (None = all).

        Returns:
            MigrationResult with counts and any errors.
        """
        import time

        start = time.time() * 1000

        migrations = self.discover_migrations()
        if target is not None:
            migrations = [m for m in migrations if m.id <= target]

        applied = 0
        skipped = 0
        errors = []

        for migration in migrations:
            try:
                logger.info(f"Applying migration: {migration.name}")
                conn = sqlite3.connect(str(self.db_path))
                try:
                    migration.up(conn)
                    conn.execute(
                        "INSERT INTO _migrations (id, name, applied_at) VALUES (?, ?, ?)",
                        (
                            migration.id,
                            migration.name,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    conn.commit()
                    applied += 1
                    logger.info(f"Applied migration: {migration.name}")
                except Exception as e:
                    conn.rollback()
                    error_msg = f"Migration {migration.name} failed: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    break  # Stop on first error
                finally:
                    conn.close()
            except Exception as e:
                error_msg = f"Failed to run migration {migration.name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                break

        elapsed = time.time() * 1000 - start

        return MigrationResult(
            applied=applied,
            skipped=skipped,
            errors=errors,
            total_time_ms=elapsed,
        )

    def rollback_migration(self, migration_id: int) -> bool:
        """Rollback a specific migration.

        Args:
            migration_id: ID of the migration to rollback.

        Returns:
            True if rollback succeeded, False otherwise.
        """
        migrations = self.discover_migrations()
        migration = next((m for m in migrations if m.id == migration_id), None)

        if migration is None:
            # Try to load the migration module directly
            for filepath in self.migrations_dir.glob("*.py"):
                try:
                    mid = int(filepath.name.split("_")[0])
                    if mid == migration_id:
                        module_name = f"src.memory.migrations.{filepath.stem}"
                        module = importlib.import_module(module_name)
                        down_fn = getattr(module, "down", None)
                        if down_fn is None:
                            logger.warning(
                                f"Migration {filepath.stem} has no down() function"
                            )
                            return False
                        migration = Migration(
                            id=mid,
                            name=filepath.stem,
                            up=lambda conn: None,
                            down=down_fn,
                        )
                        break
                except (ValueError, IndexError, ImportError):
                    continue

        if migration is None:
            logger.error(f"Migration {migration_id} not found")
            return False

        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                migration.down(conn)
                conn.execute("DELETE FROM _migrations WHERE id = ?", (migration_id,))
                conn.commit()
                logger.info(f"Rolled back migration: {migration.name}")
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Rollback failed: {e}")
                return False
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get migration status summary."""
        applied = self.get_applied_migrations()
        pending = self.discover_migrations()

        return {
            "database": str(self.db_path),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": [
                {"id": r[0], "name": r[1], "applied_at": r[2]} for r in applied
            ],
            "pending": [{"id": m.id, "name": m.name} for m in pending],
        }
