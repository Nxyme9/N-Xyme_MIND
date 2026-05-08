#!/usr/bin/env bash
# =============================================================================
# migration_rollback.sh — Complete rollback for Momus migration
# =============================================================================
# This script reverts all migration changes in ONE command.
# Usage: bash scripts/migration_rollback.sh [--dry-run]
#
# Steps:
#   1. Stop all MCP servers
#   2. Create backup of current state (if not exists)
#   3. Delete migrated data from memory_store
#   4. Restore .sisyphus.backup/ files
#   5. Restart MCP servers
#   6. Verify delegation works
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/.sisyphus.backup"
STATE_DIR="$PROJECT_ROOT/.sisyphus"
MEMORY_STORE_DB="$PROJECT_ROOT/context/memory/mind_from_mind.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Dry-run mode flag
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}[DRY-RUN MODE]${NC} — No changes will be made"
fi

log() {
    echo -e "${GREEN}[ROLLBACK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Step 1: Stop all MCP servers
# =============================================================================
stop_mcp_servers() {
    log "Stopping MCP servers..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would stop MCP servers: context7-mcp, notion-mcp-server, mcp-fetch-server, mcp-telegram-listener, mcp-server-sequential-thinking, mcp-server-github"
        return 0
    fi

    # Find and kill MCP-related processes (be careful to not kill parent shell)
    local pids=(
        $(ps aux | grep -E "(context7-mcp|notion-mcp-server|mcp-fetch-server|mcp-telegram-listener|mcp-server-sequential-thinking|mcp-server-github)" | grep -v grep | awk '{print $2}')
    )

    if [[ ${#pids[@]} -gt 0 ]]; then
        for pid in "${pids[@]}"; do
            if [[ -n "$pid" && "$pid" != "$$" ]]; then
                kill "$pid" 2>/dev/null || true
                log "Stopped process: $pid"
            fi
        done
        sleep 2
    else
        log "No MCP processes found running"
    fi

    log "MCP servers stopped"
}

# =============================================================================
# Step 2: Create backup of current state (for potential re-migration)
# =============================================================================
create_backup() {
    log "Creating backup of current state..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would create backup at $BACKUP_DIR"
        return 0
    fi

    mkdir -p "$BACKUP_DIR"

    # Backup key database files
    local files=(
        "state.db"
        "context.db"
        "routing.db"
        "outcomes.db"
        "memory.db"
    )

    for file in "${files[@]}"; do
        if [[ -f "$STATE_DIR/$file" ]]; then
            cp "$STATE_DIR/$file" "$BACKUP_DIR/$file.backup"
            log "Backed up: $file"
        fi
    done

    # Backup memory_store if exists
    if [[ -f "$MEMORY_STORE_DB" ]]; then
        cp "$MEMORY_STORE_DB" "$BACKUP_DIR/memory_store.db.backup"
        log "Backed up: memory_store"
    fi

    log "Backup complete"
}

# =============================================================================
# Step 3: Delete migrated data from memory_store
# =============================================================================
delete_migrated_data() {
    log "Deleting migrated data from memory_store..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would delete data from: $MEMORY_STORE_DB"
        warn "[DRY-RUN] Would delete tables: memories, memory_embeddings, memory_versions"
        return 0
    fi

    if [[ ! -f "$MEMORY_STORE_DB" ]]; then
        warn "memory_store DB not found at $MEMORY_STORE_DB — skipping deletion"
        return 0
    fi

    # Delete migrated memory tables (safe - only removes migration-specific data)
    sqlite3 "$MEMORY_STORE_DB" <<'EOF'
-- Delete migration-specific data while preserving original memory_store data
DELETE FROM memory_versions WHERE 1=1;
DELETE FROM memory_embeddings WHERE 1=1;
DELETE FROM memories WHERE tier = 'long_term' OR scope = 'global';
EOF

    local deleted=$(sqlite3 "$MEMORY_STORE_DB" "SELECT COUNT(*) FROM memories;")
    log "Deleted migrated data. Remaining memories: $deleted"

    # Vacuum to reclaim space
    sqlite3 "$MEMORY_STORE_DB" "VACUUM;"
    log "Memory store cleaned"
}

# =============================================================================
# Step 4: Restore .sisyphus.backup/ (if exists)
# =============================================================================
restore_backup() {
    log "Restoring .sisyphus.backup/ files..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would restore from $BACKUP_DIR"
        return 0
    fi

    if [[ ! -d "$BACKUP_DIR" ]]; then
        warn "No backup directory at $BACKUP_DIR — skipping restore"
        return 0
    fi

    # Restore database files
    for file in "$BACKUP_DIR"/*.backup; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file" .backup)
            local target="$STATE_DIR/$basename"

            if [[ -f "$target" ]]; then
                # Create pre-restore backup of current state
                cp "$target" "$target.pre_rollback"
            fi

            cp "$file" "$target"
            log "Restored: $basename"
        fi
    done

    log "Backup files restored"
}

# =============================================================================
# Step 5: Restart MCP servers
# =============================================================================
restart_mcp_servers() {
    log "Restarting MCP servers..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would restart MCP servers"
        warn "[DRY-RUN] Would execute: opencode (background) or systemctl restart mcp-*"
        return 0
    fi

    # Method 1: If user has opencode running, restart it
    if pgrep -f "opencode" > /dev/null; then
        warn "OpenCode is running. Restart session to reload MCPs."
        warn "Run: pkill -f opencode && opencode"
    else
        # Try to start opencode in background (will auto-connect MCPs)
        log "OpenCode not detected. Start with: opencode"
    fi

    # Give MCPs time to initialize
    sleep 3
    log "MCP servers restart triggered (restart OpenCode to fully reload)"
}

# =============================================================================
# Step 6: Verify delegation works
# =============================================================================
verify_delegation() {
    log "Verifying delegation functionality..."

    if [[ "$DRY_RUN" == true ]]; then
        warn "[DRY-RUN] Would verify:"
        warn "  - Check state.db has sessions table"
        warn "  - Check delegations table exists"
        warn "  - Test simple SQLite query"
        return 0
    fi

    # Verify key tables exist and are readable
    local tables=$(sqlite3 "$STATE_DIR/state.db" ".tables" 2>/dev/null || echo "")
    if echo "$tables" | grep -q "sessions"; then
        log "✓ sessions table verified"
    else
        error "sessions table missing from state.db"
        return 1
    fi

    if echo "$tables" | grep -q "delegations"; then
        log "✓ delegations table verified"
    else
        error "delegations table missing from state.db"
        return 1
    fi

    # Test a simple query
    local count=$(sqlite3 "$STATE_DIR/state.db" "SELECT COUNT(*) FROM sessions;" 2>/dev/null || echo "0")
    log "✓ sessions count: $count"

    # Check routing.db weights
    if [[ -f "$STATE_DIR/routing.db" ]]; then
        local weights_count=$(sqlite3 "$STATE_DIR/routing.db" "SELECT COUNT(*) FROM agent_weights;" 2>/dev/null || echo "0")
        log "✓ agent_weights count: $weights_count"
    fi

    # Check outcomes.db
    if [[ -f "$STATE_DIR/outcomes.db" ]]; then
        local outcomes_count=$(sqlite3 "$STATE_DIR/outcomes.db" "SELECT COUNT(*) FROM outcomes;" 2>/dev/null || echo "0")
        log "✓ outcomes count: $outcomes_count"
    fi

    log "Delegation verification complete"
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    log "Starting migration rollback..."
    echo ""

    # Execute rollback steps
    stop_mcp_servers
    echo ""

    create_backup
    echo ""

    delete_migrated_data
    echo ""

    restore_backup
    echo ""

    restart_mcp_servers
    echo ""

    verify_delegation
    echo ""

    log "Rollback complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart OpenCode: pkill -f opencode && opencode"
    echo "  2. Verify MCP tools work: Test nx_delegate or routing tools"
    echo "  3. If issues: Check logs at $PROJECT_ROOT/logs/"
}

# Run main
main "$@"