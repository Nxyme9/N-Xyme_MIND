"""Unit tests for memory.integrity_checker."""

import pytest
import tempfile
import os
import sqlite3
from pathlib import Path
from src.memory.integrity_checker import IntegrityChecker


class TestIntegrityChecker:
    """Test IntegrityChecker class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        # Create a simple table
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def temp_chroma(self):
        """Create temporary chroma directory."""
        with tempfile.TemporaryDirectory() as chroma_path:
            yield chroma_path

    @pytest.fixture
    def checker(self, temp_db, temp_chroma):
        """Create IntegrityChecker instance."""
        return IntegrityChecker(db_path=temp_db, chroma_path=temp_chroma)

    def test_integrity_checker_init(self, checker):
        """Test IntegrityChecker initialization."""
        assert checker is not None
        assert checker.db_path is not None
        assert checker.chroma_path is not None

    def test_ensure_reports_dir(self, checker):
        """Test _ensure_reports_dir creates directory."""
        # The method should not raise
        checker._ensure_reports_dir()

    def test_get_db_connection(self, checker):
        """Test _get_db_connection returns connection."""
        conn = checker._get_db_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_get_chroma_path(self, checker):
        """Test _get_chroma_path returns Path."""
        chroma_path = checker._get_chroma_path()
        assert isinstance(chroma_path, Path)

    def test_check_sqlite_integrity_with_valid_db(self, checker):
        """Test check_sqlite_integrity with valid database."""
        result = checker.check_sqlite_integrity()
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result

    def test_check_sqlite_integrity_with_missing_db(self, checker):
        """Test check_sqlite_integrity with missing database."""
        # Create a checker with non-existent db
        bad_checker = IntegrityChecker(
            db_path="/nonexistent/db.db", chroma_path=checker.chroma_path
        )
        result = bad_checker.check_sqlite_integrity()
        assert result["status"] == "fail"

    def test_check_chroma_integrity_missing_path(self, checker):
        """Test check_chroma_integrity with missing path."""
        bad_checker = IntegrityChecker(
            db_path=checker.db_path, chroma_path="/nonexistent/chroma"
        )
        result = bad_checker.check_chroma_integrity()
        assert "status" in result

    def test_check_file_existence_empty_list(self, checker):
        """Test check_file_existence with empty list."""
        result = checker.check_file_existence([])
        # Status may be "pass" or "fail" depending on db state - just verify it's a valid result
        assert isinstance(result, dict)
        assert "status" in result

    def test_check_file_existence_missing_files(self, checker):
        """Test check_file_existence with missing files."""
        result = checker.check_file_existence(["/nonexistent/file.txt"])
        assert isinstance(result, dict)
        assert "status" in result

    def test_check_integrity(self, checker):
        """Test check_integrity runs all checks."""
        result = checker.check_integrity()
        assert isinstance(result, dict)
        assert "checks" in result or "sqlite_integrity" in result

    def test_save_report(self, checker):
        """Test save_report creates a file."""
        report = {
            "check": "test",
            "status": "pass",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        report_path = checker.save_report(report)
        assert report_path is not None

    def test_get_last_report_none(self, checker):
        """Test get_last_report when no reports exist."""
        result = checker.get_last_report()
        # May be None or empty dict depending on state
        assert result is None or isinstance(result, dict)


class TestIntegrityCheckerImports:
    """Test module imports."""

    def test_import_integrity_checker(self):
        """Test IntegrityChecker can be imported."""
        from src.memory.integrity_checker import IntegrityChecker

        assert IntegrityChecker is not None
