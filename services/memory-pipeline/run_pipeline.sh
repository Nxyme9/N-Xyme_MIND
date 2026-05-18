#!/usr/bin/env bash
#
# run_pipeline.sh — One-shot holographic memory pipeline.
#
# Runs session ingestion (ONNX direct for bulk), verifies output,
# runs test searches, and reports statistics.
#
# Usage:
#   bash run_pipeline.sh
#   NX_PROJECT_ROOT=/custom/path bash run_pipeline.sh
#

set -euo pipefail

# ── Determine project root ──────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${NX_PROJECT_ROOT:-"$(cd "$SCRIPT_DIR/../.." && pwd)"}"
export NX_PROJECT_ROOT="$PROJECT_ROOT"

INGEST_SCRIPT="$PROJECT_ROOT/services/memory-pipeline/ingest_sessions.py"
SEARCH_SCRIPT="$PROJECT_ROOT/services/memory-pipeline/search_memory.py"
OUTPUT_FILE="$PROJECT_ROOT/data/memory/vectors/sessions.jsonl"
SESSION_DIR="$PROJECT_ROOT/data/sessions"

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▶${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1"; }

# ── Prelim checks ───────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   N-Xyme Holographic Memory Pipeline${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo ""
info "Project root: $PROJECT_ROOT"
info "Output file:  $OUTPUT_FILE"
info "Session dir:  $SESSION_DIR"

# Verify files exist
for f in "$INGEST_SCRIPT" "$SEARCH_SCRIPT"; do
    if [ ! -f "$f" ]; then
        err "Required script not found: $f"
        exit 1
    fi
done

if [ ! -d "$SESSION_DIR" ]; then
    err "Session directory not found: $SESSION_DIR"
    exit 1
fi

SESSION_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" -type f | wc -l)
info "Session files found: $SESSION_COUNT"

mkdir -p "$(dirname "$OUTPUT_FILE")"
echo ""

# ── Phase 1: Ingestion ─────────────────────────────────────────────
info "Phase 1: Session Ingestion (ONNX bulk embedding)"
echo ""

python3 "$INGEST_SCRIPT"

echo ""

# ── Phase 2: Verify Output ─────────────────────────────────────────
info "Phase 2: Output Verification"

if [ ! -f "$OUTPUT_FILE" ]; then
    err "Output file not created at $OUTPUT_FILE"
    exit 1
fi

VECTOR_COUNT=$(wc -l < "$OUTPUT_FILE")
info "Vector entries: $VECTOR_COUNT"

if [ "$VECTOR_COUNT" -eq 0 ]; then
    err "Output file is empty!"
    exit 1
fi

# Validate first entry
FIRST_LINE=$(head -1 "$OUTPUT_FILE")
if echo "$FIRST_LINE" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    assert 'vector' in d, 'Missing vector'
    assert 'content' in d, 'Missing content'
    vec = d['vector']
    assert len(vec) == 384, f'Expected 384-dim, got {len(vec)}'
    assert d['dim'] == 384, f'Wrong dim: {d[\"dim\"]}'
    assert 'id' in d, 'Missing id'
    assert 'session' in d, 'Missing session'
    assert 'agent' in d, 'Missing agent'
    print(f'Vector dim: {len(vec)} ✓')
    print(f'Content preview: {d[\"content\"][:80]}...')
    print(f'Session: {d.get(\"session\", \"?\")}')
    print(f'Agent: {d.get(\"agent\", \"?\")}')
    print(f'Type: {d.get(\"type\", \"?\")}')
    print(f'ID: {d.get(\"id\", \"?\")}')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    ok "Output format validated (384-dim vectors with full metadata)"
else
    err "Output validation failed"
    exit 1
fi

echo ""

# ── Phase 3: Test Search ───────────────────────────────────────────
info "Phase 3: Test Search Queries"
echo ""

TEST_QUERIES=(
    "mojo router"
    "authentication tokens"
    "JWT API auth"
    "embedding decision"
    "code search bridge"
)

for query in "${TEST_QUERIES[@]}"; do
    echo -e "${YELLOW}━━━ Search: \"$query\" ━━━${NC}"
    if python3 "$SEARCH_SCRIPT" "$query" --top 2 2>/dev/null; then
        ok "Search completed"
    else
        warn "Search encountered issues"
    fi
    echo ""
done

# ── Phase 4: Stats Report ──────────────────────────────────────────
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   PIPELINE STATISTICS${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo ""

TOTAL_BYTES=$(stat --format=%s "$OUTPUT_FILE" 2>/dev/null || stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "?")
AVG_VEC_SIZE=$(( TOTAL_BYTES / VECTOR_COUNT ))

echo "  Session files scanned:  $SESSION_COUNT"
echo "  Vectors stored:         $VECTOR_COUNT"
echo "  Vector dimension:       384"
echo "  Model:                  all-MiniLM-L6-v2"
echo "  Embedding engine:       onnxruntime (local, no subprocess)"
echo "  Output file size:       $TOTAL_BYTES bytes"
echo "  Avg record size:        $AVG_VEC_SIZE bytes"
echo ""

echo -e "${GREEN}✓ Pipeline completed successfully${NC}"
echo ""
