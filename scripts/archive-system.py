#!/usr/bin/env python3
"""
PC Archive Script - Index entire system into Graphiti memory

Scans key directories and stores file structure, configs, and key content into Graphiti.
Run: python scripts/archive-system.py

Can be run via PM2 for continuous archiving.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import requests

GRAPHITI_URL = os.getenv("GRAPHITI_URL", "http://localhost:8001")

# Key directories to archive
ARCHIVE_PATHS = [
    "/home/nxyme/.config/opencode",
    "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
    "/home/nxyme/projects",
]

# File extensions to include
INCLUDE_EXTENSIONS = {
    '.json', '.jsonc', '.yaml', '.yml', '.toml',
    '.md', '.txt', '.py', '.sh', '.js', '.ts',
    '.AGENTS.md', 'README', '.env'
}

# Max file size (KB)
MAX_FILE_SIZE = 100


def get_file_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()[:8]


def should_include(path: Path) -> bool:
    """Check if file should be included in archive."""
    # Skip hidden files/dirs
    if any(part.startswith('.') for part in path.parts):
        return False
    # Skip common large dirs
    skip_dirs = {'node_modules', '__pycache__', '.git', 'dist', 'build', 'target', '.venv', 'venv'}
    if any(d in path.parts for d in skip_dirs):
        return False
    # Check extension
    if path.is_file():
        ext = path.suffix.lower()
        name = path.name.lower()
        if ext in INCLUDE_EXTENSIONS or 'readme' in name or 'agents' in name:
            if path.stat().st_size < MAX_FILE_SIZE * 1024:
                return True
    return False


def get_dir_structure(root: Path, max_depth: int = 3) -> str:
    """Get directory structure as tree string."""
    lines = []
    
    def walk(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            if not should_include(item) and not item.is_dir():
                continue
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item.name}")
            if item.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk(item, new_prefix, depth + 1)
    
    walk(root)
    return "\n".join(lines[:100])  # Limit lines


def get_file_content(path: Path) -> str:
    """Get file content (first 2000 chars)."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()[:2000]
    except:
        return "[Unable to read file]"


def scan_directory(root: Path) -> List[Dict]:
    """Scan directory and return file info."""
    files = []
    
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if not should_include(path):
            continue
        try:
            stat = path.stat()
            files.append({
                'path': str(path),
                'name': path.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'relative': str(path.relative_to(root)),
            })
        except:
            pass
    
    return files


def add_to_graphiti(content: str, name: str, metadata: dict = None) -> bool:
    """Add content to Graphiti memory."""
    try:
        resp = requests.post(
            f"{GRAPHITI_URL}/json-rpc",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_add_episode",
                "params": {
                    "text": content,
                    "name": name,
                    "metadata": json.dumps(metadata or {})
                }
            },
            timeout=30
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Error adding to Graphiti: {e}")
        return False


def archive_system():
    """Main archive function."""
    print("=" * 60)
    print("PC ARCHIVE - Indexing system to Graphiti")
    print("=" * 60)
    
    total_files = 0
    archived = 0
    
    for root_path in ARCHIVE_PATHS:
        root = Path(root_path)
        if not root.exists():
            print(f"⚠ Skipping {root_path} - doesn't exist")
            continue
        
        print(f"\n📁 Scanning: {root_path}")
        
        # Get directory structure
        structure = get_dir_structure(root)
        
        # Scan files
        files = scan_directory(root)
        total_files += len(files)
        
        print(f"   Found {len(files)} relevant files")
        
        # Archive directory structure
        dir_info = f"Directory Structure: {root_path}\n{structure}"
        if add_to_graphiti(dir_info, f"dir-structure-{root.name}"):
            archived += 1
            print(f"   ✅ Added structure to memory")
        
        # Archive key config files
        key_files = [f for f in files if any(x in f['name'].lower() for x in 
            ['config', 'agents', 'opencode', 'model', 'mcp', 'graphiti'])]
        
        for f in key_files[:20]:  # Limit to 20 key files
            path = Path(f['path'])
            content = get_file_content(path)
            
            # Summarize the file
            summary = f"File: {f['relative']}\nSize: {f['size']} bytes\nModified: {f['modified']}\n\nContent Preview:\n{content[:1000]}"
            
            if add_to_graphiti(summary, f"file-{get_file_hash(f['relative'])}", {"path": f['relative']}):
                archived += 1
        
        print(f"   ✅ Archived {len(key_files)} key config files")
    
    # Archive system info
    system_info = f"""System Archive Summary:
- Scanned {len(ARCHIVE_PATHS)} directories
- Found {total_files} relevant files
- Archived {archived} entries to Graphiti
- Timestamp: {datetime.now().isoformat()}

System specs: AMD Ryzen 7 7800X3D, RTX 3080 Ti, 32GB DDR5
OpenCode config at: /home/nxyme/.config/opencode
N-Xyme MIND at: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
"""
    add_to_graphiti(system_info, "system-archive-summary")
    
    print(f"\n{'=' * 60}")
    print(f"✅ ARCHIVE COMPLETE")
    print(f"   Total files: {total_files}")
    print(f"   Archived: {archived}")
    print(f"{'=' * 60}")
    
    return {"total": total_files, "archived": archived}


if __name__ == "__main__":
    archive_system()
