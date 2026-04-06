"""Test delta manifest functionality."""

import tempfile
from pathlib import Path

from src.infrastructure.delta_manifest import DeltaManifest


def test_manifest_creation():
    """Test creating manifest from directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "file1.txt").write_text("hello world")
        (root / "file2.txt").write_text("test content")

        manifest = DeltaManifest.from_directory(root)

        assert len(manifest.entries) == 2
        assert "file1.txt" in manifest.entries
        assert "file2.txt" in manifest.entries
        print("✓ Manifest creation works")


def test_delta_detection():
    """Test O(1) delta detection between manifests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "file1.txt").write_text("original")

        manifest1 = DeltaManifest.from_directory(root)

        (root / "file1.txt").write_text("modified")
        (root / "new_file.txt").write_text("new")

        manifest2 = DeltaManifest.from_directory(root)

        delta = manifest1.get_delta(manifest2)

        assert "new_file.txt" in delta["added"]
        assert "file1.txt" in delta["modified"]
        print("✓ Delta detection works")


def test_file_change_detection():
    """Test individual file change detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        test_file = root / "test.txt"
        test_file.write_text("original content")

        manifest = DeltaManifest.from_directory(root)
        assert not manifest.is_changed(test_file)

        test_file.write_text("modified content")
        assert manifest.is_changed(test_file)
        print("✓ File change detection works")


def test_serialization():
    """Test manifest serialization and deserialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "data.txt").write_text("test")

        manifest1 = DeltaManifest.from_directory(root)
        serialized = manifest1.serialize()

        manifest2 = DeltaManifest.deserialize(serialized)

        assert manifest1.entries == manifest2.entries
        print("✓ Serialization works")


def test_save_load():
    """Test save and load operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "file.txt").write_text("content")

        manifest = DeltaManifest.from_directory(root)
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest.save(manifest_path)

        loaded = DeltaManifest.load(manifest_path)
        assert loaded.entries == manifest.entries
        print("✓ Save/load works")


if __name__ == "__main__":
    test_manifest_creation()
    test_delta_detection()
    test_file_change_detection()
    test_serialization()
    test_save_load()
    print("\nAll tests passed!")
