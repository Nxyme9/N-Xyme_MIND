#!/usr/bin/env python3
"""Code scanner — walks project, chunks files intelligently by function/class."""

import os
import re
import time
from pathlib import Path


# ── config ──────────────────────────────────────────────────────────────
EXTS = {'.py', '.rs', '.js', '.ts', '.mojo', '.sh'}

EXCLUDE_DIRS = {
    '.git', 'node_modules', 'target', '__pycache__', '.venv',
    'venv', 'dist', 'build', '.npm', '.cargo', '.opencode',
    '.vscode', 'idea', '.idea', '.mypy_cache', '.pytest_cache',
    '.ruff_cache', '.tox', '.eggs', 'egg-info',
}

EXCLUDE_PREFIXES = {
    '.',  # dotfiles / dotdirs
}

SMALL_FILE_LINES = 50   # files under this = one chunk
MIN_CHUNK_LINES = 10    # discard chunks smaller than this


# ── language-specific chunk boundary regexes ────────────────────────────
_LANG_BOUNDARIES = {
    '.py': re.compile(r'^(class |def |async def |@\w+)'),
    '.rs': re.compile(r'^(pub(\(.*?\))? )?(fn |struct |enum |trait |impl|mod |use |macro_rules!|type |const |unsafe )'),
    '.js': re.compile(r'^(async )?function |^class |^export (default )?(function|class)|^\w+\s*[:=]\s*(async\s*)?\('),
    '.ts': re.compile(r'^(async )?function |^class |^export (default )?(function|class|interface|type|abstract)|^\w+\s*[:=]\s*(async\s*)?\(|^interface \w+|^type \w+|^enum \w+|^abstract class \w+'),
    '.mojo': re.compile(r'^(class |def |fn |async def |@\w+|struct |trait |impl)'),
    '.sh': re.compile(r'^\w+\s*\(\s*\)\s*\{'),
}


def _get_language(ext: str) -> str:
    return {
        '.py': 'python',
        '.rs': 'rust',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.mojo': 'mojo',
        '.sh': 'shell',
    }.get(ext, ext.lstrip('.'))


def _should_exclude(path: str, root: str) -> bool:
    """Check if a path should be excluded."""
    rel = os.path.relpath(path, root)
    parts = rel.replace('\\', '/').split('/')
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith('.'):
            return True
    return False


def scan_files(root: str) -> list[dict]:
    """Walk root, return list of matching file paths with metadata."""
    root = os.path.abspath(root)
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded dirs in-place (prevents walking into them)
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.')]
        if _should_exclude(dirpath, root):
            continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in EXTS:
                continue
            fp = os.path.join(dirpath, fn)
            if _should_exclude(fp, root):
                continue
            try:
                st = os.stat(fp)
                files.append({
                    'filepath': fp,
                    'ext': ext,
                    'size_bytes': st.st_size,
                    'last_modified': st.st_mtime,
                })
            except OSError:
                continue
    return files


def chunk_file(filepath: str, text: str, ext: str, language: str) -> list[dict]:
    """Split file content into logical chunks by top-level definitions."""
    lines = text.split('\n')
    total_lines = len(lines)
    chunks = []

    if total_lines <= SMALL_FILE_LINES:
        # Small file → single chunk
        chunk_text = '\n'.join(lines).strip()
        if chunk_text and len(chunk_text) >= MIN_CHUNK_LINES * 2:
            chunks.append({
                'filepath': filepath,
                'chunk': chunk_text,
                'language': language,
                'lines_start': 1,
                'lines_end': total_lines,
                'size_bytes': len(text.encode('utf-8')),
                'last_modified': 0,  # filled by caller
            })
        return chunks

    # Large file → split by top-level boundaries
    boundary_re = _LANG_BOUNDARIES.get(ext)
    if not boundary_re:
        # No regex for this language → single chunk
        chunk_text = text.strip()
        if chunk_text:
            chunks.append({
                'filepath': filepath,
                'chunk': chunk_text,
                'language': language,
                'lines_start': 1,
                'lines_end': total_lines,
                'size_bytes': len(text.encode('utf-8')),
                'last_modified': 0,
            })
        return chunks

    # Find boundary lines (line numbers, 1-indexed)
    boundaries = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if boundary_re.match(stripped):
            boundaries.append(i)

    if not boundaries:
        # No boundaries found → single chunk
        chunk_text = text.strip()
        if chunk_text:
            chunks.append({
                'filepath': filepath,
                'chunk': chunk_text,
                'language': language,
                'lines_start': 1,
                'lines_end': total_lines,
                'size_bytes': len(text.encode('utf-8')),
                'last_modified': 0,
            })
        return chunks

    # Special handling: include everything before first boundary
    if boundaries[0] > 1:
        pre_lines = lines[:boundaries[0] - 1]
        pre_text = '\n'.join(pre_lines).strip()
        # Only include if it has actual code (not just imports/comments)
        if _has_code(pre_text):
            chunks.append({
                'filepath': filepath,
                'chunk': pre_text,
                'language': language,
                'lines_start': 1,
                'lines_end': boundaries[0] - 1,
                'size_bytes': len(pre_text.encode('utf-8')),
                'last_modified': 0,
            })

    # Chunk from each boundary to the next
    for idx, start_line in enumerate(boundaries):
        end_line = boundaries[idx + 1] - 1 if idx + 1 < len(boundaries) else total_lines
        chunk_lines = lines[start_line - 1:end_line]
        chunk_text = '\n'.join(chunk_lines).strip()
        chunk_lines_count = end_line - start_line + 1
        if chunk_lines_count >= MIN_CHUNK_LINES and len(chunk_text) >= 20:
            chunks.append({
                'filepath': filepath,
                'chunk': chunk_text,
                'language': language,
                'lines_start': start_line,
                'lines_end': end_line,
                'size_bytes': len(chunk_text.encode('utf-8')),
                'last_modified': 0,
            })

    return chunks


def _has_code(text: str) -> bool:
    """Check if text contains actual code (not just whitespace/comments)."""
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
            return True
    return False


def scan_and_chunk(root: str, progress_callback=None) -> list[dict]:
    """Full pipeline: scan files → read → chunk. Returns list of chunk dicts."""
    files = scan_files(root)
    all_chunks = []
    total = len(files)

    for idx, fmeta in enumerate(files):
        if progress_callback:
            progress_callback(idx + 1, total, fmeta['filepath'])

        try:
            with open(fmeta['filepath'], 'r', encoding='utf-8', errors='replace') as fh:
                text = fh.read()
        except Exception:
            continue

        if not text.strip():
            continue

        language = _get_language(fmeta['ext'])
        chunks = chunk_file(fmeta['filepath'], text, fmeta['ext'], language)

        for c in chunks:
            c['size_bytes'] = fmeta['size_bytes']
            c['last_modified'] = fmeta['last_modified']

        all_chunks.extend(chunks)

    return all_chunks


def watch_files(root: str, interval: float = 2.0):
    """Generator that yields changed files on each poll cycle."""
    known_mtimes: dict[str, float] = {}
    known_sizes: dict[str, int] = {}

    while True:
        files = scan_files(root)
        for f in files:
            old_mtime = known_mtimes.get(f['filepath'])
            old_size = known_sizes.get(f['filepath'])
            changed = (
                old_mtime is None or
                f['last_modified'] != old_mtime or
                f['size_bytes'] != old_size
            )
            if changed:
                known_mtimes[f['filepath']] = f['last_modified']
                known_sizes[f['filepath']] = f['size_bytes']
                yield f  # changed

        # Also detect removals
        removed = [fp for fp in known_mtimes if fp not in {f['filepath'] for f in files}]
        for fp in removed:
            del known_mtimes[fp]
            del known_sizes[fp]
            yield {'filepath': fp, 'removed': True, 'ext': os.path.splitext(fp)[1].lower()}

        time.sleep(interval)


if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/N-Xyme_CODE/N-Xyme_MIND')

    def _progress(i, total, fp):
        print(f"\r  [{i}/{total}] {os.path.relpath(fp, root):<60}", end='', flush=True)

    chunks = scan_and_chunk(root, _progress)
    print(f"\n\nDone. {len(chunks)} chunks from {len(set(c['filepath'] for c in chunks))} files.")

    # Print language breakdown
    langs: dict[str, int] = {}
    for c in chunks:
        langs[c['language']] = langs.get(c['language'], 0) + 1
    for lang, count in sorted(langs.items(), key=lambda x: -x[1]):
        print(f"  {lang:>12}: {count:>5} chunks")
