#!/usr/bin/env python3
"""
N-Xyme MIND Migration Backup Script (Python)
Creates a timestamped backup of all critical data before migration.
Cross-platform compatible (Windows, Linux, macOS).
"""

import os
import sys
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Configuration
SOURCE_ROOT = Path(r"D:\01_CODING\00_N-Xyme_CATALYST")
BACKUP_ROOT = Path(r"D:\01_CODING\backups\nxyme-catalyst-pre-migration")


# ANSI colors
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.CYAN}{msg}{Colors.RESET}")


class MigrationBackup:
    def __init__(self, source_root: Path, backup_root: Path):
        self.source_root = source_root
        self.backup_root = backup_root
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.backup_root / f"backup_{self.timestamp}"
        self.manifest: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "source": str(source_root),
            "destination": str(self.backup_dir),
            "items": [],
        }

    def backup_directory(self, source_path: Path, description: str, relative_path: str) -> bool:
        """Backup a directory."""
        dest_path = self.backup_dir / relative_path

        if source_path.exists():
            print_info(f"Backing up: {description}")
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                print_success("  Completed")
                self.manifest["items"].append(
                    {
                        "type": "directory",
                        "description": description,
                        "source": str(source_path),
                        "destination": str(dest_path),
                        "status": "success",
                    }
                )
                return True
            except Exception as e:
                print_error(f"  Failed: {e}")
                self.manifest["items"].append(
                    {
                        "type": "directory",
                        "description": description,
                        "source": str(source_path),
                        "destination": str(dest_path),
                        "status": "failed",
                        "error": str(e),
                    }
                )
                return False
        else:
            print_warning(f"  Not found: {source_path}")
            self.manifest["items"].append(
                {
                    "type": "directory",
                    "description": description,
                    "source": str(source_path),
                    "status": "not_found",
                }
            )
            return False

    def backup_file(self, source_path: Path, description: str, relative_path: str) -> bool:
        """Backup a single file."""
        dest_path = self.backup_dir / relative_path

        if source_path.exists():
            print_info(f"Backing up: {description}")
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)
                print_success("  Completed")
                self.manifest["items"].append(
                    {
                        "type": "file",
                        "description": description,
                        "source": str(source_path),
                        "destination": str(dest_path),
                        "status": "success",
                    }
                )
                return True
            except Exception as e:
                print_error(f"  Failed: {e}")
                self.manifest["items"].append(
                    {
                        "type": "file",
                        "description": description,
                        "source": str(source_path),
                        "destination": str(dest_path),
                        "status": "failed",
                        "error": str(e),
                    }
                )
                return False
        else:
            print_warning(f"  Not found: {source_path}")
            self.manifest["items"].append(
                {
                    "type": "file",
                    "description": description,
                    "source": str(source_path),
                    "status": "not_found",
                }
            )
            return False

    def run(self):
        """Execute the backup process."""
        print_info("\n=== N-Xyme CATALYST Pre-Migration Backup ===\n")

        # Create backup directory
        print_info(f"Creating backup directory: {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Core Jarvis System
        print_info("\n--- Core Jarvis System ---")
        self.backup_directory(
            self.source_root / "jarvis" / "engine",
            "Jarvis Engine (Voice, Vision, Brain)",
            "jarvis/engine",
        )
        self.backup_directory(
            self.source_root / "jarvis" / "agent",
            "Jarvis Agent (Loop, Tools, Memory)",
            "jarvis/agent",
        )
        self.backup_directory(
            self.source_root / "jarvis" / "skills",
            "Jarvis Skills (Browser, Desktop)",
            "jarvis/skills",
        )
        self.backup_directory(
            self.source_root / "jarvis" / "adhd", "ADHD Features (Focus, Tracking)", "jarvis/adhd"
        )
        self.backup_directory(
            self.source_root / "jarvis" / "ui", "UI Components (Hub, Palette)", "jarvis/ui"
        )
        self.backup_directory(
            self.source_root / "jarvis" / "api", "API Server (FastAPI, PWA)", "jarvis/api"
        )
        self.backup_file(
            self.source_root / "jarvis" / "main.py", "Jarvis Main Entry Point", "jarvis/main.py"
        )
        self.backup_file(
            self.source_root / "jarvis" / "__init__.py", "Jarvis Package Init", "jarvis/__init__.py"
        )

        # Configuration
        print_info("\n--- Configuration ---")
        self.backup_directory(
            self.source_root / "configs" / "jarvis", "Jarvis Configs", "configs/jarvis"
        )
        self.backup_directory(
            self.source_root / "configs" / "opencode", "OpenCode Configs", "configs/opencode"
        )
        self.backup_directory(
            self.source_root / "configs" / "agents", "Agent Definitions", "configs/agents"
        )
        self.backup_directory(
            self.source_root / "configs" / "graphiti", "Graphiti Configs", "configs/graphiti"
        )
        self.backup_directory(
            self.source_root / "configs" / "ollama", "Ollama Configs", "configs/ollama"
        )
        self.backup_file(
            self.source_root / "configs" / "app_config.py",
            "App Configuration",
            "configs/app_config.py",
        )
        self.backup_file(
            self.source_root / "configs" / "ports.md", "Port Assignments", "configs/ports.md"
        )

        # Scripts
        print_info("\n--- Scripts ---")
        self.backup_file(
            self.source_root / "scripts" / "start-nxyme-mind.py",
            "MIND Startup Script",
            "scripts/start-nxyme-mind.py",
        )
        self.backup_file(
            self.source_root / "scripts" / "start-nxyme-mind.bat",
            "MIND Startup Batch",
            "scripts/start-nxyme-mind.bat",
        )

        # Memory System
        print_info("\n--- Memory System ---")
        self.backup_directory(self.source_root / "memory", "Memory System", "memory")

        # Data (Runtime)
        print_info("\n--- Data (Runtime) ---")
        self.backup_file(
            self.source_root / "data" / "jarvis_events.db",
            "Jarvis Events DB",
            "data/jarvis_events.db",
        )
        self.backup_file(
            self.source_root / "data" / "jarvis_memory.db",
            "Jarvis Memory DB",
            "data/jarvis_memory.db",
        )
        self.backup_file(
            self.source_root / "data" / "jarvis_scheduler.db",
            "Jarvis Scheduler DB",
            "data/jarvis_scheduler.db",
        )
        self.backup_file(self.source_root / "data" / "nxyme.db", "N-Xyme DB", "data/nxyme.db")
        self.backup_file(
            self.source_root / "data" / "audio_config.json",
            "Audio Configuration",
            "data/audio_config.json",
        )
        self.backup_directory(self.source_root / "data" / "neo4j", "Neo4j Data", "data/neo4j")

        # Sisyphus Rules & Plans
        print_info("\n--- Sisyphus Rules & Plans ---")
        self.backup_directory(
            self.source_root / ".sisyphus" / "rules", "Sisyphus Rules", ".sisyphus/rules"
        )
        self.backup_directory(
            self.source_root / ".sisyphus" / "plans", "Sisyphus Plans", ".sisyphus/plans"
        )
        self.backup_file(
            self.source_root / ".sisyphus" / "session-config.json",
            "Session Config",
            ".sisyphus/session-config.json",
        )
        self.backup_file(
            self.source_root / ".sisyphus" / "boulder.json",
            "Boulder Config",
            ".sisyphus/boulder.json",
        )

        # Environment & Config Files
        print_info("\n--- Environment & Config Files ---")
        self.backup_file(self.source_root / ".env.example", "Environment Example", ".env.example")
        self.backup_file(
            self.source_root / "docker-compose.yml", "Docker Compose", "docker-compose.yml"
        )
        self.backup_file(
            self.source_root / "docker-compose.override.yml",
            "Docker Compose Override",
            "docker-compose.override.yml",
        )
        self.backup_file(self.source_root / "package.json", "Package.json", "package.json")
        self.backup_file(
            self.source_root / "pyproject.toml", "Python Project Config", "pyproject.toml"
        )
        self.backup_file(
            self.source_root / "requirements.txt", "Python Requirements", "requirements.txt"
        )

        # Save manifest
        print_info("\n--- Saving Backup Manifest ---")
        manifest_path = self.backup_dir / "backup-manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        print_success(f"Manifest saved: {manifest_path}")

        # Summary
        success_count = sum(1 for item in self.manifest["items"] if item["status"] == "success")
        failed_count = sum(1 for item in self.manifest["items"] if item["status"] == "failed")
        not_found_count = sum(1 for item in self.manifest["items"] if item["status"] == "not_found")

        print_info("\n=== Backup Summary ===")
        print_success(f"Successful: {success_count}")
        if failed_count > 0:
            print_error(f"Failed: {failed_count}")
        if not_found_count > 0:
            print_warning(f"Not Found: {not_found_count}")

        print_info(f"\nBackup location: {self.backup_dir}")
        print_info(f"Total items backed up: {len(self.manifest['items'])}")

        # Create compressed archive
        print_info("\nCreating compressed archive...")
        archive_path = self.backup_root / f"backup_{self.timestamp}.zip"
        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.backup_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.backup_dir)
                        zipf.write(file_path, arcname)

            backup_size = sum(
                f.stat().st_size for f in self.backup_dir.rglob("*") if f.is_file()
            ) / (1024 * 1024)
            archive_size = archive_path.stat().st_size / (1024 * 1024)
            print_success(f"Archive created: {archive_path}")
            print_info(f"Backup size: {backup_size:.2f} MB")
            print_info(f"Archive size: {archive_size:.2f} MB")
        except Exception as e:
            print_warning(f"Could not create archive: {e}")

        print_info("\n=== Backup Complete ===\n")

        return success_count, failed_count, not_found_count


def main():
    """Main entry point."""
    # Check if source exists
    if not SOURCE_ROOT.exists():
        print_error(f"Source directory not found: {SOURCE_ROOT}")
        sys.exit(1)

    # Create backup
    backup = MigrationBackup(SOURCE_ROOT, BACKUP_ROOT)
    success, failed, not_found = backup.run()

    # Exit with error code if any backups failed
    if failed > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
