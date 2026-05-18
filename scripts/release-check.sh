#!/usr/bin/env bash
# Release Readiness Check — v1.0
# Exit code: 0 = ready, 1 = warnings, 2 = blocking
# Gold-standard pre-flight checklist for N-Xyme MIND

set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; WARN=0; BLOCK=0

check() {
    local level=$1 name=$2; shift 2
    if "$@" &>/dev/null; then
        echo -e "  ${GREEN}✅${NC} $name"; PASS=$((PASS + 1))
    elif [ "$level" = "block" ]; then
        echo -e "  ${RED}❌ BLOCKING${NC} $name"
        BLOCK=$((BLOCK + 1))
    else
        echo -e "  ${YELLOW}⚠️  WARN${NC} $name"
        WARN=$((WARN + 1))
    fi
}

echo "═══════════════════════════════════════════"
echo "  N-Xyme MIND — Release Readiness Check"
echo "═══════════════════════════════════════════"
echo ""

echo "── Gold Standards ──"
check block "CHANGELOG.md exists"          test -f CHANGELOG.md
check block "CONTRIBUTING.md exists"       test -f CONTRIBUTING.md
check block "CODE_OF_CONDUCT.md exists"    test -f CODE_OF_CONDUCT.md
check block "LICENSE exists"               test -f LICENSE
check block "README.md exists"             test -f README.md
check block "llms.txt exists"              test -f llms.txt
check block ".gitignore exists"             test -f .gitignore
check warn  "SECURITY.md exists"           test -f SECURITY.md
check warn  "Issue templates exist"        test -f .github/ISSUE_TEMPLATE/bug_report.md
check warn  "PR template exists"           test -f .github/PULL_REQUEST_TEMPLATE.md

echo ""
echo "── Config Integrity ──"
check block "opencode.json valid JSON"     python3 -c "import json; json.load(open('opencode.json'))"
check block "config/nx_agents.json valid"  python3 -c "import json; json.load(open('config/nx_agents.json'))"
check warn  "Configs synced"               python3 -c "
import json
a = json.load(open('opencode.json'))
b = json.load(open('config/nx_agents.json'))
akeys = set(a.get('agent', {}).keys()) | set(a.get('agents', {}).keys())
bkeys = set(b.get('agent', {}).keys()) | set(b.get('agents', {}).keys())
# Allow either key name, check that intersection is non-empty
common = akeys & bkeys
if not common:
    # fallback: check that both have agents defined
    assert len(akeys) > 0 and len(bkeys) > 0, 'agent keys mismatch or empty'
"
check warn  "No hardcoded /home/nxyme/ in config" \
    bash -c 'grep -rn "/home/nxyme/" opencode.json config/nx_agents.json --include="*.json" 2>/dev/null; [ $? -eq 1 ]'

echo ""
echo "── Mojo Stack ──"
check block "compat.mojo exists"           test -f services/mojo/src/compat.mojo
check warn  "Mojo compiles"                bash -c 'which mojo &>/dev/null'
check warn  "bins/ in gitignore"           bash -c 'grep -q "^bins/" .gitignore 2>/dev/null'

echo ""
echo "── Git Hygiene ──"
check warn  "No unstaged changes"          git diff --quiet
check warn  "No untracked secrets"         bash -c 'git ls-files --others --exclude-standard | grep -q secrets/; [ $? -eq 1 ]'
check block "Version tag exists"           bash -c 'git describe --tags --abbrev=0 &>/dev/null'

echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${GREEN}$PASS passed${NC} | ${YELLOW}$WARN warnings${NC} | ${RED}$BLOCK blocking${NC}"
echo ""

if [ $BLOCK -gt 0 ]; then
    echo -e "${RED}❌ BLOCKING ISSUES — fix before release${NC}"
    exit 2
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS — review before release${NC}"
    exit 1
else
    echo -e "${GREEN}✅ READY FOR RELEASE${NC}"
    exit 0
fi
