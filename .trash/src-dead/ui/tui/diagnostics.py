"""
System Diagnostics Module for N-Xyme MIND Dashboard TUI.

Provides system information collection, error tracking, and configuration dumping
capabilities for diagnostic purposes.
"""

import platform
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class SystemInfo:
    """Collects system information for diagnostics."""
    
    @staticmethod
    def get_system_info() -> dict:
        """
        Get comprehensive system information.
        
        Returns:
            dict: System information including OS, Python version, memory, and disk.
        """
        return {
            "platform": SystemInfo.get_platform(),
            "python_version": SystemInfo.get_python_version(),
            "python_executable": sys.executable,
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "memory": SystemInfo.get_memory_info(),
            "disk": SystemInfo.get_disk_info(),
            "timestamp": datetime.now().isoformat(),
        }
    
    @staticmethod
    def get_python_version() -> str:
        """
        Get the Python version string.
        
        Returns:
            str: Python version in format 'major.minor.micro'.
        """
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    @staticmethod
    def get_platform() -> str:
        """
        Get the platform information.
        
        Returns:
            str: Platform string (e.g., 'Linux-5.4.0-x86_64').
        """
        return platform.platform()
    
    @staticmethod
    def get_memory_info() -> dict:
        """
        Get memory information.
        
        Returns:
            dict: Memory usage statistics.
        """
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent,
                "total_mb": round(mem.total / (1024 * 1024), 2),
                "available_mb": round(mem.available / (1024 * 1024), 2),
                "used_mb": round(mem.used / (1024 * 1024), 2),
            }
        except ImportError:
            return {
                "total": None,
                "available": None,
                "used": None,
                "percent": None,
                "error": "psutil not available",
            }
    
    @staticmethod
    def get_disk_info() -> dict:
        """
        Get disk information.
        
        Returns:
            dict: Disk usage statistics.
        """
        try:
            import psutil
            disk = psutil.disk_usage("/")
            return {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
            }
        except ImportError:
            return {
                "total": None,
                "used": None,
                "free": None,
                "percent": None,
                "error": "psutil not available",
            }


class ErrorCollector:
    """Collects and summarizes errors for diagnostic purposes."""
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the ErrorCollector.
        
        Args:
            log_dir: Optional path to log directory. Defaults to project log dir.
        """
        self.log_dir = log_dir or self._get_default_log_dir()
        self._errors: list[dict] = []
    
    @staticmethod
    def _get_default_log_dir() -> str:
        """Get the default log directory."""
        project_root = Path(__file__).parent.parent.parent.parent
        return str(project_root / "logs")
    
    def collect_recent_errors(self, count: int = 10) -> list[dict]:
        """
        Collect recent errors from log files.
        
        Args:
            count: Maximum number of errors to collect.
            
        Returns:
            list[dict]: List of error records with timestamp, type, and message.
        """
        errors = []
        
        if not os.path.exists(self.log_dir):
            return errors
        
        try:
            log_files = sorted(
                Path(self.log_dir).glob("*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            
            for log_file in log_files[:3]:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")
                        
                        for line in reversed(lines[-200:]):
                            if any(err_type in line.lower() for err_type in ["error", "exception", "critical", "failed"]):
                                if len(errors) >= count:
                                    break
                                
                                parts = line.split(" - ", 2)
                                if len(parts) >= 3:
                                    errors.append({
                                        "timestamp": parts[0].strip(),
                                        "level": parts[1].strip(),
                                        "message": parts[2].strip(),
                                        "source": log_file.name,
                                    })
                                elif len(parts) == 2:
                                    errors.append({
                                        "timestamp": "",
                                        "level": parts[0].strip(),
                                        "message": parts[1].strip(),
                                        "source": log_file.name,
                                    })
                except (OSError, IOError):
                    continue
                    
        except Exception:
            pass
        
        self._errors = errors[:count]
        return self._errors
    
    def get_error_summary(self) -> dict:
        """
        Get a summary of collected errors.
        
        Returns:
            dict: Summary including count by level and recent errors.
        """
        if not self._errors:
            self.collect_recent_errors()
        
        summary = {
            "total_errors": len(self._errors),
            "by_level": {},
            "recent_errors": self._errors[:5],
            "log_directory": self.log_dir,
            "timestamp": datetime.now().isoformat(),
        }
        
        for error in self._errors:
            level = error.get("level", "unknown")
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1
        
        return summary


class ConfigDumper:
    """Dumps configuration and environment information for diagnostics."""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the ConfigDumper.
        
        Args:
            project_root: Optional path to project root. Defaults to auto-detect.
        """
        self.project_root = project_root or self._get_project_root()
    
    @staticmethod
    def _get_project_root() -> str:
        """Get the project root directory."""
        return str(Path(__file__).parent.parent.parent.parent)
    
    def dump_config(self) -> dict:
        """
        Dump configuration files.
        
        Returns:
            dict: Configuration values from various config files.
        """
        config = {
            "project_root": self.project_root,
            "config_files": {},
            "timestamp": datetime.now().isoformat(),
        }
        
        config_files = [
            "config/settings.json",
            "config/app.json",
            ".env.example",
            "pyproject.toml",
            "package.json",
        ]
        
        for config_file in config_files:
            full_path = Path(self.project_root) / config_file
            if full_path.exists():
                try:
                    if config_file.endswith(".json"):
                        with open(full_path, "r", encoding="utf-8") as f:
                            config["config_files"][config_file] = json.load(f)
                    elif config_file in ["pyproject.toml", "package.json"]:
                        config["config_files"][config_file] = "file exists (content not parsed)"
                    elif config_file == ".env.example":
                        with open(full_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            env_keys = [line.split("=")[0] for line in lines if "=" in line]
                            config["config_files"][config_file] = env_keys
                except (OSError, IOError, json.JSONDecodeError):
                    config["config_files"][config_file] = "error reading file"
        
        return config
    
    def dump_environment(self) -> dict:
        """
        Dump environment variables (non-sensitive).
        
        Returns:
            dict: Environment variables with sensitive values redacted.
        """
        env_vars = {}
        sensitive_keys = [
            "PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY",
            "CREDENTIAL", "AUTH", "KEY", "CERT",
        ]
        
        for key, value in os.environ.items():
            if any(sensitive.lower() in key.lower() for sensitive in sensitive_keys):
                env_vars[key] = "[REDACTED]"
            else:
                env_vars[key] = value
        
        return {
            "environment_variables": env_vars,
            "pythonpath": sys.path,
            "cwd": os.getcwd(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def export_diagnosticsBundle(self, output_path: str) -> bool:
        """
        Export a complete diagnostics bundle.
        
        Args:
            output_path: Path to save the diagnostics bundle.
            
        Returns:
            bool: True if export was successful.
        """
        try:
            system_info = SystemInfo.get_system_info()
            error_collector = ErrorCollector()
            error_summary = error_collector.get_error_summary()
            config = self.dump_config()
            environment = self.dump_environment()
            
            bundle = {
                "system_info": system_info,
                "errors": error_summary,
                "config": config,
                "environment": environment,
                "export_time": datetime.now().isoformat(),
                "version": "1.0.0",
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(bundle, f, indent=2, default=str)
            
            return True
            
        except (OSError, IOError, Exception):
            return False
    
    @staticmethod
    def copy_to_clipboard(data: str) -> bool:
        """
        Copy data to clipboard.
        
        Args:
            data: String data to copy to clipboard.
            
        Returns:
            bool: True if copy was successful.
        """
        try:
            import pyperclip
            pyperclip.copy(data)
            return True
        except ImportError:
            try:
                import subprocess
                process = subprocess.Popen(
                    ["pbcopy"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.communicate(input=data.encode("utf-8"))
                return process.returncode == 0
            except (OSError, IOError, Exception):
                return False
        except Exception:
            return False


def get_full_diagnostics() -> dict:
    """
    Get a complete diagnostics snapshot.
    
    Returns:
        dict: Complete diagnostics bundle.
    """
    system_info = SystemInfo.get_system_info()
    error_collector = ErrorCollector()
    config_dumper = ConfigDumper()
    
    return {
        "system": system_info,
        "errors": error_collector.get_error_summary(),
        "config": config_dumper.dump_config(),
        "environment": config_dumper.dump_environment(),
        "timestamp": datetime.now().isoformat(),
    }