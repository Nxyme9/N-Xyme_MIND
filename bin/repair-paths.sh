#!/usr/bin/env bash
# bin/repair-paths.sh — Run this when the workspace mount path changes
# Fixes all hardcoded paths, shebangs, and symlinks automatically
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Workspace root: $ROOT"

# 1. Fix all hardcoded /home/nxyme paths in configs
echo "[1/5] Fixing config paths..."
for f in config/*.json config/**/*.json .opencode/opencode.json; do
  [ -f "$f" ] && sed -i "s|./|${ROOT}/|g" "$f" 2>/dev/null || true
done

# 2. Fix all hardcoded /run/media paths in configs (in case of previous mount)
echo "[2/5] Cleaning old mount paths..."
OLD_MOUNTS=$(grep -rn '/run/media/liveuser/[^/]*/@home/nxyme/nx_openmore' config/ .opencode/ 2>/dev/null | cut -d: -f1 | sort -u || true)
for f in $OLD_MOUNTS; do
  sed -i "s|/run/media/liveuser/[^/]*/@home/nxyme/nx_openmore|${ROOT}|g" "$f" 2>/dev/null || true
done

# 3. Fix athena venv shebangs
echo "[3/5] Fixing venv shebangs..."
if [ -d "athena/.venv/bin" ]; then
  VENV_PY="${ROOT}/athena/.venv/bin/python3"
  # First fix python3 symlink to be absolute
  if [ -f "/usr/bin/python3" ]; then
    ln -sf /usr/bin/python3 athena/.venv/bin/python3
  fi
  # Then fix all script shebangs
  find athena/.venv/bin -maxdepth 1 -type f -exec grep -l '#!' {} \; 2>/dev/null | while read f; do
    sed -i "1s|^#!.*python3|#!${VENV_PY}|" "$f" 2>/dev/null || true
  done
  echo "  Fixed $(find athena/.venv/bin -maxdepth 1 -type f | wc -l) scripts"
fi

# 4. Fix shell script paths
echo "[4/5] Fixing shell script paths..."
for f in bin/*.sh bin/quality-gates/*.sh; do
  [ -f "$f" ] && sed -i "s|/run/media/liveuser/[^/]*/@home/nxyme/nx_openmore|${ROOT}|g" "$f" 2>/dev/null || true
done
# Fix fish script
sed -i "s|.|${ROOT}|g" bin/jarvis 2>/dev/null || true
sed -i "s|~/nx_openmore|${ROOT}|g" bin/jarvis 2>/dev/null || true

# 5. Sync configs
echo "[5/5] Syncing configs..."
cp config/opencode.json .opencode/opencode.json 2>/dev/null || true

echo ""
echo "Done! All paths now point to: ${ROOT}"
echo ""
echo "If you moved the workspace, also run:"
echo "  ./bin/quality-gates/gate-5-secrets.sh  # Verify no secrets leaked"
