"""Drive indexer CLI — orchestrates scan → extract → embed pipeline."""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.memory.multi_drive_scanner import scan_drives, DEFAULT_DRIVES
from src.memory.content_extractor import extract_content
from src.memory.drive_embedder import (
    init_file_tables,
    embed_file_content,
    needs_reindex,
    get_indexed_count,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Index drives into N-Xyme memory system"
    )
    parser.add_argument("--drive", type=str, help="Single drive to scan (default: all)")
    parser.add_argument("--limit", type=int, help="Max files to process")
    parser.add_argument("--dry-run", action="store_true", help="Scan without indexing")
    args = parser.parse_args()

    drives = [args.drive] if args.drive else DEFAULT_DRIVES
    print("=" * 60)
    print("🧠 N-Xyme Drive Indexer")
    print("=" * 60)
    print(f"Drives: {drives}")
    if args.dry_run:
        print("DRY RUN MODE")
    print()

    init_file_tables()

    scanned = 0
    embedded = 0
    skipped = 0
    errors = 0
    total_chunks = 0
    total_time = 0.0
    start_time = time.time()
    last_report = time.time()

    for f in scan_drives(drives=drives):
        scanned += 1
        if args.limit and scanned > args.limit:
            print(f"\n  Limit reached ({args.limit} files)")
            break

        try:
            if not needs_reindex(f["path"], f["hash"]):
                skipped += 1
                continue

            content = extract_content(f["path"], f["type"], max_chars=20000)
            if not content or len(content) < 50:
                skipped += 1
                continue

            if args.dry_run:
                embedded += 1
                total_chunks += 1
                continue

            result = embed_file_content(
                f["path"],
                content,
                f["hash"],
                f["type"],
                f["drive"],
                f["size"],
                f["mtime"],
            )
            if result["embedded"] > 0:
                embedded += 1
                total_chunks += result["embedded"]
                total_time += result["time"]
            else:
                errors += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.debug(f"Error processing {f['path']}: {e}")

        # Progress report every 10 seconds
        now = time.time()
        if now - last_report >= 10:
            elapsed = now - start_time
            rate = embedded / elapsed if elapsed > 0 else 0
            print(
                f"  [{scanned:6d}] embedded={embedded}, skipped={skipped}, "
                f"errors={errors}, chunks={total_chunks}, rate={rate:.1f}/s"
            )
            last_report = now

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"  Files scanned: {scanned}")
    print(f"  Files embedded: {embedded}")
    print(f"  Files skipped: {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Time: {elapsed:.1f}s ({elapsed / 3600:.1f} hours)")
    if elapsed > 0:
        print(f"  Speed: {embedded / elapsed:.1f} files/sec")

    stats = get_indexed_count()
    print(f"  Index: {stats['total_files']} files, {stats['total_chunks']} chunks")
    print(f"  By drive: {stats['by_drive']}")
    print(f"  By type: {stats['by_type']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
