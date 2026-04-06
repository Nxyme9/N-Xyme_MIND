"""Tests for memory drive configuration."""

import pytest
from pathlib import Path
from src.memory.config import (
    DRIVES,
    DriveConfig,
    ConfigSchema,
    list_drives,
    list_mounted_drives,
    health_check_drives,
    get_drive,
    WATCHED_DIRECTORIES,
)


def test_drives_count():
    """Verify all 5 drives are configured."""
    assert len(DRIVES) == 5


def test_drive_names():
    """Verify expected drive names."""
    names = [d.name for d in DRIVES]
    assert "Library" in names
    assert "WIN_LIBRARY" in names
    assert "NXYME_CORE" in names
    assert "NXYME_IMAGES" in names
    assert "backup" in names


def test_drive_paths():
    """Verify drive paths are in /mnt/"""
    for drive in DRIVES:
        assert str(drive.path).startswith("/mnt/")


def test_drive_config_dataclass():
    """Verify DriveConfig dataclass works."""
    drive = DriveConfig(name="test", path=Path("/mnt/test"), enabled=True)
    assert drive.name == "test"
    assert drive.enabled is True


def test_drive_exists_property():
    """Verify exists property checks path."""
    drive = DriveConfig(name="test", path=Path("/nonexistent"))
    assert drive.exists is False


def test_list_drives():
    """Verify list_drives returns all drives."""
    drives = list_drives()
    assert len(drives) == 5


def test_list_mounted_drives():
    """Verify list_mounted_drives returns mounted ones."""
    mounted = list_mounted_drives()
    assert isinstance(mounted, list)
    for drive in mounted:
        assert drive.exists


def test_health_check_drives():
    """Verify health check returns dict."""
    results = health_check_drives()
    assert isinstance(results, dict)
    assert len(results) == 5
    for name, status in results.items():
        assert "path" in status
        assert "exists" in status
        assert "healthy" in status


def test_get_drive():
    """Verify get_drive returns correct drive."""
    drive = get_drive("Library")
    assert drive is not None
    assert drive.name == "Library"

    missing = get_drive("NonExistent")
    assert missing is None


def test_watched_directories():
    """Verify watched directories are set."""
    assert isinstance(WATCHED_DIRECTORIES, list)
    assert len(WATCHED_DIRECTORIES) > 0


def test_config_schema_from_env():
    """Verify ConfigSchema can load from env."""
    schema = ConfigSchema.from_env()
    assert schema.drives == DRIVES
    assert isinstance(schema.watched_dirs, list)
