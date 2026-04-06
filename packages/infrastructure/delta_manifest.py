"""Delta Manifest — Content-addressable file tracking for O(1) delta sync."""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """Represents a single file in the manifest."""

    path: str
    hash: str
    size: int
    mtime_ns: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "hash": self.hash,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            path=data["path"],
            hash=data["hash"],
            size=data["size"],
            mtime_ns=data["mtime_ns"],
        )


@dataclass
class DeltaManifest:
    """Content-addressable manifest for efficient file synchronization."""

    version: str = "1.0"
    root: str = ""
    entries: dict[str, FileEntry] = field(default_factory=dict)

    def add_file(self, file_path: Path) -> FileEntry:
        """Compute hash and add file to manifest."""
        content = file_path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        stat = file_path.stat()
        entry = FileEntry(
            path=str(file_path.relative_to(self.root) if self.root else file_path),
            hash=file_hash,
            size=stat.st_size,
            mtime_ns=int(stat.st_mtime_ns),
        )
        self.entries[entry.path] = entry
        return entry

    def add_file_by_content(self, rel_path: str, content: bytes) -> FileEntry:
        """Add file to manifest using provided content."""
        file_hash = hashlib.sha256(content).hexdigest()
        entry = FileEntry(path=rel_path, hash=file_hash, size=len(content), mtime_ns=0)
        self.entries[rel_path] = entry
        return entry

    def get_delta(self, other: Self) -> dict:
        """Compute O(1) delta between manifests."""
        added = []
        modified = []
        deleted = []

        for path, entry in other.entries.items():
            if path not in self.entries:
                added.append(path)
            elif self.entries[path].hash != entry.hash:
                modified.append(path)

        for path in self.entries:
            if path not in other.entries:
                deleted.append(path)

        return {"added": added, "modified": modified, "deleted": deleted}

    def is_changed(self, file_path: Path) -> bool:
        """Check if a specific file has changed since last manifest."""
        rel_path = str(file_path.relative_to(self.root) if self.root else file_path)
        if rel_path not in self.entries:
            return True

        current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        return current_hash != self.entries[rel_path].hash

    def serialize(self) -> str:
        """Serialize manifest to JSON string."""
        data = {
            "version": self.version,
            "root": self.root,
            "entries": {path: entry.to_dict() for path, entry in self.entries.items()},
        }
        return json.dumps(data, indent=2)

    def save(self, path: Path) -> None:
        """Save manifest to file."""
        path.write_text(self.serialize())
        logger.info(f"Manifest saved to {path}")

    @classmethod
    def deserialize(cls, data: str) -> Self:
        """Deserialize manifest from JSON string."""
        obj = json.loads(data)
        entries = {
            path: FileEntry.from_dict(ed) for path, ed in obj.get("entries", {}).items()
        }
        return cls(
            version=obj.get("version", "1.0"), root=obj.get("root", ""), entries=entries
        )

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load manifest from file."""
        return cls.deserialize(path.read_text())

    @classmethod
    def from_directory(cls, root: Path, patterns: list[str] | None = None) -> Self:
        """Build manifest from directory."""
        manifest = cls(root=str(root))
        if patterns is None:
            patterns = ["**/*"]

        for pattern in patterns:
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    try:
                        manifest.add_file(file_path)
                    except Exception as e:
                        logger.warning(f"Skipped {file_path}: {e}")

        logger.info(f"Built manifest with {len(manifest.entries)} entries from {root}")
        return manifest


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_content_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()
