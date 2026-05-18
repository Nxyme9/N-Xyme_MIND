#!/usr/bin/env bash
# delegate_task — routes a delegation to the target agent's data/ directory
# Usage: delegate_task <from_agent> <to_agent> <task> [files] [criteria]
# Effect: writes to agents/<to>/data/pending/<timestamp>.json
#         The target agent picks it up on next session_start

set -euo pipefail

FROM="${1:-unknown}"
TO="${2:-unknown}"
TASK="${3:-}"
FILES="${4:-}"
CRITERIA="${5:-}"

AGENTS_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/agents"
PENDING_DIR="${AGENTS_DIR}/${TO}/data/pending"
mkdir -p "${PENDING_DIR}"

TIMESTAMP=$(date +%s%N)
cat > "${PENDING_DIR}/${TIMESTAMP}.json" << EOF
{
  "from": "${FROM}",
  "to": "${TO}",
  "task": $(echo "${TASK}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "files": $(echo "${FILES}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "criteria": $(echo "${CRITERIA}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "status": "pending",
  "timestamp": $(date +%s),
  "id": "${TIMESTAMP}"
}
EOF

echo "✅ Task delegated: ${FROM} → ${TO}"
echo "   File: ${PENDING_DIR}/${TIMESTAMP}.json"
echo "   Task: ${TASK:0:80}..."
