#!/usr/bin/env python3
"""
Log Rotation Script for N-Xyme Catalyst.

Rotates and compresses log files to prevent disk space issues.
Supports configurable retention policies and compression.

Usage:
    python scripts/log-rotation.py                    # Run rotation
    python scripts/log-rotation.py --dry-run          # Preview changes
    python scripts/log-rotation.py --config           # Show current config
    python scripts/log-rotation.py --cleanup           # Remove old logs
"""

import os
import sys
import gzip
import shutil
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Configuration
CONFIG = {
    "log_directories": [
        "logs",
        ".heartbeat",
        ".zap",
    ],
    "log_patterns": [
        "*.log",
        "*.log.*",
        "*.out",
        "*.err",
    ],
    "max_size_mb": 50,  # Rotate if file exceeds this size
    "max_age_days": 30,  # Delete logs older than this
    "max_rotated_files": 10,  # Keep this many rotated files
    "compress_rotated": True,  # Compress rotated files
    "exclude_patterns": [
        "*.gz",  # Don't re-compress gzipped files
        "*.zip",  # Don't touch zip files
    ],
}

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_log_files() -> List[Path]:
    """Find all log files in configured directories."""
    log_files = []

    for log_dir in CONFIG["log_directories"]:
        dir_path = PROJECT_ROOT / log_dir
        if not dir_path.exists():
            logger.debug(f"Log directory not found: {dir_path}")
            continue

        for pattern in CONFIG["log_patterns"]:
            for file_path in dir_path.rglob(pattern):
                # Skip excluded patterns
                if any(file_path.match(exclude) for exclude in CONFIG["exclude_patterns"]):
                    continue
                log_files.append(file_path)

    return sorted(log_files)


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0


def get_file_age_days(file_path: Path) -> float:
    """Get file age in days."""
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return (datetime.now() - mtime).total_seconds() / (24 * 3600)
    except OSError:
        return 0.0


def rotate_file(file_path: Path, dry_run: bool = False) -> bool:
    """Rotate a single log file.

    Args:
        file_path: Path to log file to rotate.
        dry_run: If True, only show what would be done.

    Returns:
        True if rotation was performed (or would be performed in dry-run).
    """
    size_mb = get_file_size_mb(file_path)

    if size_mb < CONFIG["max_size_mb"]:
        logger.debug(f"Skipping {file_path.name} ({size_mb:.1f}MB < {CONFIG['max_size_mb']}MB)")
        return False

    # Generate rotation timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotated_name = f"{file_path.name}.{timestamp}"
    rotated_path = file_path.parent / rotated_name

    if dry_run:
        logger.info(f"[DRY RUN] Would rotate: {file_path.name} -> {rotated_name} ({size_mb:.1f}MB)")
        return True

    try:
        # Create rotated file
        if CONFIG["compress_rotated"]:
            # Compress and rotate
            gz_path = rotated_path.with_suffix(rotated_path.suffix + ".gz")
            with open(file_path, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            logger.info(
                f"Rotated and compressed: {file_path.name} -> {gz_path.name} ({size_mb:.1f}MB)"
            )
        else:
            # Simple rotation
            shutil.copy2(file_path, rotated_path)
            logger.info(f"Rotated: {file_path.name} -> {rotated_name} ({size_mb:.1f}MB)")

        # Truncate original file
        file_path.write_text("", encoding="utf-8")

        return True

    except Exception as e:
        logger.error(f"Failed to rotate {file_path}: {e}")
        return False


def cleanup_old_logs(dry_run: bool = False) -> int:
    """Remove old log files based on retention policy.

    Args:
        dry_run: If True, only show what would be deleted.

    Returns:
        Number of files deleted (or would be deleted in dry-run).
    """
    deleted_count = 0

    for log_dir in CONFIG["log_directories"]:
        dir_path = PROJECT_ROOT / log_dir
        if not dir_path.exists():
            continue

        # Find rotated files (with timestamps)
        for pattern in ["*.log.*", "*.log.*.gz"]:
            for file_path in dir_path.rglob(pattern):
                age_days = get_file_age_days(file_path)

                if age_days > CONFIG["max_age_days"]:
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would delete: {file_path.name} (age: {age_days:.1f} days)"
                        )
                    else:
                        try:
                            file_path.unlink()
                            logger.info(
                                f"Deleted old log: {file_path.name} (age: {age_days:.1f} days)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to delete {file_path}: {e}")
                            continue
                    deleted_count += 1

    return deleted_count


def enforce_rotation_limit(dry_run: bool = False) -> int:
    """Enforce maximum number of rotated files per log.

    Args:
        dry_run: If True, only show what would be deleted.

    Returns:
        Number of files deleted (or would be deleted in dry-run).
    """
    deleted_count = 0

    for log_dir in CONFIG["log_directories"]:
        dir_path = PROJECT_ROOT / log_dir
        if not dir_path.exists():
            continue

        # Group rotated files by base name
        rotated_files: Dict[str, List[Path]] = {}

        for pattern in ["*.log.*", "*.log.*.gz"]:
            for file_path in dir_path.rglob(pattern):
                # Extract base name (remove timestamp and extension)
                name_parts = file_path.name.split(".")
                if len(name_parts) >= 2:
                    base_name = name_parts[0]  # e.g., "jarvis" from "jarvis.log.20260319_120000.gz"
                    if base_name not in rotated_files:
                        rotated_files[base_name] = []
                    rotated_files[base_name].append(file_path)

        # Enforce limit for each base name
        for base_name, files in rotated_files.items():
            # Sort by modification time (oldest first)
            files.sort(key=lambda p: p.stat().st_mtime)

            # Delete excess files
            while len(files) > CONFIG["max_rotated_files"]:
                oldest = files.pop(0)

                if dry_run:
                    logger.info(f"[DRY RUN] Would delete excess: {oldest.name}")
                else:
                    try:
                        oldest.unlink()
                        logger.info(f"Deleted excess log: {oldest.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete {oldest}: {e}")
                        continue
                deleted_count += 1

    return deleted_count


def show_config():
    """Display current configuration."""
    print("\nLog Rotation Configuration:")
    print("=" * 50)

    for key, value in CONFIG.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")

    print("\nLog Directories (absolute paths):")
    for log_dir in CONFIG["log_directories"]:
        dir_path = PROJECT_ROOT / log_dir
        exists = "✓" if dir_path.exists() else "✗"
        print(f"  {exists} {dir_path}")


def show_status():
    """Show current log file status."""
    print("\nLog File Status:")
    print("=" * 50)

    log_files = get_log_files()

    if not log_files:
        print("No log files found.")
        return

    total_size = 0.0

    for file_path in log_files:
        size_mb = get_file_size_mb(file_path)
        age_days = get_file_age_days(file_path)
        total_size += size_mb

        status = "NEEDS ROTATION" if size_mb >= CONFIG["max_size_mb"] else "OK"
        print(f"{file_path.name:30} {size_mb:8.1f}MB {age_days:6.1f}d {status}")

    print(f"\nTotal: {len(log_files)} files, {total_size:.1f}MB")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Log rotation for N-Xyme Catalyst")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    parser.add_argument("--status", action="store_true", help="Show log file status")
    parser.add_argument("--cleanup", action="store_true", help="Only run cleanup (remove old logs)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.config:
        show_config()
        return

    if args.status:
        show_status()
        return

    print("=" * 60)
    print("LOG ROTATION - N-Xyme Catalyst")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE] No changes will be made\n")

    # Initialize counters
    rotated_count = 0
    deleted_count = 0
    excess_count = 0

    # Step 1: Rotate large files
    print("\n[STEP 1] Rotating large log files...")
    log_files = get_log_files()

    for file_path in log_files:
        if rotate_file(file_path, args.dry_run):
            rotated_count += 1

    print(f"Rotated {rotated_count} files")

    # Step 2: Cleanup old logs
    print("\n[STEP 2] Cleaning up old logs...")
    deleted_count = cleanup_old_logs(args.dry_run)
    print(f"Deleted {deleted_count} old files")

    # Step 3: Enforce rotation limits
    print("\n[STEP 3] Enforcing rotation limits...")
    excess_count = enforce_rotation_limit(args.dry_run)
    print(f"Removed {excess_count} excess files")

    # Summary
    print("\n" + "=" * 60)
    print("ROTATION COMPLETE")
    print("=" * 60)
    print(f"Files rotated: {rotated_count}")
    print(f"Old files deleted: {deleted_count}")
    print(f"Excess files removed: {excess_count}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply.")


if __name__ == "__main__":
    main()
