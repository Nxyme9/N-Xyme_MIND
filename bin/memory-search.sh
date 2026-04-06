#!/usr/bin/env bash
# Memory Search Script - Query workspace memory from bot
# Usage: ./bin/memory-search.sh "<query>"

QUERY="${1:-}"
MIND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <search-query>"
    exit 1
fi

# Use athena smart search if available
if [ -f "$MIND_DIR/.venv/bin/python3" ]; then
    PYTHON="$MIND_DIR/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "No Python found"
    exit 1
fi

# Try athena smart search
cd "$MIND_DIR"
$PYTHON -c "
import sys
sys.path.insert(0, 'athena/src')
from athena.tools.smart_search import SmartSearch

searcher = SmartSearch()
results = searcher.search('$QUERY', limit=5)

if results:
    print('🧠 Memory Search Results:')
    print()
    for i, r in enumerate(results, 1):
        title = r.get('title', 'Untitled')
        content = r.get('content', '')[:200]
        source = r.get('source', 'unknown')
        print(f'{i}. {title}')
        print(f'   Source: {source}')
        print(f'   {content}...')
        print()
else:
    print('No results found for: $QUERY')
" 2>/dev/null || echo "Search failed - Athena not available"
