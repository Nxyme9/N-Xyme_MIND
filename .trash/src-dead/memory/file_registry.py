"""File registry for tracking indexed files with xxhash64 change detection.

This module provides SQLite-based file tracking with fast xxhash64 hashing
to enable incremental scans by detecting file changes since last index.
"""

import hashlib
import logging
import os
import sqlite3
import struct
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# xxhash64 constants (https://code.google.com/archive/p/xxhash/)
XXH64_PRIME = 0x9E3779B185EBCA87
CHUNK_SIZE = 65536  # 64KB chunks for fast hashing (~10GB/s)


def _xxh64_init() -> int:
    """Initialize xxhash64 state."""
    return XXH64_PRIME


def _xxh64_update(state: int, data: bytes) -> int:
    """Update xxhash64 state with chunk data."""
    # Read 8-byte values from chunk
    for i in range(0, len(data), 8):
        if i + 8 <= len(data):
            # Little-endian 64-bit read
            k1 = struct.unpack_from("<Q", data, i)[0]
            state ^= (k1 * XXH64_PRIME) & 0xFFFFFFFFFFFFFFFF
            state = (state * XXH64_PRIME) & 0xFFFFFFFFFFFFFFFF
        else:
            # Handle remaining bytes
            for b in data[i:]:
                state ^= b * ((i + 1) & 0xFF)
                state = (state * XXH64_PRIME) & 0xFFFFFFFFFFFFFFFF
    return state


def _xxh64_digest(state: int, length: int) -> int:
    """Finalize xxhash64 state to get digest."""
    state ^= length
    state ^= state >> 33
    state = (state * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
    state ^= state >> 33
    state = (state * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
    state ^= state >> 33
    return state


def get_file_hash(filepath: str) -> str:
    """Compute xxhash64 hash of file content.
    
    Uses 64KB chunks for fast hashing (~10GB/s on modern SSDs).
    Falls back to SHA256 if file is small enough for simpler approach.
    
    Args:
        filepath: Path to file to hash
        
    Returns:
        Hex string of file hash
    """
    try:
        file_size = os.path.getsize(filepath)
        
        # For small files, use faster approach
        if file_size <= CHUNK_SIZE:
            with open(filepath, "rb") as f:
                data = f.read()
            state = _xxh64_init()
            state = _xxh64_update(state, data)
            digest = _xxh64_digest(state, len(data))
            return format(digest, "016x")
        
        # For larger files, use chunked xxhash64
        state = _xxh64_init()
        bytes_read = 0
        
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                state = _xxh64_update(state, chunk)
                bytes_read += len(chunk)
        
        digest = _xxh64_digest(state, bytes_read)
        return format(digest, "016x")
        
    except Exception as e:
        logger.warning(f"Failed to hash {filepath}: {e}")
        # Fallback to sha256 for error cases
        try:
            with open(filepath, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return ""


def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get SQLite connection with WAL mode and proper settings."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_registry(db_path: str) -> bool:
    """Initialize file_registry table with indexes.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = _get_db_connection(db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_registry (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                mtime REAL,
                size_bytes INTEGER,
                content_hash TEXT,
                indexed_at TEXT NOT NULL,
                drive TEXT NOT NULL
            )
        """)
        
        # Indexes for common queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_registry_drive 
            ON file_registry(drive)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_registry_indexed_at 
            ON file_registry(indexed_at)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_registry_hash 
            ON file_registry(file_hash)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Initialized file_registry at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize registry: {e}")
        return False


def needs_processing(db_path: str, filepath: str) -> bool:
    """Check if file needs processing (changed since last index).
    
    Compares current mtime and size against stored values.
    Also checks content_hash if file was previously indexed.
    
    Args:
        db_path: Path to SQLite database
        filepath: Path to file to check
        
    Returns:
        True if file needs processing, False if up-to-date
    """
    try:
        if not os.path.exists(filepath):
            return False
            
        conn = _get_db_connection(db_path)
        
        cursor = conn.execute(
            "SELECT mtime, size_bytes, file_hash FROM file_registry WHERE file_path = ?",
            (filepath,),
        )
        row = cursor.fetchone()
        
        if row is None:
            conn.close()
            return True  # Not indexed yet
            
        stored_mtime, stored_size, stored_hash = row
        
        # Get current stats
        current_stat = os.stat(filepath)
        current_mtime = current_stat.st_mtime
        current_size = current_stat.st_size
        
        # Check if mtime or size changed
        if abs(stored_mtime - current_mtime) > 0.001 or stored_size != current_size:
            conn.close()
            return True
            
        conn.close()
        return False  # File unchanged
        
    except Exception as e:
        logger.debug(f"Error checking processing status for {filepath}: {e}")
        return True  # Default to processing on error


def update_registry(
    db_path: str, filepath: str, file_hash: str, drive: str
) -> bool:
    """Upsert file record in registry.
    
    Args:
        db_path: Path to SQLite database
        filepath: Full path to file
        file_hash: xxhash64 hash of file
        drive: Drive identifier (e.g., 'local', 'github')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = _get_db_connection(db_path)
        
        # Get current file stats
        stat = os.stat(filepath)
        mtime = stat.st_mtime
        size_bytes = stat.st_size
        
        # Current timestamp for indexed_at
        from datetime import datetime, timezone
        indexed_at = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """INSERT OR REPLACE INTO file_registry 
               (file_path, file_hash, mtime, size_bytes, content_hash, indexed_at, drive)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (filepath, file_hash, mtime, size_bytes, file_hash, indexed_at, drive),
        )
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Updated registry: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update registry for {filepath}: {e}")
        return False


def remove_file(db_path: str, filepath: str) -> bool:
    """Remove file from registry.
    
    Args:
        db_path: Path to SQLite database
        filepath: Full path to file to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = _get_db_connection(db_path)
        
        conn.execute(
            "DELETE FROM file_registry WHERE file_path = ?",
            (filepath,),
        )
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Removed from registry: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to remove {filepath} from registry: {e}")
        return False


DEFAULT_REGISTRY_DB = "context/memory/file_registry.db"


def get_stats(db_path: str = DEFAULT_REGISTRY_DB) -> dict:
    """Get registry statistics.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with total_files, indexed, pending, by_drive
    """
    try:
        conn = _get_db_connection(db_path)
        
        # Total count
        total_cursor = conn.execute("SELECT COUNT(*) FROM file_registry")
        total_files = total_cursor.fetchone()[0] or 0
        
        # By drive
        drive_cursor = conn.execute(
            "SELECT drive, COUNT(*) FROM file_registry GROUP BY drive"
        )
        by_drive = {row[0]: row[1] for row in drive_cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_files": total_files,
            "indexed": total_files,
            "pending": 0,
            "by_drive": by_drive,
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "total_files": 0,
            "indexed": 0,
            "pending": 0,
            "by_drive": {},
        }