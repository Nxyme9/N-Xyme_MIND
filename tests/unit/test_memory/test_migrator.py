"""Unit tests for memory.migrator."""

import json
import os
import pytest
import tempfile
from datetime import datetime
from src.memory.migrator import (
    MigrationDB,
    MigrationRecord,
    MigrationStatus,
    MEMORY_DB_PATH,
    NX_OPENMORE_PATH,
    N_XYME_CATALYST_PATH,
)


class TestMigrationRecord:
    def test_migration_record_creation(self):
        record = MigrationRecord(
            id="test-1",
            source="test_source",
            source_type="test_type",
            content="test content",
        )
        assert record.id == "test-1"
        assert record.source == "test_source"
        assert record.source_type == "test_type"
        assert record.content == "test content"
        assert record.embedded is False
        assert record.embedding is None
        assert record.metadata == {}

    def test_migration_record_with_metadata(self):
        record = MigrationRecord(
            id="test-2",
            source="test_source",
            source_type="test_type",
            content="test content",
            metadata={"key": "value"},
        )
        assert record.metadata == {"key": "value"}

    def test_migration_record_with_embedding(self):
        record = MigrationRecord(
            id="test-3",
            source="test_source",
            source_type="test_type",
            content="test content",
            embedded=True,
            embedding=[0.1, 0.2, 0.3],
        )
        assert record.embedded is True
        assert record.embedding == [0.1, 0.2, 0.3]


class TestMigrationStatus:
    def test_migration_status_creation(self):
        status = MigrationStatus(
            source_name="test_source", exists=True, record_count=100, migrated_count=50
        )
        assert status.source_name == "test_source"
        assert status.exists is True
        assert status.record_count == 100
        assert status.migrated_count == 50
        assert status.error is None

    def test_migration_status_with_error(self):
        status = MigrationStatus(
            source_name="test_source",
            exists=True,
            record_count=100,
            migrated_count=0,
            error="Connection failed",
        )
        assert status.error == "Connection failed"


class TestConstants:
    def test_memory_db_path_default(self):
        assert MEMORY_DB_PATH == "./data/memory_migration.db"

    def test_nx_openmore_path_default(self):
        assert NX_OPENMORE_PATH == "/mnt/Library/nx_openmore"

    def test_n_xyme_catalyst_path_default(self):
        assert N_XYME_CATALYST_PATH == "/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST"


class TestMigrationDB:
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_migration_db_init(self, temp_db):
        db = MigrationDB(db_path=temp_db)
        assert db.db_path == temp_db
        assert os.path.exists(temp_db)

    def test_update_status(self, temp_db):
        db = MigrationDB(db_path=temp_db)
        status = MigrationStatus(
            source_name="test_source",
            exists=True,
            record_count=200,
            migrated_count=150,
            error=None,
        )
        db.update_status(status)
        retrieved = db.get_status("test_source")
        assert retrieved is not None
        assert retrieved.record_count == 200
        assert retrieved.migrated_count == 150

    def test_get_status_not_found(self, temp_db):
        db = MigrationDB(db_path=temp_db)
        status = db.get_status("nonexistent")
        assert status is None

    def test_get_all_status_empty(self, temp_db):
        db = MigrationDB(db_path=temp_db)
        statuses = db.get_all_status()
        assert statuses == []

    def test_get_all_status_multiple(self, temp_db):
        db = MigrationDB(db_path=temp_db)
        status1 = MigrationStatus(source_name="source1", exists=True, record_count=100)
        status2 = MigrationStatus(source_name="source2", exists=True, record_count=200)
        db.update_status(status1)
        db.update_status(status2)
        statuses = db.get_all_status()
        assert len(statuses) == 2
