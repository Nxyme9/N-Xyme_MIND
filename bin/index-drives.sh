#!/usr/bin/env bash
# Index all drives into the N-Xyme memory system.
# Usage: bin/index-drives.sh [--drive /mnt/DRIVE] [--limit N] [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

DRIVE=""
LIMIT=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --drive) DRIVE="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --dry-run) DRY_RUN="--dry-run"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "========================================"
echo "🧠 N-Xyme Drive Indexer"
echo "========================================"
echo ""

if [ -n "$DRY_RUN" ]; then
    echo "DRY RUN MODE - no files will be indexed"
    echo ""
fi

.venv/bin/python3 - "$DRIVE" "$LIMIT" "$DRY_RUN" << 'PYEOF'
import sys, time, os
sys.path.insert(0, '.')

drive_filter = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
dry_run = len(sys.argv) > 3 and sys.argv[3] == "--dry-run"

from src.memory.multi_drive_scanner import scan_drives, DEFAULT_DRIVES
from src.memory.content_extractor import extract_content
from src.memory.drive_embedder import init_file_tables, embed_file_content, needs_reindex, get_indexed_count

init_file_tables()

drives = [drive_filter] if drive_filter else DEFAULT_DRIVES
print(f"Drives to scan: {drives}")
print()

scanned = 0
embedded = 0
skipped = 0
errors = 0
total_chunks = 0
total_time = 0
start_time = time.time()
last_report = time.time()

for f in scan_drives(drives=drives):
    scanned += 1
    if limit and scanned > limit:
        print(f"\n  Limit reached ({limit} files)")
        break

    try:
        if not needs_reindex(f['path'], f['hash']):
            skipped += 1
            continue

        content = extract_content(f['path'], f['type'], max_chars=20000)
        if not content or len(content) < 50:
            skipped += 1
            continue

        if dry_run:
            embedded += 1
            total_chunks += 1
            continue

        result = embed_file_content(
            f['path'], content, f['hash'], f['type'],
            f['drive'], f['size'], f['mtime']
        )
        if result['embedded'] > 0:
            embedded += 1
            total_chunks += result['embedded']
            total_time += result['time']
        else:
            errors += 1
    except Exception as e:
        errors += 1

    now = time.time()
    if now - last_report >= 10:
        elapsed = now - start_time
        rate = embedded / elapsed if elapsed > 0 else 0
        eta = "N/A"
        if rate > 0 and not limit:
            remaining = 77119 - scanned  # rough estimate
            eta = f"{remaining/rate/60:.0f}min"
        print(f"  [{scanned:6d}] embedded={embedded}, skipped={skipped}, errors={errors}, "
              f"chunks={total_chunks}, rate={rate:.1f}/s, ETA={eta}")
        last_report = now

elapsed = time.time() - start_time

print()
print("========================================")
print("SCAN COMPLETE")
print("========================================")
print(f"  Files scanned: {scanned}")
print(f"  Files embedded: {embedded}")
print(f"  Files skipped: {skipped}")
print(f"  Errors: {errors}")
print(f"  Total chunks: {total_chunks}")
print(f"  Time: {elapsed:.1f}s ({elapsed/3600:.1f} hours)")
if elapsed > 0:
    print(f"  Speed: {embedded/elapsed:.1f} files/sec")

stats = get_indexed_count()
print(f"  Index: {stats['total_files']} files, {stats['total_chunks']} chunks")
print(f"  By drive: {stats['by_drive']}")
print(f"  By type: {stats['by_type']}")
print("========================================")
PYEOF
