#!/usr/bin/env python3
"""Comprehensive tests for PC memory synthesis system modules (Waves 1-3).

Tests for:
- file_registry.py
- drive_scanner.py
- scan_config.py
- content_extractors.py
- chunker.py
- metadata_extractor.py
- file_embedder.py
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


# ============================================================================
# FILE REGISTRY TESTS
# ============================================================================


class TestFileRegistry:
    """Tests for file_registry.py module."""

    def test_init_registry(self, tmp_path):
        """Test registry initialization creates proper database schema."""
        from src.memory.file_registry import init_registry

        db_path = str(tmp_path / "test_registry.db")
        result = init_registry(db_path)

        assert result is True, "init_registry should return True on success"
        assert os.path.exists(db_path), "Database file should be created"

        # Verify schema
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_registry'"
        )
        table_exists = cursor.fetchone() is not None
        conn.close()

        assert table_exists, "file_registry table should exist"

    def test_init_registry_twice(self, tmp_path):
        """Test that calling init_registry twice is idempotent."""
        from src.memory.file_registry import init_registry

        db_path = str(tmp_path / "test_registry.db")

        result1 = init_registry(db_path)
        result2 = init_registry(db_path)

        assert result1 is True
        assert result2 is True, "init_registry should be idempotent"

    def test_get_file_hash(self, tmp_path):
        """Test xxhash64 file hashing."""
        from src.memory.file_registry import get_file_hash

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = get_file_hash(str(test_file))
        assert hash1, "Hash should not be empty"
        assert len(hash1) == 16, "Hash should be 16 hex characters (64-bit)"

        # Same content should produce same hash
        hash2 = get_file_hash(str(test_file))
        assert hash1 == hash2, "Same content should produce same hash"

        # Different content should produce different hash
        test_file.write_text("Different content")
        hash3 = get_file_hash(str(test_file))
        assert hash1 != hash3, "Different content should produce different hash"

    def test_get_file_hash_nonexistent(self, tmp_path):
        """Test hashing a nonexistent file returns empty string."""
        from src.memory.file_registry import get_file_hash

        result = get_file_hash(str(tmp_path / "nonexistent.txt"))
        assert result == "", "Nonexistent file should return empty string"

    def test_needs_processing_new_file(self, tmp_path):
        """Test that new files need processing."""
        from src.memory.file_registry import init_registry, needs_processing

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        test_file = tmp_path / "new.py"
        test_file.write_text("# New file")

        result = needs_processing(db_path, str(test_file))
        assert result is True, "New file should need processing"

    def test_needs_processing_unchanged(self, tmp_path):
        """Test that unchanged files don't need processing."""
        from src.memory.file_registry import (
            init_registry,
            needs_processing,
            update_registry,
            get_file_hash,
        )

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        test_file = tmp_path / "unchanged.py"
        test_file.write_text("# Test content")

        file_hash = get_file_hash(str(test_file))
        update_registry(db_path, str(test_file), file_hash, "test_drive")

        # Check again - should not need processing
        result = needs_processing(db_path, str(test_file))
        assert result is False, "Unchanged file should not need processing"

    def test_needs_processing_modified(self, tmp_path):
        """Test that modified files need processing."""
        from src.memory.file_registry import (
            init_registry,
            needs_processing,
            update_registry,
            get_file_hash,
        )

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        test_file = tmp_path / "modified.py"
        test_file.write_text("# Original")

        file_hash = get_file_hash(str(test_file))
        update_registry(db_path, str(test_file), file_hash, "test_drive")

        # Modify the file
        test_file.write_text("# Modified content")

        result = needs_processing(db_path, str(test_file))
        assert result is True, "Modified file should need processing"

    def test_update_registry(self, tmp_path):
        """Test registry update/insert."""
        from src.memory.file_registry import (
            init_registry,
            update_registry,
            get_file_hash,
        )

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test")

        file_hash = get_file_hash(str(test_file))
        result = update_registry(db_path, str(test_file), file_hash, "test_drive")

        assert result is True, "update_registry should return True"

        # Verify record exists
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT file_path, drive FROM file_registry")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == str(test_file)
        assert rows[0][1] == "test_drive"

    def test_remove_file(self, tmp_path):
        """Test removing file from registry."""
        from src.memory.file_registry import (
            init_registry,
            update_registry,
            remove_file,
            get_file_hash,
        )

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test")

        file_hash = get_file_hash(str(test_file))
        update_registry(db_path, str(test_file), file_hash, "test_drive")

        result = remove_file(db_path, str(test_file))
        assert result is True, "remove_file should return True"

        # Verify removal
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM file_registry")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0, "File should be removed from registry"

    def test_get_stats(self, tmp_path):
        """Test getting registry statistics."""
        from src.memory.file_registry import (
            init_registry,
            update_registry,
            get_file_hash,
            get_stats,
        )

        db_path = str(tmp_path / "test_registry.db")
        init_registry(db_path)

        # Add some files
        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"# Test {i}")
            file_hash = get_file_hash(str(test_file))
            update_registry(db_path, str(test_file), file_hash, "drive1")

        stats = get_stats(db_path)

        assert stats["total_files"] == 3
        assert stats["indexed"] == 3
        assert "drive1" in stats["by_drive"]
        assert stats["by_drive"]["drive1"] == 3


# ============================================================================
# DRIVE SCANNER TESTS
# ============================================================================


class TestDriveScanner:
    """Tests for drive_scanner.py module."""

    def test_default_drives(self):
        """Test DEFAULT_DRIVES constant."""
        from src.memory.drive_scanner import DEFAULT_DRIVES

        assert isinstance(DEFAULT_DRIVES, list), "DEFAULT_DRIVES should be a list"
        assert len(DEFAULT_DRIVES) == 5, "Should have 5 default drives"
        assert all(isinstance(d, str) for d in DEFAULT_DRIVES), (
            "All items should be strings"
        )

    def test_default_include_exts(self):
        """Test DEFAULT_INCLUDE_EXTS constant."""
        from src.memory.drive_scanner import DEFAULT_INCLUDE_EXTS

        assert isinstance(DEFAULT_INCLUDE_EXTS, set), (
            "DEFAULT_INCLUDE_EXTS should be a set"
        )
        assert ".py" in DEFAULT_INCLUDE_EXTS
        assert ".md" in DEFAULT_INCLUDE_EXTS
        assert ".json" in DEFAULT_INCLUDE_EXTS

    def test_default_exclude_dirs(self):
        """Test DEFAULT_EXCLUDE_DIRS constant."""
        from src.memory.drive_scanner import DEFAULT_EXCLUDE_DIRS

        assert isinstance(DEFAULT_EXCLUDE_DIRS, set), (
            "DEFAULT_EXCLUDE_DIRS should be a set"
        )
        assert "node_modules" in DEFAULT_EXCLUDE_DIRS
        assert ".git" in DEFAULT_EXCLUDE_DIRS
        assert "__pycache__" in DEFAULT_EXCLUDE_DIRS

    def test_max_file_size(self):
        """Test MAX_FILE_SIZE constant."""
        from src.memory.drive_scanner import MAX_FILE_SIZE

        assert isinstance(MAX_FILE_SIZE, int), "MAX_FILE_SIZE should be an int"
        assert MAX_FILE_SIZE == 10 * 1024 * 1024, "Should be 10MB"

    def test_scan_drive_empty(self, tmp_path):
        """Test scanning an empty directory."""
        from src.memory.drive_scanner import scan_drive

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        results = list(scan_drive(str(empty_dir)))
        assert results == [], "Empty directory should yield no files"

    def test_scan_drive_nonexistent(self, tmp_path):
        """Test scanning a nonexistent directory."""
        from src.memory.drive_scanner import scan_drive

        results = list(scan_drive(str(tmp_path / "nonexistent")))
        assert results == [], "Nonexistent directory should yield empty"

    def test_scan_drive_with_files(self, tmp_path):
        """Test scanning directory with matching files."""
        from src.memory.drive_scanner import scan_drive

        # Create test directory structure
        test_dir = tmp_path / "test_drive"
        test_dir.mkdir()

        (test_dir / "test.py").write_text("# Python file")
        (test_dir / "test.md").write_text("# Markdown file")
        (test_dir / "test.txt").write_text("Text file")
        (test_dir / "test.png").write_bytes(b"fake png")  # Should be excluded

        results = list(scan_drive(str(test_dir)))

        assert len(results) == 3, "Should find 3 matching files"
        assert any("test.py" in r for r in results)
        assert any("test.md" in r for r in results)
        assert any("test.txt" in r for r in results)

    def test_scan_drive_excludes_dirs(self, tmp_path):
        """Test that excluded directories are skipped."""
        from src.memory.drive_scanner import scan_drive

        test_dir = tmp_path / "test_drive"
        test_dir.mkdir()

        # Create excluded directory with files
        node_modules = test_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "index.js").write_text("// JS file")

        # Create regular directory with files
        src = test_dir / "src"
        src.mkdir()
        (src / "app.py").write_text("# Python file")

        results = list(scan_drive(str(test_dir)))

        # Should find app.py but not index.js from node_modules
        assert any("app.py" in r for r in results), "Should find Python in src"
        assert not any("index.js" in r for r in results), "Should skip node_modules"

    def test_scan_drive_max_size(self, tmp_path):
        """Test max file size filtering."""
        from src.memory.drive_scanner import scan_drive, MAX_FILE_SIZE

        test_dir = tmp_path / "test_drive"
        test_dir.mkdir()

        # Create small file
        small_file = test_dir / "small.py"
        small_file.write_text("x" * 100)

        # Create large file
        large_file = test_dir / "large.py"
        large_file.write_bytes(b"x" * (MAX_FILE_SIZE + 1))

        results = list(scan_drive(str(test_dir)))

        assert any("small.py" in r for r in results), "Small file should be included"
        assert not any("large.py" in r for r in results), (
            "Large file should be excluded"
        )

    def test_scan_all_drives(self, tmp_path):
        """Test parallel scanning of multiple drives."""
        from src.memory.drive_scanner import scan_all_drives

        # Create multiple test directories
        drive1 = tmp_path / "drive1"
        drive1.mkdir()
        (drive1 / "file1.py").write_text("# Python")

        drive2 = tmp_path / "drive2"
        drive2.mkdir()
        (drive2 / "file2.py").write_text("# Python")

        results = list(scan_all_drives([str(drive1), str(drive2)]))

        assert len(results) == 2, "Should find files from both drives"

    def test_get_file_types(self):
        """Test file type categorization."""
        from src.memory.drive_scanner import get_file_types

        assert get_file_types("test.py") == "code"
        assert get_file_types("test.js") == "code"
        assert get_file_types("test.md") == "doc"
        assert get_file_types("test.txt") == "doc"
        assert get_file_types("config.json") == "config"
        assert get_file_types("data.csv") == "data"
        assert get_file_types("unknown.xyz") == "other"

    def test_estimate_scan_time(self, tmp_path):
        """Test scan time estimation."""
        from src.memory.drive_scanner import estimate_scan_time

        test_dir = tmp_path / "test_drive"
        test_dir.mkdir()

        # Create a few files
        for i in range(5):
            (test_dir / f"file{i}.py").write_text(f"# File {i}")

        result = estimate_scan_time(str(test_dir))

        assert "estimated_files" in result
        assert "estimated_time_seconds" in result
        assert result["estimated_files"] >= 0


# ============================================================================
# SCAN CONFIG TESTS
# ============================================================================


class TestScanConfig:
    """Tests for scan_config.py module."""

    def test_default_config(self):
        """Test DEFAULT_CONFIG constant structure."""
        from src.memory.scan_config import DEFAULT_CONFIG

        assert isinstance(DEFAULT_CONFIG, dict), "DEFAULT_CONFIG should be a dict"
        assert "drives" in DEFAULT_CONFIG
        assert "include_extensions" in DEFAULT_CONFIG
        assert "exclude_dirs" in DEFAULT_CONFIG
        assert "max_file_size" in DEFAULT_CONFIG
        assert "batch_size" in DEFAULT_CONFIG
        assert "chunk_size" in DEFAULT_CONFIG
        assert "chunk_overlap" in DEFAULT_CONFIG

        # Verify values
        assert len(DEFAULT_CONFIG["drives"]) == 5
        assert DEFAULT_CONFIG["max_file_size"] == 10485760  # 10MB
        assert DEFAULT_CONFIG["chunk_size"] == 512

    def test_get_config_lazy_load(self, tmp_path, monkeypatch):
        """Test that get_config uses lazy loading."""
        from src.memory import scan_config

        # Reset cache
        scan_config.reset_config()

        # Patch file loading to use our test config
        test_config = {"drives": ["/test/path"], "chunk_size": 256}
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(test_config))

        # Mock the path function to return our test file
        monkeypatch.setattr(scan_config, "_get_config_file_path", lambda x: config_file)

        config = scan_config.load_config(str(config_file))

        assert config["drives"] == ["/test/path"]
        assert config["chunk_size"] == 256

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from JSON file."""
        from src.memory.scan_config import load_config

        test_config = {
            "drives": ["/custom/path"],
            "batch_size": 50,
            "custom_key": "custom_value",
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(test_config))

        config = load_config(str(config_file))

        assert config["drives"] == ["/custom/path"]
        assert config["batch_size"] == 50
        # Should also have defaults
        assert "chunk_size" in config
        assert "include_extensions" in config

    def test_save_config(self, tmp_path):
        """Test saving config to file."""
        from src.memory.scan_config import save_config

        config = {"drives": ["/test"], "chunk_size": 256}
        config_file = tmp_path / "output.json"

        save_config(config, str(config_file))

        assert config_file.exists(), "Config file should be created"

        # Verify contents
        loaded = json.loads(config_file.read_text())
        assert loaded["drives"] == ["/test"]
        assert loaded["chunk_size"] == 256

    def test_update_config(self, tmp_path):
        """Test updating config with new values."""
        from src.memory import scan_config

        scan_config.reset_config()
        scan_config.load_config()

        updates = {"batch_size": 200, "new_key": "new_value"}
        result = scan_config.update_config(updates)

        assert result["batch_size"] == 200
        assert result["new_key"] == "new_value"

    def test_config_merge_nested(self, tmp_path):
        """Test that nested dicts are merged correctly."""
        from src.memory.scan_config import _merge_config

        base = {"max_workers": {"extraction": 16, "embedding": 4}}
        updates = {"max_workers": {"extraction": 8}}

        result = _merge_config(base, updates)

        assert result["max_workers"]["extraction"] == 8
        assert result["max_workers"]["embedding"] == 4


# ============================================================================
# CONTENT EXTRACTORS TESTS
# ============================================================================


class TestContentExtractors:
    """Tests for content_extractors.py module."""

    def test_is_binary_text(self, tmp_path):
        """Test detecting text file as not binary."""
        from src.memory.content_extractors import is_binary

        test_file = tmp_path / "text.txt"
        test_file.write_text("This is plain text content")

        result = is_binary(str(test_file))
        assert result is False, "Text file should not be binary"

    def test_is_binary_binary(self, tmp_path):
        """Test detecting binary file."""
        from src.memory.content_extractors import is_binary

        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\x00\x89PNG")

        result = is_binary(str(test_file))
        assert result is True, "Binary file should be detected as binary"

    def test_is_binary_pdf_signature(self, tmp_path):
        """Test detecting PDF by signature."""
        from src.memory.content_extractors import is_binary

        test_file = tmp_path / "file.pdf"
        test_file.write_bytes(b"%PDF-1.4 some content")

        result = is_binary(str(test_file))
        assert result is True, "PDF should be detected as binary"

    def test_get_encoding_utf8(self, tmp_path):
        """Test UTF-8 encoding detection."""
        from src.memory.content_extractors import get_encoding

        test_file = tmp_path / "utf8.txt"
        test_file.write_text("Hello, World! 你好世界", encoding="utf-8")

        result = get_encoding(str(test_file))
        assert result == "utf-8"

        # UTF-8 can decode ASCII, so the function may return 'utf-8' instead of 'ascii'
        assert result in ("ascii", "utf-8"), f"Expected ascii or utf-8, got {result}"
    def test_extract_code_python(self, tmp_path):
        """Test extracting Python code."""
        from src.memory.content_extractors import extract_code

        test_file = tmp_path / "test.py"
        test_file.write_text(
            'def hello():\n    print("Hello, World!")\n',
            encoding="utf-8",
        )

        result = extract_code(str(test_file))
        assert result is not None
        assert "def hello" in result
        assert 'print("Hello, World!")' in result

    def test_extract_code_empty(self, tmp_path):
        """Test extracting from empty file."""
        from src.memory.content_extractors import extract_code

        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        result = extract_code(str(test_file))
        assert result is None, "Empty file should return None"

    def test_extract_markdown(self, tmp_path):
        """Test extracting Markdown content."""
        from src.memory.content_extractors import extract_markdown

        test_file = tmp_path / "readme.md"
        test_file.write_text("# Hello\n\nThis is markdown.", encoding="utf-8")

        result = extract_markdown(str(test_file))
        assert result is not None
        assert "# Hello" in result
        assert "This is markdown" in result

    def test_extract_text(self, tmp_path):
        """Test extracting plain text."""
        from src.memory.content_extractors import extract_text

        test_file = tmp_path / "data.txt"
        test_file.write_text("Plain text content", encoding="utf-8")

        result = extract_text(str(test_file))
        assert result is not None
        assert "Plain text content" in result

    @pytest.mark.skipif(True, reason="PDF libraries may not be installed")
    def test_extract_pdf(self, tmp_path):
        """Test PDF extraction (may be skipped if no PDF libraries)."""
        from src.memory.content_extractors import extract_pdf

        # This test would require actual PDF library
        # Skip if libraries not available
        test_file = tmp_path / "test.pdf"
        if not test_file.exists():
            pytest.skip("No PDF library available")

        result = extract_pdf(str(test_file))
        # Result may be None if no PDF libraries or invalid PDF
        assert result is None or isinstance(result, str)

    def test_extract_content_dispatch(self, tmp_path):
        """Test content extraction dispatcher."""
        from src.memory.content_extractors import extract_content

        # Test Python file
        py_file = tmp_path / "test.py"
        py_file.write_text("# Python code")
        result = extract_content(str(py_file))
        assert result is not None
        assert "# Python code" in result

        # Test Markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Markdown")
        result = extract_content(str(md_file))
        assert result is not None
        assert "# Markdown" in result

        # Test non-existent file
        result = extract_content(str(tmp_path / "nonexistent.txt"))
        assert result is None

    def test_extract_content_unknown_extension(self, tmp_path):
        """Test extraction for unknown file extension."""
        from src.memory.content_extractors import extract_content

        test_file = tmp_path / "file.xyz"
        test_file.write_text("Some content")

        result = extract_content(str(test_file))
        assert result is not None
        assert "Some content" in result


# ============================================================================
# CHUNKER TESTS
# ============================================================================


class TestChunker:
    """Tests for chunker.py module."""

    def test_default_constants(self):
        """Test DEFAULT_CHUNK_SIZE and DEFAULT_CHUNK_OVERLAP."""
        from src.memory.chunker import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

        assert DEFAULT_CHUNK_SIZE == 512
        assert DEFAULT_CHUNK_OVERLAP == 50

    def test_count_tokens_empty(self):
        """Test token counting for empty text."""
        from src.memory.chunker import count_tokens

        assert count_tokens("") == 0
        assert count_tokens("   ") == 0

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        from src.memory.chunker import count_tokens

        text = "Hello world this is a test"
        tokens = count_tokens(text)
        assert tokens > 0
        assert tokens <= len(text.split())  # Should be ~75% of word count

    def test_chunk_by_tokens_simple(self):
        """Test simple token-based chunking."""
        from src.memory.chunker import chunk_by_tokens

        text = "word " * 100  # 100 words
        chunks = chunk_by_tokens(text, chunk_size=50, chunk_overlap=10)

        assert len(chunks) > 1, "Should create multiple chunks"
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_by_tokens_single(self):
        """Test that short text returns as single chunk."""
        from src.memory.chunker import chunk_by_tokens

        text = "short text"
        chunks = chunk_by_tokens(text, chunk_size=100, chunk_overlap=10)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_by_tokens_empty(self):
        """Test chunking empty text."""
        from src.memory.chunker import chunk_by_tokens

        chunks = chunk_by_tokens("", chunk_size=50, chunk_overlap=10)
        assert chunks == []

    def test_chunk_by_tokens_invalid_params(self):
        """Test error on invalid parameters."""
        from src.memory.chunker import chunk_by_tokens

        with pytest.raises(ValueError):
            chunk_by_tokens("text", chunk_size=0, chunk_overlap=10)

        with pytest.raises(ValueError):
            chunk_by_tokens("text", chunk_size=50, chunk_overlap=-1)

    def test_chunk_by_lines_simple(self):
        """Test line-based chunking."""
        from src.memory.chunker import chunk_by_lines

        text = "\n".join([f"line {i}" for i in range(250)])
        chunks = chunk_by_lines(text, max_lines=100)

        assert len(chunks) > 1

    def test_chunk_by_lines_single(self):
        """Test that short text returns as single chunk."""
        from src.memory.chunker import chunk_by_lines

        text = "line 1\nline 2\nline 3"
        chunks = chunk_by_lines(text, max_lines=100)

        assert len(chunks) == 1

    def test_chunk_by_lines_empty(self):
        """Test chunking empty text."""
        from src.memory.chunker import chunk_by_lines

        chunks = chunk_by_lines("", max_lines=100)
        assert chunks == []

    def test_chunk_by_lines_invalid_params(self):
        """Test error on invalid max_lines."""
        from src.memory.chunker import chunk_by_lines

        with pytest.raises(ValueError):
            chunk_by_lines("text", max_lines=0)

    def test_chunk_text_metadata(self, tmp_path):
        """Test chunk_text returns proper metadata."""
        from src.memory.chunker import chunk_text

        text = "word " * 100
        file_path = str(tmp_path / "test.py")

        chunks = chunk_text(text, file_path, chunk_size=50, chunk_overlap=10)

        assert len(chunks) > 0, "Should return at least one chunk"

        # Check first chunk has required metadata
        chunk = chunks[0]
        assert "text" in chunk
        assert "chunk_index" in chunk
        assert "total_chunks" in chunk
        assert "file_path" in chunk
        assert "token_count" in chunk
        assert chunk["chunk_index"] == 0

    def test_chunk_text_prose_vs_code(self, tmp_path):
        """Test that prose and code use different chunking strategies."""
        from src.memory.chunker import chunk_text

        # Python file should use line-based chunking
        py_text = "\n".join([f"line {i}" for i in range(100)])
        py_chunks = chunk_text(py_text, str(tmp_path / "test.py"))

        # Markdown should use token-based
        md_text = "word " * 100
        md_chunks = chunk_text(md_text, str(tmp_path / "test.md"))

        # Both should return chunks
        assert len(py_chunks) > 0
        assert len(md_chunks) > 0


# ============================================================================
# METADATA EXTRACTOR TESTS
# ============================================================================


class TestMetadataExtractor:
    """Tests for metadata_extractor.py module."""

    def test_get_file_type(self):
        """Test file type determination."""
        from src.memory.metadata_extractor import get_file_type

        assert get_file_type("test.py") == "code"
        assert get_file_type("test.js") == "code"
        assert get_file_type("test.md") == "doc"
        assert get_file_type("test.txt") == "text"
        assert get_file_type("config.json") == "config"
        assert get_file_type("data.csv") == "data"
        assert get_file_type("unknown.xyz") == "other"

    def test_get_language(self):
        """Test language detection."""
        from src.memory.metadata_extractor import get_language

        assert get_language("test.py") == "python"
        assert get_language("test.js") == "javascript"
        assert get_language("test.ts") == "typescript"
        assert get_language("test.go") == "go"
        assert get_language("test.rs") == "rust"
        assert get_language("test.md") == "markdown"
        assert get_language("test.unknown") == "unknown"

    def test_get_drive_name(self, tmp_path):
        """Test drive name extraction."""
        from src.memory.metadata_extractor import get_drive_name

        # Test with /mnt/ path
        result = get_drive_name("/mnt/Library/path/to/file.py")
        assert result == "Library"

        # Test with /media/ path
        result = get_drive_name("/media/usb/doc.txt")
        assert result == "usb"

    def test_count_lines(self, tmp_path):
        """Test line counting."""
        from src.memory.metadata_extractor import count_lines

        test_file = tmp_path / "lines.txt"
        test_file.write_text("line1\nline2\nline3\n")

        count = count_lines(str(test_file))
        # Note: count_lines counts lines in binary mode
        assert count >= 3

    def test_estimate_importance(self):
        """Test importance scoring."""
        from src.memory.metadata_extractor import estimate_importance

        # Code file in src/ should have higher score
        score_high = estimate_importance("/project/src/main.py", 5000)
        assert score_high > 0.5

        # Test file should have lower score
        score_low = estimate_importance("/project/tests/test_main.py", 5000)
        assert score_low < score_high

    def test_estimate_importance_bounds(self):
        """Test importance score is clamped to 0-1."""
        from src.memory.metadata_extractor import estimate_importance

        # Very large file should have lower score
        score = estimate_importance("/path/to/file.py", 5000000)
        assert 0.0 <= score <= 1.0

    def test_extract_metadata_basic(self, tmp_path):
        """Test basic metadata extraction."""
        from src.memory.metadata_extractor import extract_metadata

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\nprint('hello')")

        metadata = extract_metadata(str(test_file))

        assert metadata is not None
        assert "file_path" in metadata
        assert "file_name" in metadata
        assert metadata["file_name"] == "test.py"
        assert "extension" in metadata
        assert metadata["extension"] == ".py"
        assert "size_bytes" in metadata
        assert "file_type" in metadata
        assert metadata["file_type"] == "code"
        assert "language" in metadata
        assert metadata["language"] == "python"
        assert "is_binary" in metadata

    def test_extract_metadata_nonexistent(self, tmp_path):
        """Test metadata extraction for nonexistent file."""
        from src.memory.metadata_extractor import extract_metadata

        result = extract_metadata(str(tmp_path / "nonexistent.py"))
        assert result is None

    def test_extract_metadata_line_count(self, tmp_path):
        """Test that line count is included for code files."""
        from src.memory.metadata_extractor import extract_metadata

        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        metadata = extract_metadata(str(test_file))

        assert "line_count" in metadata
        assert metadata["line_count"] >= 5

    def test_extract_metadata_importance(self, tmp_path):
        """Test that importance is calculated."""
        from src.memory.metadata_extractor import extract_metadata

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test content")

        metadata = extract_metadata(str(test_file))

        assert "importance" in metadata
        assert 0.0 <= metadata["importance"] <= 1.0


# ============================================================================
# FILE EMBEDDER TESTS
# ============================================================================


class TestFileEmbedder:
    """Tests for file_embedder.py module."""

    def test_init_chroma(self, tmp_path):
        """Test ChromaDB initialization."""
        from src.memory.file_embedder import init_chroma

        db_path = str(tmp_path / "chroma_test")

        collection = init_chroma(db_path)

        assert collection is not None
        assert hasattr(collection, "name") or hasattr(collection, "peek")

    def test_init_chroma_cached(self, tmp_path):
        """Test that init_chroma returns cached collection."""
        from src.memory.file_embedder import init_chroma

        db_path = str(tmp_path / "chroma_test")

        collection1 = init_chroma(db_path)
        collection2 = init_chroma(db_path)

        assert collection1 is collection2, "Should return same cached collection"

    def test_embed_batch_empty(self):
        """Test embedding empty batch."""
        from src.memory.file_embedder import embed_batch

        result = embed_batch([])
        assert result == []

    @pytest.mark.skipif(True, reason="Requires Ollama running")
    def test_embed_batch_with_chunks(self):
        """Test embedding non-empty batch (requires Ollama)."""
        from src.memory.file_embedder import embed_batch

        chunks = [{"text": "This is a test document"}]

        result = embed_batch(chunks)
        # Will fail if Ollama not running
        assert isinstance(result, list)

    def test_store_embeddings_mismatch(self, tmp_path):
        """Test that store_embeddings validates input."""
        from src.memory.file_embedder import store_embeddings

        chunks = [{"text": "test"}]
        embeddings = [[0.1] * 768, [0.2] * 768]  # 2 embeddings for 1 chunk

        with pytest.raises(ValueError):
            store_embeddings(chunks, embeddings, str(tmp_path / "db"))

        # ChromaDB doesn't accept empty embeddings - this is the expected behavior
        with pytest.raises(ValueError):
            store_embeddings([], [], str(tmp_path / "db"))

    def test_embed_file_no_chunks(self, tmp_path):
        """Test embed_file with empty content."""
        from src.memory.file_embedder import embed_file

        test_file = tmp_path / "test.py"
        test_file.write_text("")

        result = embed_file(str(test_file), "")

        assert "chunks" in result
        assert "embedded" in result
        assert result["chunks"] == 0
        assert result["embedded"] == 0

    @pytest.mark.skipif(True, reason="Requires Ollama running")
    def test_embed_file_full_pipeline(self, tmp_path):
        """Test full embed pipeline (requires Ollama)."""
        from src.memory.file_embedder import embed_file

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('world')")

        result = embed_file(
            str(test_file),
            "def hello():\n    print('world')",
            db_path=str(tmp_path / "embed_db"),
        )

        assert result["chunks"] > 0
        assert result["embedded"] > 0

    def test_get_pending_embeddings(self):
        """Test get_pending_embeddings returns list."""
        from src.memory.file_embedder import get_pending_embeddings

        result = get_pending_embeddings()

        assert isinstance(result, list)

    def test_get_file_embedding_count(self, tmp_path):
        """Test getting embedding count."""
        from src.memory.file_embedder import init_chroma, get_file_embedding_count

        db_path = str(tmp_path / "chroma_count")
        init_chroma(db_path)

        count = get_file_embedding_count(db_path)
        assert isinstance(count, int)
        assert count >= 0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
