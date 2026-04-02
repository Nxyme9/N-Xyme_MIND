#!/usr/bin/env python3
"""
index_local.py — Index Athena memory files into ChromaDB

Scans all Athena memory directories, chunks files, embeds via Ollama,
stores in ChromaDB for local semantic search without Supabase.

Usage:
    python scripts/index_local.py              # Delta index (only changed files)
    python scripts/index_local.py --force      # Re-index everything
    python scripts/index_local.py --dry-run    # Show what would be indexed
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from athena.memory.sync import chunk_text
from athena.memory.vectors import get_embedding
from athena.memory.local_vectors import index_document

# === Directory to Collection Mapping ===
# Maps directory name patterns to ChromaDB collection names
DIR_TO_COLLECTION = {
    "session_logs": "sessions",
    "case_studies": "case_studies",
    "protocols": "protocols",
    "capabilities": "capabilities",
    "workflows": "workflows",
    "modules": "system_docs",
    "memory": "user_profile",
    "playbooks": "playbooks",
    "references": "references",
    "frameworks": "frameworks",
    "entities": "entities",
    "context": "system_docs",
    "skills": "capabilities",
    "docs": "system_docs",
}

# Core memory directories (from config.py)
CORE_DIRS = [
    ".context/memories/session_logs",
    ".context/memories/case_studies",
    ".agent/skills/protocols",
    ".agent/skills/capabilities",
    ".agent/workflows",
    ".framework/v8.2-stable/modules",
]

# Extended memory directories
EXTENDED_DIRS = [
    ".athena/memory",
    ".agent/skills/playbooks",
    ".agent/skills/references",
    ".agent/skills/frameworks",
    ".agent/skills/entities",
    "examples/protocols",
    "examples/skills",
    "docs",
    ".context",
]

# Metadata file for tracking index state
INDEX_STATE_FILE = PROJECT_ROOT / ".agent" / "state" / "index_state.json"


def get_collection_name(dir_path: str) -> str:
    """Determine ChromaDB collection name from directory path."""
    # Extract the last meaningful directory component
    path = Path(dir_path)
    for part in reversed(path.parts):
        if part in DIR_TO_COLLECTION:
            return DIR_TO_COLLECTION[part]
    
    # Fallback: use last directory name sanitized
    return path.name.replace("-", "_").replace(" ", "_").lower()


def load_index_state() -> Dict[str, float]:
    """Load the index state (file_path -> last_indexed_mtime)."""
    if INDEX_STATE_FILE.exists():
        try:
            return json.loads(INDEX_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_index_state(state: Dict[str, float]) -> None:
    """Save the index state to disk."""
    INDEX_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_STATE_FILE.write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def should_index_file(file_path: Path, state: Dict[str, float], force: bool) -> bool:
    """Check if a file should be indexed based on modification time."""
    if force:
        return True
    
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    current_mtime = file_path.stat().st_mtime
    last_mtime = state.get(rel_path, 0)
    
    return current_mtime > last_mtime


def index_single_file(
    file_path: Path,
    collection: str,
    project_root: Path,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> int:
    """Index a single markdown file into ChromaDB.
    
    Returns:
        Number of chunks indexed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"  ⚠ Error reading {file_path.name}: {e}")
        return 0
    
    if not content.strip():
        return 0
    
    # Chunk the content
    chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return 0
    
    # Get relative path for storage
    try:
        rel_path = str(file_path.relative_to(project_root))
    except ValueError:
        rel_path = str(file_path)
    
    # Extract title from first H1 header or filename
    title = file_path.stem
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break
    
    # Index each chunk
    indexed_count = 0
    for i, chunk in enumerate(chunks):
        doc_id = f"{rel_path}::chunk_{i}"
        
        try:
            embedding = get_embedding(chunk)
        except Exception as e:
            print(f"  ⚠ Embedding error for {file_path.name} chunk {i}: {e}")
            continue
        
        metadata = {
            "file_path": rel_path,
            "title": title,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        
        if index_document(collection, doc_id, chunk, embedding, metadata):
            indexed_count += 1
    
    return indexed_count


def index_directory(
    dir_path: str,
    project_root: Path,
    state: Dict[str, float],
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Index all markdown files in a directory.
    
    Returns:
        Dict with 'files' and 'chunks' counts.
    """
    full_path = project_root / dir_path
    if not full_path.exists():
        return {"files": 0, "chunks": 0}
    
    collection = get_collection_name(dir_path)
    
    # Find all .md files
    md_files = sorted(full_path.rglob("*.md"))
    if not md_files:
        return {"files": 0, "chunks": 0}
    
    print(f"\n📁 {dir_path}")
    print(f"   Collection: {collection}")
    print(f"   Files found: {len(md_files)}")
    
    files_to_index = [
        f for f in md_files
        if should_index_file(f, state, force)
    ]
    
    if not files_to_index:
        print(f"   ✓ All files up to date")
        return {"files": 0, "chunks": 0}
    
    print(f"   Files to index: {len(files_to_index)}")
    
    if dry_run:
        for f in files_to_index:
            print(f"   - {f.name}")
        return {"files": len(files_to_index), "chunks": 0}
    
    total_chunks = 0
    indexed_files = 0
    errors = 0
    
    for i, md_file in enumerate(files_to_index, 1):
        try:
            chunks = index_single_file(md_file, collection, project_root)
            if chunks > 0:
                total_chunks += chunks
                indexed_files += 1
                rel_path = str(md_file.relative_to(project_root))
                state[rel_path] = md_file.stat().st_mtime
                
                if i % 10 == 0 or i == len(files_to_index):
                    print(f"   Progress: {i}/{len(files_to_index)} files ({total_chunks} chunks)")
            else:
                print(f"   ⚠ Skipped (empty): {md_file.name}")
        except Exception as e:
            errors += 1
            print(f"   ✗ Error indexing {md_file.name}: {e}")
    
    print(f"   ✓ Indexed: {indexed_files} files, {total_chunks} chunks")
    if errors:
        print(f"   ⚠ Errors: {errors}")
    
    return {"files": indexed_files, "chunks": total_chunks}


def index_all_files(
    force: bool = False,
    dry_run: bool = False,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> None:
    """Main indexing function — scans all memory directories."""
    print("=" * 60)
    print("Athena Local Indexer — ChromaDB + Ollama")
    print("=" * 60)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Mode: {'FORCE' if force else 'DELTA'}")
    if dry_run:
        print("Mode: DRY RUN (no changes)")
    print(f"Chunk size: {chunk_size}, Overlap: {overlap}")
    
    # Load index state
    state = {} if force else load_index_state()
    
    all_dirs = CORE_DIRS + EXTENDED_DIRS
    total_stats = {"files": 0, "chunks": 0, "dirs": 0}
    start_time = time.time()
    
    for dir_path in all_dirs:
        stats = index_directory(
            dir_path,
            PROJECT_ROOT,
            state,
            force=force,
            dry_run=dry_run,
        )
        total_stats["files"] += stats["files"]
        total_stats["chunks"] += stats["chunks"]
        if stats["files"] > 0:
            total_stats["dirs"] += 1
    
    # Save state (unless dry run or force)
    if not dry_run and not force:
        save_index_state(state)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Directories processed: {total_stats['dirs']}")
    print(f"Files indexed: {total_stats['files']}")
    print(f"Total chunks: {total_stats['chunks']}")
    print(f"Time elapsed: {elapsed:.1f}s")
    
    if dry_run:
        print("\n⚠ Dry run — no changes made")
    else:
        print(f"\n✓ Index state saved to {INDEX_STATE_FILE.relative_to(PROJECT_ROOT)}")
    
    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(
        description="Index Athena memory files into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/index_local.py              # Delta index (only changed files)
  python scripts/index_local.py --force      # Re-index everything
  python scripts/index_local.py --dry-run    # Show what would be indexed
  python scripts/index_local.py --chunk-size 2000 --overlap 400
        """,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all files, ignoring modification times",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without making changes",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size in characters (default: 1000)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Chunk overlap in characters (default: 200)",
    )
    
    args = parser.parse_args()
    
    try:
        index_all_files(
            force=args.force,
            dry_run=args.dry_run,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
