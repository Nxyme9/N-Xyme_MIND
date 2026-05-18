#!/bin/bash
# find-session — search sessions + extract content
# Usage:
#   scripts/find-session                  → last 30 sessions
#   scripts/find-session "agent builder"  → search by title/agent
#   scripts/find-session --content <id>   → get all text from session

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DB="$HOME/.local/share/opencode/opencode.db"

if [ "${1:-}" = "--content" ]; then
  ID="$2"
  if [ -z "$ID" ]; then echo "Usage: $0 --content <session_id>"; exit 1; fi
  echo "── $ID ──────────────────────────────────"
  sqlite3 "$DB" \
    "SELECT substr(data,1,4000) FROM part
     WHERE session_id='$ID' AND data LIKE '%\"type\":\"text\"%'
     ORDER BY time_created;" \
    -separator ''
  echo "── end ──────────────────────────────────"
  echo
  echo "Full JSONL: cat $ROOT/data/sessions/$ID.jsonl 2>/dev/null || echo 'not on disk yet (still live)'"
  exit 0
fi

SEARCH="${1:-}"
list_all() {
  sqlite3 "$DB" \
    "SELECT id, agent, substr(title,1,60),
            datetime(time_created/1000,'unixepoch','localtime') as created
     FROM session
     ORDER BY time_created DESC
     LIMIT ${1:-30};" \
    -separator ' │ '
}

search() {
  sqlite3 "$DB" \
    "SELECT id, agent, substr(title,1,60),
            datetime(time_created/1000,'unixepoch','localtime') as created
     FROM session
     WHERE title LIKE '%${1}%' OR agent LIKE '%${1}%'
     ORDER BY time_created DESC
     LIMIT 20;" \
    -separator ' │ '
}

if [ -z "$SEARCH" ]; then
  echo "── Recent Sessions ──────────────────────"
  list_all 30
else
  echo "── Sessions matching: $SEARCH ───────────"
  search "$SEARCH"
fi
echo
echo "Get content: scripts/find-session --content <id>"
echo "Full JSONL:  cat data/sessions/<id>.jsonl"
