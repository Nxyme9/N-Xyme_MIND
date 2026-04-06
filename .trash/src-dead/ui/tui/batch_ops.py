"""
Batch Operations Module for N-Xyme MIND Dashboard TUI.

Provides batch operations management for agents including start, stop, and delete
operations with operation tracking and selection management.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class BatchOperation:
    """Represents a batch operation on multiple agents.

    Attributes:
        operation_id: Unique identifier for this operation.
        operation_type: Type of operation ("start", "stop", "delete").
        target_ids: List of agent IDs targeted by this operation.
        status: Current status of the operation.
        results: Dictionary mapping agent IDs to success status.
    """

    operation_id: str
    operation_type: str
    target_ids: list[str]
    status: str = "pending"
    results: dict[str, bool] = field(default_factory=dict[str, bool])

    def __post_init__(self) -> None:
        """Validate operation after initialization."""
        if self.operation_type not in ("start", "stop", "delete"):
            raise ValueError(f"Invalid operation_type: {self.operation_type}")
        if self.status not in ("pending", "running", "completed", "failed"):
            raise ValueError(f"Invalid status: {self.status}")


class BatchManager:
    """Manages batch operations on agents.

    Provides methods to create, track, and manage batch operations across
    multiple agents. Supports start, stop, and delete operations with
    operation tracking and status management.

    Attributes:
        _operations: Dictionary mapping operation IDs to BatchOperation instances.
    """

    def __init__(self) -> None:
        """Initialize the BatchManager."""
        self._operations: dict[str, BatchOperation] = {}

    def start_batch(self, target_ids: list[str]) -> str:
        """Create a batch start operation for the specified agents.

        Args:
            target_ids: List of agent IDs to start.

        Returns:
            The operation_id for the created batch operation.
        """
        operation_id = str(uuid.uuid4())
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type="start",
            target_ids=target_ids,
            status="pending",
            results={}
        )
        self._operations[operation_id] = operation
        return operation_id

    def stop_batch(self, target_ids: list[str]) -> str:
        """Create a batch stop operation for the specified agents.

        Args:
            target_ids: List of agent IDs to stop.

        Returns:
            The operation_id for the created batch operation.
        """
        operation_id = str(uuid.uuid4())
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type="stop",
            target_ids=target_ids,
            status="pending",
            results={}
        )
        self._operations[operation_id] = operation
        return operation_id

    def delete_batch(self, target_ids: list[str]) -> str:
        """Create a batch delete operation for the specified agents.

        Args:
            target_ids: List of agent IDs to delete.

        Returns:
            The operation_id for the created batch operation.
        """
        operation_id = str(uuid.uuid4())
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type="delete",
            target_ids=target_ids,
            status="pending",
            results={}
        )
        self._operations[operation_id] = operation
        return operation_id

    def get_operation(self, operation_id: str) -> Optional[BatchOperation]:
        """Retrieve a batch operation by its ID.

        Args:
            operation_id: The ID of the operation to retrieve.

        Returns:
            The BatchOperation if found, None otherwise.
        """
        return self._operations.get(operation_id)

    def get_active_operations(self) -> list[BatchOperation]:
        """Get all operations that are currently pending or running.

        Returns:
            List of active BatchOperation instances.
        """
        return [
            op for op in self._operations.values()
            if op.status in ("pending", "running")
        ]

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a pending operation.

        Only pending operations can be cancelled. Running or completed
        operations cannot be cancelled.

        Args:
            operation_id: The ID of the operation to cancel.

        Returns:
            True if the operation was cancelled, False if not found
            or already running/completed.
        """
        operation = self._operations.get(operation_id)
        if operation is None:
            return False
        if operation.status != "pending":
            return False
        operation.status = "failed"
        return True


class BatchSelection:
    """Manages selection of items for batch operations.

    Provides methods to select, deselect, toggle, and retrieve selected
    items. Useful for building UI selection interfaces for batch operations.

    Attributes:
        _selected: Set of selected item IDs.
    """

    def __init__(self) -> None:
        """Initialize the BatchSelection."""
        self._selected: set[str] = set()

    def select(self, item_id: str) -> None:
        """Select a specific item.

        Args:
            item_id: The ID of the item to select.
        """
        self._selected.add(item_id)

    def deselect(self, item_id: str) -> None:
        """Deselect a specific item.

        Args:
            item_id: The ID of the item to deselect.
        """
        self._selected.discard(item_id)

    def toggle(self, item_id: str) -> None:
        """Toggle selection state of an item.

        If the item is selected, it will be deselected.
        If the item is not selected, it will be selected.

        Args:
            item_id: The ID of the item to toggle.
        """
        if item_id in self._selected:
            self._selected.discard(item_id)
        else:
            self._selected.add(item_id)

    def select_all(self, items: list[str]) -> None:
        """Select multiple items at once.

        Args:
            items: List of item IDs to select.
        """
        self._selected.update(items)

    def clear_selection(self) -> None:
        """Clear all selected items."""
        self._selected.clear()

    def get_selection(self) -> list[str]:
        """Get the list of selected item IDs.

        Returns:
            List of selected item IDs in insertion order.
        """
        return list(self._selected)

    def get_count(self) -> int:
        """Get the number of selected items.

        Returns:
            Count of selected items.
        """
        return len(self._selected)