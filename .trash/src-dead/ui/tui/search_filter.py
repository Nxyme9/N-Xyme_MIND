"""
Search and filter functionality for N-Xyme MIND Dashboard TUI.

This module provides global search and filter capabilities for the dashboard,
supporting case-insensitive search, regex search toggle, and filter state management.
"""

import re
from typing import Callable, Dict, List, Optional


class GlobalSearch:
    """
    Global search functionality for dashboard data.

    Provides search across data sources with support for case-insensitive
    and regex search modes.
    """

    def __init__(self) -> None:
        """Initialize the GlobalSearch with empty results and query."""
        self._results: List[Dict] = []
        self._query: str = ""
        self._regex_enabled: bool = False

    @property
    def results(self) -> List[Dict]:
        """Return the current search results."""
        return self._results

    @property
    def query(self) -> str:
        """Return the current search query."""
        return self._query

    def search(self, query: str, data_source: Callable[[], List[Dict]]) -> List[Dict]:
        """
        Search for query in data source.

        Args:
            query: The search query string.
            data_source: A callable that returns list of dicts to search through.

        Returns:
            List of matching dictionaries from the data source.
        """
        self._query = query

        if not query:
            self._results = data_source()
            return self._results

        data = data_source()

        if self._regex_enabled:
            try:
                pattern = re.compile(query, re.IGNORECASE)
                self._results = [
                    item
                    for item in data
                    if any(pattern.search(str(v)) for v in item.values())
                ]
            except re.error:
                # Fallback to case-insensitive if regex is invalid
                query_lower = query.lower()
                self._results = [
                    item
                    for item in data
                    if any(query_lower in str(v).lower() for v in item.values())
                ]
        else:
            query_lower = query.lower()
            self._results = [
                item
                for item in data
                if any(query_lower in str(v).lower() for v in item.values())
            ]

        return self._results

    def highlight_matches(self, text: str, query: str) -> str:
        """
        Highlight matching text portions.

        Args:
            text: The text to search within.
            query: The search query.

        Returns:
            The text with matches highlighted (using ANSI codes).
        """
        if not query:
            return text

        if self._regex_enabled:
            try:
                pattern = re.compile(f"({query})", re.IGNORECASE)
                return pattern.sub(r"\1", text)
            except re.error:
                pass

        # Case-insensitive highlight
        query_lower = query.lower()
        text_lower = text.lower()

        result = ""
        last_end = 0
        start = 0

        while True:
            idx = text_lower.find(query_lower, start)
            if idx == -1:
                result += text[last_end:]
                break

            result += text[last_end:idx]
            result += text[idx : idx + len(query)]
            last_end = idx + len(query)
            start = idx + len(query)

        return result

    def filter_by_tab(self, tab_name: str) -> List[Dict]:
        """
        Filter results by tab/category name.

        Args:
            tab_name: The tab name to filter by.

        Returns:
            List of dictionaries matching the tab.
        """
        return [
            item
            for item in self._results
            if item.get("tab") == tab_name or item.get("category") == tab_name
        ]

    def set_regex_enabled(self, enabled: bool) -> None:
        """
        Enable or disable regex search mode.

        Args:
            enabled: True to enable regex, False for normal text search.
        """
        self._regex_enabled = enabled

    def get_results(self) -> List[Dict]:
        """
        Get the current search results.

        Returns:
            List of dictionaries representing search results.
        """
        return self._results


class FilterState:
    """
    Manages active filters and applies them to data.

    Provides methods to add, remove, and apply filters to data sets.
    """

    def __init__(self) -> None:
        """Initialize the FilterState with empty filters."""
        self.active_filters: Dict[str, str] = {}

    def add_filter(self, key: str, value: str) -> None:
        """
        Add a filter to the active filters.

        Args:
            key: The filter key (e.g., 'status', 'type').
            value: The filter value to match.
        """
        self.active_filters[key] = value

    def remove_filter(self, key: str) -> None:
        """
        Remove a filter from active filters.

        Args:
            key: The filter key to remove.
        """
        if key in self.active_filters:
            del self.active_filters[key]

    def clear_filters(self) -> None:
        """Clear all active filters."""
        self.active_filters.clear()

    def apply_filters(self, data: List[Dict]) -> List[Dict]:
        """
        Apply active filters to the given data.

        Args:
            data: List of dictionaries to filter.

        Returns:
            Filtered list of dictionaries matching all active filters.
        """
        if not self.active_filters:
            return data

        result = data

        for key, value in self.active_filters.items():
            value_lower = value.lower()
            result = [
                item
                for item in result
                if key in item and value_lower in str(item[key]).lower()
            ]

        return result
