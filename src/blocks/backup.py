#!/usr/bin/env python3
"""
Backup Script for N-Xyme Catalyst.

Creates backups of critical configuration and data files.
Supports incremental backups, compression, and retention policies.

Usage:
    python scripts/backup.py                    # Run full backup
    python scripts/backup.py --incremental      # Run incremental backup
    python scripts/backup.py --dry-run          # Preview changes
    python scripts/backup.py --list             # List existing backups
    python scripts/backup.py --restore          # Restore from latest backup
    python scripts/backup.py --cleanup          # Remove old backups
"""

import os
import sys
import json
import shutil
import logging
import argparse
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Optional
import zipfile

# Configuration
CONFIG = {
    "backup_root": "backups",
    "max_backups": 10,  # Keep this many backups
    "max_age_days": 90,  # Delete backups older than this
    "compress": True,  # Compress backups
    "incremental": True,  # Support incremental backups
    # Directories to backup
    "include_dirs": [
        "configs",
        "scripts",
        "docs",
        "data",
        "memory",
        ".github",
    ],
    # Files to backup
    "include_files": [
        "docker-compose.yml",
        "docker-compose.override.yml",
        "ecosystem.config.js",
        "package.json",
        "pnpm-workspace.yaml",
        "pyproject.toml",
        "requirements.txt",
        "Makefile",
        ".env.example",
        ".gitignore",
        "AGENTS.md",
        "README.md",
        "LICENSE",
    ],
    # Patterns to exclude
    "exclude_patterns": [
        "*.pyc",
        "__pycache__",
        "node_modules",
        ".git",
        "*.log",
        "*.tmp",
        "*.temp",
        ".sessions",
        ".sisyphus",
        ".zap",
        ".heartbeat",
        ".pytest_cache",
        ".ruff_cache",
    ],
    # Critical data directories (always full backup)
    "critical_dirs": [
        "configs",
        "memory",
        "data",
    ],
}

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_backup_dir() -> Path:
    """Get the backup directory path."""
    backup_dir = PROJECT_ROOT / CONFIG["backup_root"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except (OSError, IOError):
        return ""


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from backup."""
    path_str = str(path)

    for pattern in CONFIG["exclude_patterns"]:
        if pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True

    return False


def get_files_to_backup() -> List[Path]:
    """Get list of files to backup."""
    files = []

    # Add individual files
    for file_name in CONFIG["include_files"]:
        file_path = PROJECT_ROOT / file_name
        if file_path.exists() and not should_exclude(file_path):
            files.append(file_path)

    # Add files from directories
    for dir_name in CONFIG["include_dirs"]:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and not should_exclude(file_path):
                files.append(file_path)

    return sorted(set(files))


def get_changed_files(last_backup_time: Optional[datetime] = None) -> List[Path]:
    """Get files changed since last backup."""
    all_files = get_files_to_backup()

    if last_backup_time is None:
        return all_files

    changed_files = []
    for file_path in all_files:
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime > last_backup_time:
                changed_files.append(file_path)
        except OSError:
            # If we can't get mtime, include the file
            changed_files.append(file_path)

    return changed_files


def create_backup_archive(
    files: List[Path], backup_name: str, dry_run: bool = False
) -> Optional[Path]:
    """Create a backup archive.

    Args:
        files: List of files to include.
        backup_name: Name for the backup.
        dry_run: If True, only show what would be done.

    Returns:
        Path to created archive, or None if dry_run.
    """
    backup_dir = get_backup_dir()

    if CONFIG["compress"]:
        archive_path = backup_dir / f"{backup_name}.zip"

        if dry_run:
            total_size = sum(f.stat().st_size for f in files if f.exists())
            logger.info(
                f"[DRY RUN] Would create: {archive_path.name} ({total_size / (1024 * 1024):.1f}MB, {len(files)} files)"
            )
            return None

        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    if not file_path.exists():
                        continue

                    # Calculate relative path from project root
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    zf.write(file_path, rel_path)

            size_mb = archive_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"Created backup: {archive_path.name} ({size_mb:.1f}MB, {len(files)} files)"
            )
            return archive_path

        except Exception as e:
            logger.error(f"Failed to create backup archive: {e}")
            return None

    else:
        # Create uncompressed backup directory
        backup_path = backup_dir / backup_name

        if dry_run:
            total_size = sum(f.stat().st_size for f in files if f.exists())
            logger.info(
                f"[DRY RUN] Would create: {backup_path.name} ({total_size / (1024 * 1024):.1f}MB, {len(files)} files)"
            )
            return None

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            for file_path in files:
                if not file_path.exists():
                    continue

                # Calculate relative path from project root
                rel_path = file_path.relative_to(PROJECT_ROOT)
                dest_path = backup_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)

            # Calculate total size
            total_size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)

            logger.info(f"Created backup: {backup_path.name} ({size_mb:.1f}MB, {len(files)} files)")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None


def get_last_backup_time() -> Optional[datetime]:
    """Get the timestamp of the last backup."""
    backup_dir = get_backup_dir()

    # Find the most recent backup
    backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    for backup in backups:
        if backup.is_file() and backup.suffix == ".zip":
            return datetime.fromtimestamp(backup.stat().st_mtime)
        elif backup.is_dir():
            return datetime.fromtimestamp(backup.stat().st_mtime)

    return None


def list_backups():
    """List existing backups."""
    backup_dir = get_backup_dir()

    print("\nExisting Backups:")
    print("=" * 60)

    backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not backups:
        print("No backups found.")
        return

    for backup in backups:
        if backup.is_file() and backup.suffix == ".zip":
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            age_days = (datetime.now() - mtime).days

            print(
                f"{backup.name:40} {size_mb:8.1f}MB {mtime.strftime('%Y-%m-%d %H:%M'):20} {age_days:3}d"
            )

        elif backup.is_dir():
            # Calculate directory size
            total_size = sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            age_days = (datetime.now() - mtime).days

            print(
                f"{backup.name:40} {size_mb:8.1f}MB {mtime.strftime('%Y-%m-%d %H:%M'):20} {age_days:3}d"
            )


def cleanup_old_backups(dry_run: bool = False) -> int:
    """Remove old backups based on retention policy.

    Args:
        dry_run: If True, only show what would be deleted.

    Returns:
        Number of backups deleted.
    """
    backup_dir = get_backup_dir()
    deleted_count = 0

    # Get all backups sorted by modification time (oldest first)
    backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime)

    # Remove backups older than max_age_days
    for backup in backups:
        try:
            age_days = (datetime.now() - datetime.fromtimestamp(backup.stat().st_mtime)).days

            if age_days > CONFIG["max_age_days"]:
                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would delete old backup: {backup.name} (age: {age_days}d)"
                    )
                else:
                    if backup.is_file():
                        backup.unlink()
                    elif backup.is_dir():
                        shutil.rmtree(backup)
                    logger.info(f"Deleted old backup: {backup.name} (age: {age_days}d)")
                deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to process {backup}: {e}")

    # Remove excess backups (keep only max_backups)
    backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    while len(backups) > CONFIG["max_backups"]:
        oldest = backups.pop()

        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would delete excess backup: {oldest.name}")
            else:
                if oldest.is_file():
                    oldest.unlink()
                elif oldest.is_dir():
                    shutil.rmtree(oldest)
                logger.info(f"Deleted excess backup: {oldest.name}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {oldest}: {e}")

    return deleted_count


def restore_backup(backup_path: Optional[Path] = None, dry_run: bool = False) -> bool:
    """Restore from a backup.

    Args:
        backup_path: Path to backup to restore from. If None, uses latest.
        dry_run: If True, only show what would be restored.

    Returns:
        True if restore was successful.
    """
    backup_dir = get_backup_dir()

    if backup_path is None:
        # Find the latest backup
        backups = sorted(backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

        for backup in backups:
            if backup.is_file() and backup.suffix == ".zip":
                backup_path = backup
                break
            elif backup.is_dir():
                backup_path = backup
                break

        if backup_path is None:
            logger.error("No backups found to restore from.")
            return False

    print("\n" + "=" * 60)
    print("RESTORE BACKUP")
    print("=" * 60)
    print(f"Restoring from: {backup_path.name}")

    if dry_run:
        print("\n[DRY RUN MODE] No changes will be made\n")

    try:
        if backup_path.is_file() and backup_path.suffix == ".zip":
            # Extract zip archive
            if dry_run:
                with zipfile.ZipFile(backup_path, "r") as zf:
                    file_list = zf.namelist()
                    print(f"Would restore {len(file_list)} files:")
                    for file in file_list[:20]:  # Show first 20
                        print(f"  - {file}")
                    if len(file_list) > 20:
                        print(f"  ... and {len(file_list) - 20} more")
            else:
                with zipfile.ZipFile(backup_path, "r") as zf:
                    zf.extractall(PROJECT_ROOT)
                logger.info(f"Restored {len(zf.namelist())} files from {backup_path.name}")

        elif backup_path.is_dir():
            # Copy directory contents
            if dry_run:
                file_list = list(backup_path.rglob("*"))
                file_list = [f for f in file_list if f.is_file()]
                print(f"Would restore {len(file_list)} files:")
                for file in file_list[:20]:  # Show first 20
                    rel_path = file.relative_to(backup_path)
                    print(f"  - {rel_path}")
                if len(file_list) > 20:
                    print(f"  ... and {len(file_list) - 20} more")
            else:
                for item in backup_path.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(backup_path)
                        dest_path = PROJECT_ROOT / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)

                file_count = len(list(backup_path.rglob("*")))
                logger.info(f"Restored {file_count} files from {backup_path.name}")

        if not dry_run:
            print("\n[SUCCESS] Restore completed!")
            print("NOTE: You may need to restart services for changes to take effect.")

        return True

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def show_status():
    """Show backup status and statistics."""
    backup_dir = get_backup_dir()

    print("\nBackup Status:")
    print("=" * 60)

    # Count backups
    backups = list(backup_dir.glob("*"))
    zip_backups = [b for b in backups if b.is_file() and b.suffix == ".zip"]
    dir_backups = [b for b in backups if b.is_dir()]

    print(f"Total backups: {len(backups)}")
    print(f"  - Compressed: {len(zip_backups)}")
    print(f"  - Uncompressed: {len(dir_backups)}")

    # Calculate total size
    total_size = 0
    for backup in backups:
        if backup.is_file():
            total_size += backup.stat().st_size
        elif backup.is_dir():
            total_size += sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())

    print(f"Total size: {total_size / (1024 * 1024):.1f}MB")

    # Show last backup
    last_backup_time = get_last_backup_time()
    if last_backup_time:
        age_hours = (datetime.now() - last_backup_time).total_seconds() / 3600
        print(f"Last backup: {last_backup_time.strftime('%Y-%m-%d %H:%M')} ({age_hours:.1f}h ago)")
    else:
        print("Last backup: Never")

    # Show files that would be backed up
    files = get_files_to_backup()
    total_file_size = sum(f.stat().st_size for f in files if f.exists())
    print(f"\nFiles to backup: {len(files)} ({total_file_size / (1024 * 1024):.1f}MB)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backup for N-Xyme Catalyst")
    parser.add_argument("--incremental", action="store_true", help="Run incremental backup")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--restore", action="store_true", help="Restore from latest backup")
    parser.add_argument("--restore-from", type=str, help="Restore from specific backup")
    parser.add_argument(
        "--cleanup", action="store_true", help="Only run cleanup (remove old backups)"
    )
    parser.add_argument("--status", action="store_true", help="Show backup status")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        list_backups()
        return

    if args.status:
        show_status()
        return

    if args.restore or args.restore_from:
        backup_path = Path(args.restore_from) if args.restore_from else None
        restore_backup(backup_path, args.dry_run)
        return

    print("=" * 60)
    print("BACKUP - N-Xyme Catalyst")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE] No changes will be made\n")

    # Generate backup name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_type = "incremental" if args.incremental else "full"
    backup_name = f"backup_{backup_type}_{timestamp}"

    # Get files to backup
    if args.incremental:
        last_backup_time = get_last_backup_time()
        files = get_changed_files(last_backup_time)
        print(f"\nIncremental backup: {len(files)} changed files")
    else:
        files = get_files_to_backup()
        print(f"\nFull backup: {len(files)} files")

    if not files:
        print("No files to backup.")
        return

    # Create backup
    print("\n[STEP 1] Creating backup...")
    backup_path = create_backup_archive(files, backup_name, args.dry_run)

    # Cleanup old backups
    if not args.cleanup:
        print("\n[STEP 2] Cleaning up old backups...")
        deleted_count = cleanup_old_backups(args.dry_run)
        print(f"Deleted {deleted_count} old backups")

    # Summary
    print("\n" + "=" * 60)
    print("BACKUP COMPLETE")
    print("=" * 60)

    if backup_path:
        print(f"Backup created: {backup_path.name}")
    else:
        print("[DRY RUN] No backup was created")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply.")


if __name__ == "__main__":
    main()
