"""Checkpoint/Resume — State persistence for long-running operations."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """A saved state checkpoint."""

    operation_id: str
    state: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "state": self.state,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Checkpoint:
        return cls(
            operation_id=data["operation_id"],
            state=data["state"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    """Manages checkpoint persistence for long-running operations.

    Uses atomic writes (write to temp file, then rename) to prevent
    data loss on crash.
    """

    def __init__(self, checkpoint_dir: str = "context/memory/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint atomically.

        Args:
            checkpoint: Checkpoint to save.

        Returns:
            Path to saved checkpoint file.
        """
        filepath = self.checkpoint_dir / f"{checkpoint.operation_id}.json"

        # Atomic write: write to temp file, then rename
        data = json.dumps(checkpoint.to_dict(), indent=2)
        fd, tmp_path = tempfile.mkstemp(dir=self.checkpoint_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(data)
            os.rename(tmp_path, filepath)
            logger.info(f"Checkpoint saved: {filepath}")
            return str(filepath)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self, operation_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint.

        Args:
            operation_id: Operation ID to load.

        Returns:
            Checkpoint if found, None otherwise.
        """
        filepath = self.checkpoint_dir / f"{operation_id}.json"
        if not filepath.exists():
            return None

        try:
            with open(filepath) as f:
                data = json.load(f)
            return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load checkpoint {operation_id}: {e}")
            return None

    def delete(self, operation_id: str) -> bool:
        """Delete a checkpoint.

        Args:
            operation_id: Operation ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        filepath = self.checkpoint_dir / f"{operation_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all saved checkpoints.

        Returns:
            List of checkpoints sorted by timestamp (newest first).
        """
        checkpoints = []
        for filepath in self.checkpoint_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                checkpoints.append(Checkpoint.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
        return checkpoints

    def cleanup_old(self, max_age_seconds: float = 86400.0) -> int:
        """Delete checkpoints older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds (default: 24 hours).

        Returns:
            Number of checkpoints deleted.
        """
        deleted = 0
        cutoff = time.time() - max_age_seconds

        for filepath in self.checkpoint_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                if data.get("timestamp", 0) < cutoff:
                    filepath.unlink()
                    deleted += 1
            except (json.JSONDecodeError, KeyError, OSError):
                continue

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted


class CheckpointResume:
    """High-level checkpoint/resume for operations.

    Usage:
        mgr = CheckpointResume("my_operation")
        if mgr.has_checkpoint():
            state = mgr.resume()
            # Continue from checkpoint
        else:
            state = mgr.start(initial_state)

        # During operation
        mgr.save_checkpoint(current_state)

        # On completion
        mgr.complete()
    """

    def __init__(
        self, operation_id: str, checkpoint_dir: str = "context/memory/checkpoints"
    ):
        self.operation_id = operation_id
        self.manager = CheckpointManager(checkpoint_dir)
        self._started = False

    def start(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        """Start a new operation.

        Args:
            initial_state: Initial operation state.

        Returns:
            Initial state.
        """
        self._started = True
        return initial_state

    def has_checkpoint(self) -> bool:
        """Check if a checkpoint exists for this operation."""
        return self.manager.load(self.operation_id) is not None

    def resume(self) -> Optional[dict[str, Any]]:
        """Resume from checkpoint.

        Returns:
            Saved state if checkpoint exists, None otherwise.
        """
        checkpoint = self.manager.load(self.operation_id)
        if checkpoint:
            self._started = True
            return checkpoint.state
        return None

    def save_checkpoint(self, state: dict[str, Any], metadata: Optional[dict] = None):
        """Save current state as checkpoint.

        Args:
            state: Current operation state.
            metadata: Optional metadata.
        """
        if not self._started:
            raise RuntimeError("Operation not started. Call start() or resume() first.")

        checkpoint = Checkpoint(
            operation_id=self.operation_id,
            state=state,
            metadata=metadata or {},
        )
        self.manager.save(checkpoint)

    def complete(self):
        """Mark operation as complete and delete checkpoint."""
        self.manager.delete(self.operation_id)
        self._started = False
        logger.info(f"Operation '{self.operation_id}' completed")
