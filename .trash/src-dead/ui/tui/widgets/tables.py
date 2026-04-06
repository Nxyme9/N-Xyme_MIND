"""
Table widgets for N-Xyme MIND Dashboard TUI.

Provides sortable and filterable table components based on Textual's DataTable.
"""

from typing import Callable, Optional

from textual.widgets import DataTable


class SortableTable(DataTable):
    """
    A DataTable-based widget with sorting and filtering capabilities.

    Inherits from textual.widgets.DataTable and adds:
    - Column management with custom widths
    - Row sorting by any column
    - Row filtering via predicate function
    - Row selection and retrieval

    Example:
        table = SortableTable()
        table.add_column("Name", width=20)
        table.add_column("Age", width=10)
        table.add_row(["Alice", "30"])
        table.add_row(["Bob", "25"])
        table.sort_by("Age", reverse=True)  # Sort by age descending
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the SortableTable widget."""
        super().__init__(*args, **kwargs)
        self._column_widths: dict[str, int] = {}
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False
        self._rows_data: list[list[str]] = []
        self._column_order: list[str] = []
        self._selected_index: int = -1

    def add_column(self, name: str, width: int | None = None) -> None:
        """
        Add a column to the table.

        Args:
            name: The column header name.
            width: Optional width for the column. If None, uses default.
        """
        super().add_column(name, width=width)
        self._column_widths[name] = width if width else 0
        if name not in self._column_order:
            self._column_order.append(name)

    def add_row(self, values: list[str]) -> None:
        """
        Add a row of data to the table.

        Args:
            values: List of string values for each column.

        Note:
            Ensure values correspond to the columns in order.
        """
        self._rows_data.append(values.copy())
        super().add_row(*values)

    def sort_by(self, column_name: str, reverse: bool = False) -> None:
        """
        Sort table rows by the specified column.

        Args:
            column_name: Name of the column to sort by.
            reverse: If True, sort in descending order. Defaults to False.

        Raises:
            KeyError: If column_name is not found in columns.
        """
        if column_name not in self._column_order:
            raise KeyError(f"Column '{column_name}' not found.")

        self._sort_column = column_name
        self._sort_reverse = reverse

        col_index = self._column_order.index(column_name)

        def get_sort_key(row: list[str]) -> str:
            if col_index < len(row):
                return row[col_index]
            return ""

        sorted_data = sorted(self._rows_data, key=get_sort_key, reverse=reverse)

        self.clear()
        self._rows_data = []
        for row in sorted_data:
            self._rows_data.append(row)
            super().add_row(*row)

    def filter(self, predicate: Callable[[list[str]], bool]) -> None:
        """
        Filter table rows using a predicate function.

        Args:
            predicate: A function that takes a row (list of strings) and
                       returns True to keep the row, False to remove it.

        Note:
            This modifies the table in-place, keeping only matching rows.
        """
        filtered_data = [row for row in self._rows_data if predicate(row)]

        self.clear()
        self._rows_data = []
        for row in filtered_data:
            self._rows_data.append(row)
            super().add_row(*row)

    def select_row(self, index: int) -> None:
        """
        Select a row by its index.

        Args:
            index: The row index to select (0-based).

        Note:
            Row must exist in the table. Use carefully with filtered data.
        """
        if 0 <= index < self.row_count:
            self._selected_index = index
            self.move_cursor(row=index)

    def get_selected_row(self) -> list[str] | None:
        """
        Get the currently selected row's data.

        Returns:
            List of string values for the selected row, or None if no row selected.
        """
        if self._selected_index >= 0 and self._selected_index < len(self._rows_data):
            return self._rows_data[self._selected_index]
        return None

    @property
    def row_count(self) -> int:
        """Return the number of rows in the table."""
        return len(self._rows_data)

    def clear(self) -> None:
        """Clear all rows from the table."""
        super().clear()
        self._rows_data = []
        self._selected_index = -1

    def get_column_widths(self) -> dict[str, int]:
        """
        Get the configured widths for all columns.

        Returns:
            Dictionary mapping column names to their widths.
        """
        return self._column_widths.copy()

    def get_sort_state(self) -> tuple[Optional[str], bool]:
        """
        Get the current sort state.

        Returns:
            Tuple of (column_name, reverse) or (None, False) if not sorted.
        """
        return (self._sort_column, self._sort_reverse)


class MultiSortableTable(SortableTable):
    """
    Extended SortableTable with multi-column sorting support.

    Allows sorting by multiple columns with priority ordering.

    Example:
        table = MultiSortableTable()
        table.add_column("Name")
        table.add_column("Age")
        table.add_column("City")
        table.add_row(["Alice", "30", "NYC"])
        table.add_row(["Bob", "25", "LA"])
        # Sort by Age first, then by Name
        table.multi_sort([("Age", False), ("Name", False)])
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the MultiSortableTable widget."""
        super().__init__(*args, **kwargs)
        self._sort_keys: list[tuple[str, bool]] = []

    def multi_sort(self, sort_specs: list[tuple[str, bool]]) -> None:
        """
        Sort table by multiple columns.

        Args:
            sort_specs: List of (column_name, reverse) tuples.
                       First spec has highest priority.

        Example:
            table.multi_sort([("Age", False), ("Name", True)])
            # Sorts by Age ascending, then Name descending
        """
        if not sort_specs:
            return

        self._sort_keys = sort_specs

        def get_sort_key(row: list[str]) -> tuple[str, ...]:
            keys: list[str] = []
            for col_name, _ in sort_specs:
                if col_name in self._column_order:
                    col_index = self._column_order.index(col_name)
                    if col_index < len(row):
                        keys.append(row[col_index])
                    else:
                        keys.append("")
                else:
                    keys.append("")
            return tuple(keys)

        sorted_data = sorted(self._rows_data, key=get_sort_key)

        self.clear()
        self._rows_data = []
        for row_data in sorted_data:
            self._rows_data.append(row_data)
            super().add_row(*row_data)

    def get_sort_state(self) -> list[tuple[str, bool]]:
        """
        Get the current multi-column sort state.

        Returns:
            List of (column_name, reverse) tuples.
        """
        return self._sort_keys.copy()
