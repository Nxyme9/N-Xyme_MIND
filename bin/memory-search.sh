#!/usr/bin/env bash
# Memory Search Script - Query workspace memory from bot
# Usage: ./bin/memory-search.sh "<query>"

QUERY="${1:-}"
MIND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <search-query>"
    exit 1
fi

# Use unified memory (packages/memory_core)
if [ -f "$MIND_DIR/.venv/bin/python3" ]; then
    PYTHON="$MIND_DIR/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "No Python found"
    exit 1
fi

# Use unified memory instead of deprecated Athena
cd "$MIND_DIR"
$PYTHON -c "
import sys
sys.path.insert(0, '.')
from packages.memory_core.router import MemoryRouter, UnifiedMemoryQuery

router = MemoryRouter()
query = UnifiedMemoryQuery(query='$QUERY', max_results_per_source=5)
results = router.search(query)

if results.results:
    print('🧠 Memory Search Results:')
    print()
    for i, r in enumerate(results.results[:5], 1):
        content = r.content[:200] if isinstance(r.content, str) else str(r.content)[:200]
        print(f'{i}. {r.source}')
        print(f'   {content}...')
        print()
else:
    print('No results found for: $QUERY')
" 2>/dev/null || echo "Search failed"
