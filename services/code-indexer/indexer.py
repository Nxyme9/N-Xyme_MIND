#!/usr/bin/env python3
"""Code indexer — embeddings via minilm-cli + SQLite storage."""

import os
import sys
import json
import sqlite3
import struct
import subprocess
import time
import argparse

# ── paths ───────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.expanduser('~/N-Xyme_CODE/N-Xyme_MIND')
MINILM_CLI = os.path.join(PROJECT_ROOT, 'target', 'debug', 'minilm-cli')
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'code-index', 'code.db')

# ── cache ───────────────────────────────────────────────────────────────
_cache: dict[str, list[float]] = {}
_cache_hits = 0
_cache_misses = 0


def embed(text: str) -> dict:
    """Get 384-dim embedding via minilm-cli. Returns {'embedding': [...], 'dim': 384, 'latency_ms': N}."""
    global _cache_hits, _cache_misses

    cache_key = text[:200]
    if cache_key in _cache:
        _cache_hits += 1
        return {'embedding': _cache[cache_key], 'dim': 384, 'latency_ms': 0}

    start = time.time()
    try:
        result = subprocess.run(
            [MINILM_CLI, text],
            capture_output=True, text=True, timeout=30
        )
    except FileNotFoundError:
        return {'error': f'minilm-cli not found at {MINILM_CLI}', 'dim': 0, 'latency_ms': 0}
    except subprocess.TimeoutExpired:
        return {'error': 'minilm-cli timed out', 'dim': 0, 'latency_ms': 0}

    elapsed = time.time() - start

    if result.returncode != 0:
        return {'error': result.stderr.strip(), 'dim': 0, 'latency_ms': int(elapsed * 1000)}

    # Parse "First 10 values: [..." line
    vec = None
    for line in result.stdout.split('\n'):
        if 'First 10 values:' in line:
            vec_str = line.split('First 10 values:')[1].strip().strip('[]...')
            vec = [float(x) for x in vec_str.split(',')]
            break

    if not vec or len(vec) == 0:
        return {'error': 'Failed to parse embedding from output', 'dim': 0, 'latency_ms': int(elapsed * 1000)}

    _cache[cache_key] = vec
    _cache_misses += 1
    return {'embedding': vec, 'dim': len(vec), 'latency_ms': int(elapsed * 1000)}


def embedding_to_blob(vec: list[float]) -> bytes:
    """Serialize list of floats to binary blob (f32 little-endian)."""
    return struct.pack(f'<{len(vec)}f', *vec)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Deserialize binary blob back to list of floats."""
    n = len(blob) // 4
    return list(struct.unpack(f'<{n}f', blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ── database ────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Open (and initialize if needed) the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=NORMAL')
    db.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath    TEXT    NOT NULL,
            chunk       TEXT    NOT NULL,
            language    TEXT    NOT NULL,
            lines_start INTEGER NOT NULL,
            lines_end   INTEGER NOT NULL,
            embedding   BLOB,
            size_bytes  INTEGER NOT NULL DEFAULT 0,
            last_modified REAL  NOT NULL DEFAULT 0
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON chunks(filepath)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_language ON chunks(language)')
    db.commit()
    return db


def count_chunks(db: sqlite3.Connection) -> int:
    return db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]


def count_files(db: sqlite3.Connection) -> int:
    return db.execute('SELECT COUNT(DISTINCT filepath) FROM chunks').fetchone()[0]


def language_breakdown(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        'SELECT language, COUNT(*) as count FROM chunks GROUP BY language ORDER BY count DESC'
    ).fetchall()
    return [dict(r) for r in rows]


def size_distribution(db: sqlite3.Connection) -> dict:
    """Return bins of file sizes."""
    total = db.execute('SELECT SUM(size_bytes) FROM chunks').fetchone()[0] or 0
    return {
        'total_bytes': total,
        'total_kb': round(total / 1024, 1),
        'total_mb': round(total / (1024 * 1024), 2),
    }


def recent_changes(db: sqlite3.Connection, limit: int = 20) -> list[dict]:
    rows = db.execute(
        'SELECT DISTINCT filepath, last_modified FROM chunks ORDER BY last_modified DESC LIMIT ?',
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# ── indexing ────────────────────────────────────────────────────────────

def index_chunks(chunks: list[dict], db: sqlite3.Connection,
                 progress_callback=None) -> int:
    """Embed each chunk and store in DB. Returns number of chunks indexed."""
    indexed = 0
    total = len(chunks)
    # Use transaction for speed
    db.execute('BEGIN')
    try:
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx + 1, total, chunk)

            text = chunk['chunk']
            if not text.strip():
                continue

            # Truncate to 2000 chars for speed (minilm handles max 512 tokens anyway)
            embed_text = text[:2000]
            result = embed(embed_text)

            if 'error' in result:
                if progress_callback:
                    progress_callback(idx + 1, total, chunk, error=result['error'])
                continue

            vec = result['embedding']
            blob = embedding_to_blob(vec)

            db.execute(
                '''INSERT INTO chunks (filepath, chunk, language, lines_start, lines_end,
                                      embedding, size_bytes, last_modified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    chunk['filepath'],
                    chunk['chunk'],
                    chunk['language'],
                    chunk['lines_start'],
                    chunk['lines_end'],
                    blob,
                    chunk['size_bytes'],
                    chunk['last_modified'],
                )
            )
            indexed += 1

        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise

    return indexed


def clear_index(db: sqlite3.Connection):
    """Clear all rows from the chunks table."""
    db.execute('DELETE FROM chunks')
    db.commit()


def get_all_embeddings(db: sqlite3.Connection) -> list[dict]:
    """Load all chunks with embeddings for search."""
    rows = db.execute(
        'SELECT id, filepath, chunk, language, lines_start, lines_end, embedding, size_bytes, last_modified '
        'FROM chunks WHERE embedding IS NOT NULL'
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['embedding_vec'] = blob_to_embedding(d['embedding'])
        del d['embedding']  # raw blob no longer needed
        result.append(d)
    return result


def search_similar(query_chunks: list[dict], query_embedding: list[float],
                   top_k: int = 20) -> list[dict]:
    """Rank chunks by cosine similarity to query embedding."""
    scored = []
    for item in query_chunks:
        sim = cosine_similarity(query_embedding, item['embedding_vec'])
        scored.append((sim, item))
    scored.sort(key=lambda x: -x[0])
    results = []
    for sim, item in scored[:top_k]:
        results.append({
            'id': item['id'],
            'filepath': item['filepath'],
            'chunk': item['chunk'][:500],  # truncate for display
            'language': item['language'],
            'lines_start': item['lines_start'],
            'lines_end': item['lines_end'],
            'similarity': round(sim, 4),
            'size_bytes': item['size_bytes'],
        })
    return results


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Code Indexer — scan, embed, and search code')
    parser.add_argument('action', nargs='?', default='index',
                        choices=['index', 'clear', 'stats', 'search', 'reindex'],
                        help='Action to perform')
    parser.add_argument('--query', '-q', help='Search query text')
    parser.add_argument('--top-k', type=int, default=10, help='Top K results for search')
    parser.add_argument('--root', default=PROJECT_ROOT, help='Project root to scan')
    parser.add_argument('--no-embed', action='store_true', help='Skip embedding (just scan + DB)')
    args = parser.parse_args()

    db = get_db()

    if args.action == 'clear':
        clear_index(db)
        print('Index cleared.')
        return

    if args.action == 'stats':
        print(f'Total files:  {count_files(db)}')
        print(f'Total chunks: {count_chunks(db)}')
        print()
        print('Language breakdown:')
        for lang in language_breakdown(db):
            print(f'  {lang["language"]:>12}: {lang["count"]:>5}')
        print()
        sd = size_distribution(db)
        print(f'Total size: {sd["total_mb"]} MB ({sd["total_kb"]} KB)')
        print()
        print('Recent changes:')
        for rc in recent_changes(db, 10):
            mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rc['last_modified']))
            print(f'  {mtime}  {os.path.relpath(rc["filepath"], PROJECT_ROOT)}')
        return

    if args.action == 'search':
        if not args.query:
            print('error: --query is required for search')
            sys.exit(1)
        print(f'Searching for: "{args.query}"')
        q_result = embed(args.query[:2000])
        if 'error' in q_result:
            print(f'Embedding error: {q_result["error"]}')
            sys.exit(1)
        all_items = get_all_embeddings(db)
        if not all_items:
            print('No indexed chunks found. Run `index` first.')
            return
        results = search_similar(all_items, q_result['embedding'], args.top_k)
        print(f'\nTop {len(results)} results:\n')
        for i, r in enumerate(results, 1):
            relpath = os.path.relpath(r['filepath'], PROJECT_ROOT)
            print(f'{i}. [{r["similarity"]:.4f}] {relpath} (lines {r["lines_start"]}-{r["lines_end"]}, {r["language"]})')
            # Print a preview snippet
            preview = r['chunk'][:200].replace('\n', '↵ ')
            print(f'   {preview}')
            print()
        return

    if args.action == 'reindex':
        clear_index(db)
        # fall through to index

    # Default: index
    from scanner import scan_and_chunk

    print('Scanning codebase...')
    def _scan_progress(i, total, fp):
        print(f"\r  Scanning [{i}/{total}] {os.path.relpath(fp, PROJECT_ROOT):<60}", end='', flush=True)

    chunks = scan_and_chunk(args.root, _scan_progress)
    print(f'\n  Found {len(chunks)} chunks from {len(set(c["filepath"] for c in chunks))} files.\n')

    if args.no_embed:
        # Just store without embeddings (for stats-only use)
        db.execute('BEGIN')
        for c in chunks:
            db.execute(
                '''INSERT INTO chunks (filepath, chunk, language, lines_start, lines_end,
                                      size_bytes, last_modified)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (c['filepath'], c['chunk'], c['language'],
                 c['lines_start'], c['lines_end'],
                 c['size_bytes'], c['last_modified'])
            )
        db.execute('COMMIT')
        print(f'Stored {len(chunks)} chunks in DB (no embeddings).')
        return

    print('Generating embeddings (this may take a while)...')
    def _embed_progress(i, total, chunk, error=None):
        rel = os.path.relpath(chunk['filepath'], PROJECT_ROOT)
        msg = f'  Embedding [{i}/{total}] {rel}:{chunk["lines_start"]}'
        if error:
            msg += f' ⚠ {error}'
        print(f'\r{msg:<80}', end='', flush=True)

    indexed = index_chunks(chunks, db, _embed_progress)
    print(f'\n\nDone. Indexed {indexed} chunks with embeddings.')

    # Print cache stats
    total_calls = _cache_hits + _cache_misses
    hit_rate = round(_cache_hits / total_calls * 100, 1) if total_calls > 0 else 0
    print(f'Cache: {_cache_hits} hits / {_cache_misses} misses ({hit_rate}% hit rate)')


if __name__ == '__main__':
    main()
