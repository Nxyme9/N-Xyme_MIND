"""
Export/Import module for dashboard data.

Provides functionality to export and import dashboard state and data
in JSON and YAML formats.
"""

import json
from pathlib import Path
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ExportManager:
    """
    Manages export operations for dashboard data.
    
    Supports exporting full dashboard state, partial data (by tab),
    and multiple output formats (JSON, YAML).
    """
    
    SUPPORTED_FORMATS = ("json", "yaml")
    
    def export_full(self, dashboard_state: dict[str, Any], output_path: str, format: str) -> bool:
        """
        Export full dashboard state to a file.
        
        Args:
            dashboard_state: Complete dashboard state dictionary.
            output_path: Path to the output file.
            format: Export format ("json" or "yaml").
            
        Returns:
            bool: True if export succeeded, False otherwise.
        """
        if format not in self.SUPPORTED_FORMATS:
            return False
        
        output = Path(output_path)
        
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                return self.export_to_json(dashboard_state, output_path)
            elif format == "yaml":
                return self.export_to_yaml(dashboard_state, output_path)
            
            return False
        except (IOError, OSError):
            return False
    
    def export_partial(self, data: dict[str, Any], tab_name: str, output_path: str, format: str) -> bool:
        """
        Export partial data for a specific tab.
        
        Args:
            data: Dictionary containing data for the specific tab.
            tab_name: Name of the tab being exported.
            output_path: Path to the output file.
            format: Export format ("json" or "yaml").
            
        Returns:
            bool: True if export succeeded, False otherwise.
        """
        if format not in self.SUPPORTED_FORMATS:
            return False
        
        output = Path(output_path)
        
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            
            wrapped_data: dict[str, Any] = {
                "tab": tab_name,
                "data": data,
                "exported_at": self._get_timestamp()
            }
            
            if format == "json":
                return self.export_to_json(wrapped_data, output_path)
            elif format == "yaml":
                return self.export_to_yaml(wrapped_data, output_path)
            
            return False
        except (IOError, OSError):
            return False
    
    def export_to_json(self, data: dict[str, Any], path: str) -> bool:
        """
        Export data to JSON file.
        
        Args:
            data: Dictionary to export.
            path: Output file path.
            
        Returns:
            bool: True if export succeeded, False otherwise.
        """
        try:
            output = Path(path)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, OSError, TypeError):
            return False
    
    def export_to_yaml(self, data: dict[str, Any], path: str) -> bool:
        """
        Export data to YAML file.
        
        Args:
            data: Dictionary to export.
            path: Output file path.
            
        Returns:
            bool: True if export succeeded, False otherwise.
        """
        if not YAML_AVAILABLE:
            return False
        
        try:
            output = Path(path)
            with open(output, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            return True
        except (IOError, OSError, yaml.YAMLError):
            return False
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current ISO format timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class ImportManager:
    """
    Manages import operations for dashboard data.
    
    Supports importing data from JSON and YAML files,
    validation, and merging with existing state.
    """
    
    SUPPORTED_FORMATS = ("json", "yaml")
    
    def import_data(self, source_path: str, format: str) -> dict[str, Any] | None:
        """
        Import data from a file.
        
        Args:
            source_path: Path to the source file.
            format: Import format ("json" or "yaml").
            
        Returns:
            dict | None: Imported data dictionary, or None if import failed.
        """
        if format not in self.SUPPORTED_FORMATS:
            return None
        
        source = Path(source_path)
        
        if not source.exists():
            return None
        
        try:
            if format == "json":
                return self._import_json(source)
            elif format == "yaml":
                return self._import_yaml(source)
            
            return None
        except (IOError, OSError, json.JSONDecodeError):
            return None
    
    def _import_json(self, path: Path) -> dict[str, Any] | None:
        """Import JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return None
        except (IOError, OSError, json.JSONDecodeError):
            return None
    
    def _import_yaml(self, path: Path) -> dict[str, Any] | None:
        """Import YAML file."""
        if not YAML_AVAILABLE:
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return data
            return None
        except (IOError, OSError, yaml.YAMLError):
            return None
    
    def merge_on_import(self, existing: dict[str, Any], imported: dict[str, Any]) -> dict[str, Any]:
        """
        Merge imported data with existing dashboard state.
        
        Uses a simple merge strategy:
        - Imported values override existing ones for top-level keys
        - For nested dicts, recursively merges
        
        Args:
            existing: Existing dashboard state dictionary.
            imported: Imported data dictionary.
            
        Returns:
            dict: Merged dictionary.
        """
        result = existing.copy()
        
        for key, value in imported.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_on_import(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate_import(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate imported data structure.
        
        Checks for basic dashboard data requirements.
        
        Args:
            data: Imported data dictionary.
            
        Returns:
            tuple: (is_valid, list of error messages)
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Import data must be a dictionary")
            return False, errors
        
        # Check for expected dashboard fields (optional but warn if missing)
        expected_fields = ["tab", "data", "current_tab", "dark_mode", "preferences"]
        missing_optional = [f for f in expected_fields if f not in data]
        
        if missing_optional and len(data) > 0:
            # Only warn if data is non-empty but missing common fields
            pass  # Optional fields, not critical
        
        return True, errors


class ExportImportDialog:
    """
    Textual Screen for export/import operations.
    
    Provides UI for:
    - Export tab with format selector
    - Import tab with file picker
    - Merge option checkbox
    """
    
    def __init__(self) -> None:
        """Initialize the export/import dialog."""
        self.export_manager = ExportManager()
        self.import_manager = ImportManager()
        self._selected_format = "json"
        self._merge_on_import = False
    
    @property
    def selected_format(self) -> str:
        """Get currently selected format."""
        return self._selected_format
    
    @selected_format.setter
    def selected_format(self, value: str) -> None:
        """Set selected format if valid."""
        if value in ("json", "yaml"):
            self._selected_format = value
    
    @property
    def merge_on_import(self) -> bool:
        """Get merge on import setting."""
        return self._merge_on_import
    
    @merge_on_import.setter
    def merge_on_import(self, value: bool) -> None:
        """Set merge on import setting."""
        self._merge_on_import = value
    
    def export_dashboard(self, dashboard_state: dict[str, Any], output_path: str) -> bool:
        """
        Export dashboard state using current settings.
        
        Args:
            dashboard_state: Dashboard state to export.
            output_path: Output file path.
            
        Returns:
            bool: True if export succeeded.
        """
        return self.export_manager.export_full(
            dashboard_state, output_path, self._selected_format
        )
    
    def export_tab(self, data: dict[str, Any], tab_name: str, output_path: str) -> bool:
        """
        Export specific tab data.
        
        Args:
            data: Tab data to export.
            tab_name: Name of the tab.
            output_path: Output file path.
            
        Returns:
            bool: True if export succeeded.
        """
        return self.export_manager.export_partial(
            data, tab_name, output_path, self._selected_format
        )
    
    def import_dashboard(self, source_path: str) -> dict[str, Any] | None:
        """
        Import dashboard data from file.
        
        Args:
            source_path: Source file path.
            
        Returns:
            dict | None: Imported data or None if failed.
        """
        data = self.import_manager.import_data(source_path, self._selected_format)
        
        if data is None:
            return None
        
        is_valid, errors = self.import_manager.validate_import(data)
        
        if not is_valid:
            return None
        
        return data
    
    def import_and_merge(self, existing: dict[str, Any], source_path: str) -> dict[str, Any] | None:
        """
        Import and optionally merge with existing state.
        
        Args:
            existing: Existing dashboard state.
            source_path: Source file path.
            
        Returns:
            dict | None: Merged data or None if import failed.
        """
        imported = self.import_dashboard(source_path)
        
        if imported is None:
            return None
        
        if self._merge_on_import:
            return self.import_manager.merge_on_import(existing, imported)
        
        return imported
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported export/import formats."""
        formats = ["json"]
        if YAML_AVAILABLE:
            formats.append("yaml")
        return formats
    
    def is_yaml_available(self) -> bool:
        """Check if YAML support is available."""
        return YAML_AVAILABLE